"""
CAMS AI Tutor Router — REST & SSE Endpoints for AI Chess Tutor.
"""
import asyncio
import json
import logging
import random
import time
import uuid
from typing import Any, Optional


from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import FileResponse, Response, StreamingResponse
from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.core.config import settings
from app.core.database import get_db, async_session_factory
from app.core.redis import (
    check_ai_tutor_rate_limit,
    check_ai_tutor_tts_rate_limit,
    get_cached_ai_response,
    refund_ai_tutor_rate_limit,
    set_cached_ai_response,
)
from app.models.ai_tutor import ChatMessage, ChatSession
from app.models.puzzle import Puzzle
from app.models.user import User
from app.schemas.ai_tutor import (
    ChatMessageOut,
    ChatRequest,
    ChatSessionOut,
    PuzzleCheckRequest,
    PuzzleCheckResponse,
    PuzzleExplainResponse,
    PuzzleSolutionResponse,
    TTSRequest,
)
from app.services.ai_tutor import (
    AI_TUTOR_SYSTEM_PROMPT,
    AIProviderError,
    TTSProviderError,
    check_puzzle_move,
    explain_puzzle_solution,
    extract_and_validate_board,
    get_cached_audio_path,
    get_llm_provider,
    get_puzzle_solution,
    get_tts_provider,
    prepare_text_for_speech,
    record_puzzle_attempt,
    save_cached_audio,
    search_approved_puzzles,
)
from app.services.llm import LLMProviderError, stream_chat_resilient

logger = logging.getLogger(__name__)

router = APIRouter()

SUPPORTED_VOICES = {
    "vi-VN-HoaiMyNeural": "Nữ (Hoài My)",
    "vi-VN-NamMinhNeural": "Nam (Nam Minh)",
}


def _generate_title(message: str) -> str:
    """Generate a concise title from the user's first prompt."""
    clean = message.strip().replace("\n", " ")
    if len(clean) > 40:
        return clean[:37] + "..."
    return clean or "Cuộc trò chuyện mới"


@router.get("/sessions", response_model=list[ChatSessionOut])
async def list_sessions(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Retrieve all chat sessions for the current user."""
    stmt = (
        select(ChatSession)
        .where(ChatSession.user_id == current_user.id)
        .order_by(desc(ChatSession.created_at))
    )
    result = await db.execute(stmt)
    sessions = result.scalars().all()
    return sessions


@router.get("/sessions/{session_id}/messages", response_model=list[ChatMessageOut])
async def get_session_messages(
    session_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Retrieve message history for a specific session."""
    session_stmt = select(ChatSession).where(
        ChatSession.id == session_id,
        ChatSession.user_id == current_user.id,
    )
    session_res = await db.execute(session_stmt)
    session = session_res.scalars().first()
    if not session:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Không tìm thấy phiên trò chuyện.")

    msg_stmt = (
        select(ChatMessage)
        .where(ChatMessage.session_id == session_id)
        .order_by(ChatMessage.created_at.asc())
    )
    msg_res = await db.execute(msg_stmt)
    messages = msg_res.scalars().all()
    return messages


@router.delete("/sessions/{session_id}")
async def delete_session(
    session_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Delete a chat session and all its messages."""
    stmt = select(ChatSession).where(
        ChatSession.id == session_id,
        ChatSession.user_id == current_user.id,
    )
    res = await db.execute(stmt)
    session = res.scalars().first()
    if not session:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Không tìm thấy phiên trò chuyện.")

    await db.delete(session)
    await db.commit()
    return {"message": "Đã xóa cuộc trò chuyện thành công."}


@router.post("/chat")
async def chat_stream(
    request: ChatRequest,
    current_user: User = Depends(get_current_user),
):
    """
    Send a message to the AI Chess Tutor and receive response via Server-Sent Events (SSE).
    """
    # 1. Rate limiting check
    is_allowed, error_msg = await check_ai_tutor_rate_limit(current_user.id)
    if not is_allowed:
        raise HTTPException(status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail=error_msg)

    # 2. Setup or verify session in DB
    session_id = request.session_id
    title = _generate_title(request.message)

    async with async_session_factory() as db:
        if session_id:
            s_stmt = select(ChatSession).where(
                ChatSession.id == session_id,
                ChatSession.user_id == current_user.id,
            )
            s_res = await db.execute(s_stmt)
            chat_session = s_res.scalars().first()
            if not chat_session:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Phiên trò chuyện không tồn tại.")
        else:
            chat_session = ChatSession(
                user_id=current_user.id,
                title=title,
            )
            db.add(chat_session)
            await db.commit()
            await db.refresh(chat_session)
            session_id = chat_session.id

        # 3. Retrieve conversation history
        history_stmt = (
            select(ChatMessage)
            .where(ChatMessage.session_id == session_id)
            .order_by(desc(ChatMessage.created_at))
            .limit(settings.AI_TUTOR_HISTORY_LIMIT)
        )
        h_res = await db.execute(history_stmt)
        past_messages = list(reversed(h_res.scalars().all()))

        # Save user message
        user_message_record = ChatMessage(
            session_id=session_id,
            role="user",
            content=request.message,
        )
        db.add(user_message_record)
        await db.commit()

        history_payload = [
            {"role": m.role, "content": m.content}
            for m in past_messages
        ]
        history_payload.append({"role": "user", "content": request.message})

    # 4. Stream generator for SSE
    async def sse_stream():
        # Check cache first
        cached = await get_cached_ai_response(request.message)
        if cached:
            clean_content = cached.get("content", "")
            board_data = cached.get("board_data")
            puzzle_data = cached.get("puzzle_data")

            # Stream cached text in small chunks for consistent UI feel
            chunk_size = 30
            for i in range(0, len(clean_content), chunk_size):
                chunk = clean_content[i : i + chunk_size]
                yield f"event: message\ndata: {json.dumps({'chunk': chunk}, ensure_ascii=False)}\n\n"

            if board_data:
                yield f"event: board\ndata: {json.dumps({'board_data': board_data}, ensure_ascii=False)}\n\n"

            if puzzle_data:
                yield f"event: puzzles\ndata: {json.dumps({'puzzles': puzzle_data}, ensure_ascii=False)}\n\n"

            # Save cached assistant message to DB
            async with async_session_factory() as db:
                asst_msg = ChatMessage(
                    session_id=session_id,
                    role="assistant",
                    content=clean_content,
                    board_data=board_data,
                    puzzle_data=puzzle_data,
                )
                db.add(asst_msg)
                await db.commit()
                await db.refresh(asst_msg)
                msg_id = str(asst_msg.id)

            yield f"event: done\ndata: {json.dumps({'session_id': str(session_id), 'message_id': msg_id})}\n\n"
            return

        # Puzzles collected during tool execution
        retrieved_puzzles: list[dict[str, Any]] = []

        async def handle_tool_call(name: str, args: dict[str, Any]) -> dict[str, Any]:
            if name == "search_puzzles":
                theme = args.get("theme", "")
                level = args.get("level")
                limit = args.get("limit", 2)
                async with async_session_factory() as db:
                    puzzles = await search_approved_puzzles(
                        db=db,
                        user_id=current_user.id,
                        theme=theme,
                        level=level,
                        limit=limit,
                    )
                retrieved_puzzles.extend(puzzles)
                # Formulate safe LLM tool response WITHOUT solution moves or internal secret details
                return {
                    "puzzles_found": len(puzzles),
                    "theme": theme,
                    "puzzles": [
                        {
                            "id": p["id"],
                            "title": p["title"],
                            "side_to_move": "Trắng đi trước" if p["side_to_move"] == "w" else "Đen đi trước",
                            "theme": p["theme"],
                            "difficulty": p["difficulty"],
                        }
                        for p in puzzles
                    ],
                    "message": (
                        f"Đã tìm thấy {len(puzzles)} thế cờ từ kho bài tập."
                        if puzzles
                        else f"Không tìm thấy bài tập nào với chủ đề '{theme}' trong kho bài tập."
                    ),
                }
            return {"error": f"Unknown tool: {name}"}

        # Call Resilient Dynamic LLM Provider
        accumulated_text = ""
        has_emitted_tokens = False

        try:
            async for chunk in stream_chat_resilient(
                system_instruction=AI_TUTOR_SYSTEM_PROMPT,
                messages=history_payload,
                tool_handler=handle_tool_call,
            ):
                has_emitted_tokens = True
                accumulated_text += chunk
                yield f"event: message\ndata: {json.dumps({'chunk': chunk}, ensure_ascii=False)}\n\n"

        except (AIProviderError, LLMProviderError) as e:
            err_code = getattr(e, "code", "other")
            err_msg = getattr(e, "message", str(e))
            err_retryable = getattr(e, "retryable", False)
            logger.warning("AI Provider Error during stream: [%s] %s", err_code, err_msg)

            # Refund rate limit so student is not penalized for external Gemini overloads/quotas
            if err_code in ("overloaded", "quota"):
                await refund_ai_tutor_rate_limit(current_user.id)

            error_payload = {
                "error": err_msg,
                "code": err_code,
                "retryable": not has_emitted_tokens and err_retryable,
            }
            done_payload = {"error": True, "code": err_code}
            yield f"event: error\ndata: {json.dumps(error_payload, ensure_ascii=False)}\n\n"
            yield f"event: done\ndata: {json.dumps(done_payload)}\n\n"
            return

        except Exception as e:
            logger.error("Unexpected error in AI Tutor stream: %s", e)
            error_payload = {
                "error": "Có lỗi bất ngờ khi trao đổi với AI. Vui lòng thử lại sau.",
                "code": "other",
                "retryable": not has_emitted_tokens,
            }
            done_payload = {"error": True, "code": "other"}
            yield f"event: error\ndata: {json.dumps(error_payload, ensure_ascii=False)}\n\n"
            yield f"event: done\ndata: {json.dumps(done_payload)}\n\n"
            return

        # 5. Extract & validate board illustration
        clean_text, board_data = extract_and_validate_board(accumulated_text)

        if board_data:
            yield f"event: board\ndata: {json.dumps({'board_data': board_data}, ensure_ascii=False)}\n\n"

        if retrieved_puzzles:
            yield f"event: puzzles\ndata: {json.dumps({'puzzles': retrieved_puzzles}, ensure_ascii=False)}\n\n"

        # 6. Save assistant message to Database & Cache (only if non-empty content)
        msg_id = None
        if clean_text:
            async with async_session_factory() as db:
                asst_msg = ChatMessage(
                    session_id=session_id,
                    role="assistant",
                    content=clean_text,
                    board_data=board_data,
                    puzzle_data=retrieved_puzzles if retrieved_puzzles else None,
                )
                db.add(asst_msg)
                await db.commit()
                await db.refresh(asst_msg)
                msg_id = str(asst_msg.id)

            # Cache the validated response
            await set_cached_ai_response(
                request.message,
                clean_text,
                board_data,
                puzzle_data=retrieved_puzzles if retrieved_puzzles else None,
            )

        # 7. Complete SSE stream
        yield f"event: done\ndata: {json.dumps({'session_id': str(session_id), 'message_id': msg_id})}\n\n"

    return StreamingResponse(
        sse_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.post("/tts")
async def generate_tts(
    request: TTSRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Generate speech audio (MP3) for an assistant message in the user's session.
    Guarded against unauthorized access and rate-limited via Redis.
    """
    # 1. Check TTS rate limit
    is_allowed, error_msg = await check_ai_tutor_tts_rate_limit(current_user.id)
    if not is_allowed:
        raise HTTPException(status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail=error_msg)

    # 2. Validate voice choice
    voice = request.voice if request.voice in SUPPORTED_VOICES else settings.AI_TUTOR_TTS_VOICE

    # 3. Query message & verify ownership (must belong to a session of current_user)
    stmt = (
        select(ChatMessage)
        .join(ChatSession, ChatMessage.session_id == ChatSession.id)
        .where(
            ChatMessage.id == request.message_id,
            ChatSession.user_id == current_user.id,
        )
    )
    result = await db.execute(stmt)
    message = result.scalars().first()

    if not message:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Không tìm thấy tin nhắn hoặc bạn không có quyền truy cập.",
        )

    # 4. Prepare text for speech (clean markdown & format chess notation)
    speech_text = prepare_text_for_speech(message.content, max_chars=settings.AI_TUTOR_TTS_MAX_CHARS)
    if not speech_text:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Tin nhắn này không có nội dung văn bản để đọc.",
        )

    # 5. Check cache on disk
    cached_path = get_cached_audio_path(speech_text, voice)
    if cached_path and cached_path.is_file():
        return FileResponse(
            path=str(cached_path),
            media_type="audio/mpeg",
            headers={
                "Content-Disposition": "inline; filename=speech.mp3",
                "X-Cache": "HIT",
            },
        )

    # 6. Generate speech audio using provider
    provider = get_tts_provider()
    try:
        audio_bytes = await provider.generate_speech(speech_text, voice)
    except TTSProviderError as e:
        logger.warning("TTS Provider error: %s", e.message)
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=e.message)
    except Exception as e:
        logger.error("Unexpected TTS error: %s", e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Không thể tạo giọng đọc lúc này. Vui lòng thử lại sau.",
        )

    # 7. Save to disk cache for future requests
    save_cached_audio(speech_text, voice, audio_bytes)

    return Response(
        content=audio_bytes,
        media_type="audio/mpeg",
        headers={
            "Content-Disposition": "inline; filename=speech.mp3",
            "X-Cache": "MISS",
        },
    )


@router.post("/puzzles/{puzzle_id}/check", response_model=PuzzleCheckResponse)
async def check_move(
    puzzle_id: uuid.UUID,
    req: PuzzleCheckRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Validate a student's move for an AI Tutor interactive puzzle.
    Returns whether the move was correct, whether the puzzle is completed,
    and the opponent's counter-move if applicable.
    """
    try:
        res = await check_puzzle_move(
            db=db,
            puzzle_id=puzzle_id,
            user_id=current_user.id,
            move_str=req.move,
            current_fen=req.current_fen,
            step_index=req.step_index,
            session_id=req.session_id,
        )
        return res
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.get("/puzzles/{puzzle_id}/hint")
async def get_hint(
    puzzle_id: uuid.UUID,
    session_id: Optional[uuid.UUID] = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Get a gentle tactical theme hint for a puzzle without revealing the moves.
    Tracks hint usage in ai_puzzle_attempts.
    """
    stmt = select(Puzzle).where(Puzzle.id == puzzle_id)
    res = await db.execute(stmt)
    puzzle = res.scalar_one_or_none()
    if not puzzle:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Thế cờ không tồn tại.")

    await record_puzzle_attempt(
        db=db,
        user_id=current_user.id,
        puzzle_id=puzzle_id,
        is_correct=False,
        session_id=session_id,
        increment_attempt=False,
        increment_hint=True,
    )

    theme_name = puzzle.puzzle_type or (puzzle.tags[0] if puzzle.tags else "Chiến thuật")
    return {
        "puzzle_id": str(puzzle.id),
        "theme": theme_name,
        "hint": f"Gợi ý: Bài tập này xoay quanh đòn chiến thuật '{theme_name}'. Con hãy quan sát kỹ đường đi của các quân cờ!",
    }


@router.post("/puzzles/{puzzle_id}/solution", response_model=PuzzleSolutionResponse)
async def view_solution(
    puzzle_id: uuid.UUID,
    session_id: Optional[uuid.UUID] = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Reveal official solution moves only when explicitly requested by student.
    """
    try:
        res = await get_puzzle_solution(
            db=db,
            puzzle_id=puzzle_id,
            user_id=current_user.id,
            session_id=session_id,
        )
        return res
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@router.post("/puzzles/{puzzle_id}/explain", response_model=PuzzleExplainResponse)
async def explain_solution(
    puzzle_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Generate an AI tactical explanation grounded strictly on the DB solution line.
    """
    try:
        explanation = await explain_puzzle_solution(db=db, puzzle_id=puzzle_id)
        return PuzzleExplainResponse(puzzle_id=puzzle_id, explanation=explanation)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))

