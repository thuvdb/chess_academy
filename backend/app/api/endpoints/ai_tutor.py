"""
CAMS AI Tutor Router — REST & SSE Endpoints for AI Chess Tutor.
"""
import json
import logging
import uuid
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.deps import get_current_user
from app.core.config import settings
from app.core.database import get_db, async_session_factory
from app.core.redis import check_ai_tutor_rate_limit, get_cached_ai_response, set_cached_ai_response
from app.models.ai_tutor import ChatMessage, ChatSession
from app.models.user import User
from app.schemas.ai_tutor import (
    ChatMessageOut,
    ChatRequest,
    ChatSessionDetailOut,
    ChatSessionOut,
)
from app.services.ai_tutor.board_validator import extract_and_validate_board
from app.services.ai_tutor.prompt import AI_TUTOR_SYSTEM_PROMPT
from app.services.ai_tutor.provider import AIProviderError, get_llm_provider

logger = logging.getLogger(__name__)

router = APIRouter()


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

            # Stream cached text in small chunks for consistent UI feel
            chunk_size = 30
            for i in range(0, len(clean_content), chunk_size):
                chunk = clean_content[i : i + chunk_size]
                yield f"event: message\ndata: {json.dumps({'chunk': chunk}, ensure_ascii=False)}\n\n"

            if board_data:
                yield f"event: board\ndata: {json.dumps({'board_data': board_data}, ensure_ascii=False)}\n\n"

            # Save cached assistant message to DB
            async with async_session_factory() as db:
                asst_msg = ChatMessage(
                    session_id=session_id,
                    role="assistant",
                    content=clean_content,
                    board_data=board_data,
                )
                db.add(asst_msg)
                await db.commit()
                await db.refresh(asst_msg)
                msg_id = str(asst_msg.id)

            yield f"event: done\ndata: {json.dumps({'session_id': str(session_id), 'message_id': msg_id})}\n\n"
            return

        # Call LLM Provider
        provider = get_llm_provider()
        accumulated_text = ""

        try:
            async for chunk in provider.stream_chat(
                messages=history_payload,
                system_instruction=AI_TUTOR_SYSTEM_PROMPT,
                max_tokens=settings.AI_TUTOR_MAX_TOKENS,
            ):
                accumulated_text += chunk
                # Yield text chunk to client
                yield f"event: message\ndata: {json.dumps({'chunk': chunk}, ensure_ascii=False)}\n\n"

        except AIProviderError as e:
            logger.warning("AI Provider Error during stream: %s", e.message)
            yield f"event: error\ndata: {json.dumps({'error': e.message}, ensure_ascii=False)}\n\n"
            return
        except Exception as e:
            logger.error("Unexpected error in AI Tutor stream: %s", e)
            yield f"event: error\ndata: {json.dumps({'error': 'Có lỗi bất ngờ khi trao đổi với AI. Vui lòng thử lại.'}, ensure_ascii=False)}\n\n"
            return

        # 5. Extract & validate board illustration
        clean_text, board_data = extract_and_validate_board(accumulated_text)

        if board_data:
            yield f"event: board\ndata: {json.dumps({'board_data': board_data}, ensure_ascii=False)}\n\n"

        # 6. Save assistant message to Database & Cache
        async with async_session_factory() as db:
            asst_msg = ChatMessage(
                session_id=session_id,
                role="assistant",
                content=clean_text,
                board_data=board_data,
            )
            db.add(asst_msg)
            await db.commit()
            await db.refresh(asst_msg)
            msg_id = str(asst_msg.id)

        # Cache the validated response
        await set_cached_ai_response(request.message, clean_text, board_data)

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
