"""
CAMS AI Tutor — Puzzle Bank Integration Service.
Provides approved puzzle retrieval, FEN validation, move checking, and attempt tracking.
"""
import logging
import uuid
from typing import Any, Optional

import chess
from sqlalchemy import desc, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.ai_tutor import AIPuzzleAttempt
from app.models.puzzle import Puzzle, PuzzleSolution

logger = logging.getLogger(__name__)

# Keyword mappings for Vietnamese / English chess themes to internal tags and types
THEME_MAPPINGS: dict[str, dict[str, Any]] = {
    "ghim": {"tag": "pin", "types": ["tactic"]},
    "pin": {"tag": "pin", "types": ["tactic"]},
    "đòn ghim": {"tag": "pin", "types": ["tactic"]},
    "đòn đôi": {"tag": "fork", "types": ["tactic"]},
    "fork": {"tag": "fork", "types": ["tactic"]},
    "chĩa đôi": {"tag": "fork", "types": ["tactic"]},
    "bắt đôi": {"tag": "fork", "types": ["tactic"]},
    "xiên": {"tag": "skewer", "types": ["tactic"]},
    "skewer": {"tag": "skewer", "types": ["tactic"]},
    "chiếu mở": {"tag": "discovered_attack", "types": ["tactic"]},
    "discovered attack": {"tag": "discovered_attack", "types": ["tactic"]},
    "chiếu bí": {"types": ["mate_in_1", "mate_in_2", "mate_in_3", "mate_in_4"]},
    "chiếu hết": {"types": ["mate_in_1", "mate_in_2", "mate_in_3", "mate_in_4"]},
    "mate": {"types": ["mate_in_1", "mate_in_2", "mate_in_3", "mate_in_4"]},
    "mate in 1": {"types": ["mate_in_1"]},
    "mate in 2": {"types": ["mate_in_2"]},
    "mate in 3": {"types": ["mate_in_3"]},
    "mate in 4": {"types": ["mate_in_4"]},
    "tàn cuộc": {"types": ["endgame"], "tag": "endgame"},
    "endgame": {"types": ["endgame"], "tag": "endgame"},
    "khai cuộc": {"types": ["opening"], "tag": "opening"},
    "opening": {"types": ["opening"], "tag": "opening"},
}

DIFFICULTY_MAPPINGS: dict[str, str] = {
    "beginner": "easy",
    "easy": "easy",
    "dễ": "easy",
    "intermediate": "medium",
    "medium": "medium",
    "trung bình": "medium",
    "advanced": "hard",
    "hard": "hard",
    "khó": "hard",
    "expert": "expert",
}


def normalize_difficulty(level: Optional[str]) -> Optional[str]:
    """Map user/LLM level input to database difficulty enum string."""
    if not level:
        return None
    return DIFFICULTY_MAPPINGS.get(level.strip().lower())


async def search_approved_puzzles(
    db: AsyncSession,
    user_id: uuid.UUID,
    theme: str,
    level: Optional[str] = None,
    limit: int = 2,
) -> list[dict[str, Any]]:
    """
    Search approved puzzles from PostgreSQL Puzzle Bank.
    - Capped at maximum 3 puzzles.
    - Only solution_verified == True.
    - Excludes recently attempted puzzles if possible.
    - Validates FEN with python-chess.
    - Strictly withholds solution moves.
    """
    # Enforce backend limit: max 3, min 1
    max_count = min(max(1, limit or 2), 3)

    clean_theme = (theme or "").strip().lower()
    norm_level = normalize_difficulty(level)

    # Subquery: get IDs of recently attempted puzzles by this user (last 20 attempts)
    recent_attempts_stmt = (
        select(AIPuzzleAttempt.puzzle_id)
        .where(AIPuzzleAttempt.user_id == user_id)
        .order_by(desc(AIPuzzleAttempt.created_at))
        .limit(20)
    )
    recent_res = await db.execute(recent_attempts_stmt)
    recent_puzzle_ids = set(recent_res.scalars().all())

    # Build base filter
    stmt = (
        select(Puzzle)
        .options(selectinload(Puzzle.solutions))
        .where(Puzzle.solution_verified.is_(True))
    )

    if norm_level:
        stmt = stmt.where(Puzzle.difficulty == norm_level)

    # Resolve theme filters
    matched_mapping = THEME_MAPPINGS.get(clean_theme)
    theme_conditions = []

    if matched_mapping:
        if "types" in matched_mapping:
            theme_conditions.append(Puzzle.puzzle_type.in_(matched_mapping["types"]))
        if "tag" in matched_mapping:
            tag_val = matched_mapping["tag"]
            theme_conditions.append(Puzzle.tags.contains([tag_val]))
    else:
        # Flexible keyword search
        search_kw = f"%{clean_theme}%"
        theme_conditions.extend([
            Puzzle.title.ilike(search_kw),
            Puzzle.description.ilike(search_kw),
            Puzzle.puzzle_type.ilike(search_kw),
            Puzzle.tags.contains([clean_theme]),
        ])

    if theme_conditions:
        stmt = stmt.where(or_(*theme_conditions))

    # Try first excluding recently solved puzzles
    if recent_puzzle_ids:
        unseen_stmt = stmt.where(Puzzle.id.not_in(recent_puzzle_ids)).order_by(func.random()).limit(max_count * 2)
        res = await db.execute(unseen_stmt)
        candidates = list(res.scalars().all())
    else:
        candidates = []

    # If not enough unseen candidates, query without exclusion
    if len(candidates) < max_count:
        fallback_stmt = stmt.order_by(func.random()).limit(max_count * 2)
        fallback_res = await db.execute(fallback_stmt)
        for p in fallback_res.scalars().all():
            if p not in candidates:
                candidates.append(p)
            if len(candidates) >= max_count * 2:
                break

    # If still empty (theme not found), try general verified tactic puzzles as fallback pool
    # so we can inform or suggest
    valid_puzzles: list[dict[str, Any]] = []

    for p in candidates:
        if len(valid_puzzles) >= max_count:
            break

        # Validate FEN using python-chess
        try:
            board = chess.Board(p.fen)
            if not board.is_valid():
                logger.warning("Skipping puzzle %s with invalid FEN: %s", p.id, p.fen)
                continue
        except Exception as e:
            logger.warning("Error parsing FEN for puzzle %s: %s", p.id, e)
            continue

        turn = "w" if board.turn == chess.WHITE else "b"

        # Safe puzzle data payload for student — NO SOLUTION MOVES
        valid_puzzles.append({
            "id": str(p.id),
            "fen": p.fen,
            "side_to_move": turn,
            "theme": clean_theme or (p.puzzle_type or "Chiến thuật"),
            "title": p.title or f"Bài tập cờ thế #{str(p.id)[:8]}",
            "difficulty": p.difficulty or "easy",
            "rating": p.rating,
        })

    return valid_puzzles


async def record_puzzle_attempt(
    db: AsyncSession,
    user_id: uuid.UUID,
    puzzle_id: uuid.UUID,
    is_correct: bool,
    session_id: Optional[uuid.UUID] = None,
    increment_attempt: bool = True,
    increment_hint: bool = False,
) -> AIPuzzleAttempt:
    """Track or update student puzzle attempt for AI Tutor session."""
    stmt = (
        select(AIPuzzleAttempt)
        .where(
            AIPuzzleAttempt.user_id == user_id,
            AIPuzzleAttempt.puzzle_id == puzzle_id,
        )
    )
    if session_id:
        stmt = stmt.where(AIPuzzleAttempt.session_id == session_id)

    res = await db.execute(stmt.order_by(desc(AIPuzzleAttempt.created_at)))
    attempt = res.scalars().first()

    if not attempt:
        attempt = AIPuzzleAttempt(
            user_id=user_id,
            puzzle_id=puzzle_id,
            session_id=session_id,
            is_correct=is_correct,
            attempts_count=1 if increment_attempt else 0,
            hints_used=1 if increment_hint else 0,
        )
        db.add(attempt)
    else:
        if increment_attempt:
            attempt.attempts_count += 1
        if increment_hint:
            attempt.hints_used += 1
        if is_correct:
            attempt.is_correct = True

    await db.commit()
    await db.refresh(attempt)
    return attempt


async def check_puzzle_move(
    db: AsyncSession,
    puzzle_id: uuid.UUID,
    user_id: uuid.UUID,
    move_str: str,
    current_fen: str,
    step_index: int = 0,
    session_id: Optional[uuid.UUID] = None,
) -> dict[str, Any]:
    """
    Validate student move against puzzle solutions line.
    Handles player turn, computes next board FEN, and executes opponent counter-move if applicable.
    """
    # 1. Fetch puzzle with solutions
    stmt = (
        select(Puzzle)
        .options(selectinload(Puzzle.solutions))
        .where(Puzzle.id == puzzle_id)
    )
    res = await db.execute(stmt)
    puzzle = res.scalar_one_or_none()
    if not puzzle:
        raise ValueError("Thế cờ không tồn tại.")

    # 2. Parse board state and student move
    try:
        board = chess.Board(current_fen)
    except Exception as e:
        raise ValueError(f"FEN không hợp lệ: {e}")

    clean_move = (move_str or "").strip()
    try:
        move = chess.Move.from_uci(clean_move.lower())
        if move not in board.legal_moves:
            move = board.parse_san(clean_move)
    except Exception:
        try:
            move = board.parse_san(clean_move)
        except Exception:
            # Illegal move on the board
            await record_puzzle_attempt(
                db=db,
                user_id=user_id,
                puzzle_id=puzzle_id,
                is_correct=False,
                session_id=session_id,
            )
            return {
                "is_correct": False,
                "is_completed": False,
                "opponent_move": None,
                "next_fen": current_fen,
                "message": "Nước đi không hợp lệ theo luật cờ vua. Hãy thử lại!",
            }

    # 3. Match against expected solution line
    sorted_solutions = sorted(puzzle.solutions, key=lambda s: s.move_order)
    solutions_by_order = {s.move_order: s for s in sorted_solutions}

    # Expected order for student's move at this step: 1, 3, 5...
    expected_order = step_index * 2 + 1
    expected_sol = solutions_by_order.get(expected_order)

    user_uci = move.uci().lower()
    is_correct = False

    if expected_sol and expected_sol.move_uci.lower() == user_uci:
        is_correct = True
    elif board.is_checkmate():
        # Alternative move delivering checkmate is also accepted as correct
        is_correct = True

    if not is_correct:
        await record_puzzle_attempt(
            db=db,
            user_id=user_id,
            puzzle_id=puzzle_id,
            is_correct=False,
            session_id=session_id,
        )
        return {
            "is_correct": False,
            "is_completed": False,
            "opponent_move": None,
            "next_fen": current_fen,
            "message": "Nước đi chưa chính xác, con hãy quan sát kĩ và thử lại nhé!",
        }

    # 4. Move is correct! Apply to board
    board.push(move)

    if board.is_checkmate():
        await record_puzzle_attempt(
            db=db,
            user_id=user_id,
            puzzle_id=puzzle_id,
            is_correct=True,
            session_id=session_id,
        )
        return {
            "is_correct": True,
            "is_completed": True,
            "opponent_move": None,
            "next_fen": board.fen(),
            "message": "Chiếu hết! Con đã giải chính xác bài tập cờ thế này, rất xuất sắc!",
        }

    # Check if there is an opponent counter-move
    opp_order = expected_order + 1
    opp_sol = solutions_by_order.get(opp_order)

    if opp_sol:
        try:
            opp_move = chess.Move.from_uci(opp_sol.move_uci.lower())
            if opp_move in board.legal_moves:
                board.push(opp_move)
                return {
                    "is_correct": True,
                    "is_completed": False,
                    "opponent_move": {
                        "uci": opp_sol.move_uci,
                        "san": opp_sol.move_san,
                    },
                    "next_fen": board.fen(),
                    "message": f"Nước đi rất hay! Đối thủ đã đáp trả {opp_sol.move_san}.",
                }
        except Exception as e:
            logger.warning("Failed to play opponent counter move: %s", e)

    # If no further opponent moves or at end of line:
    await record_puzzle_attempt(
        db=db,
        user_id=user_id,
        puzzle_id=puzzle_id,
        is_correct=True,
        session_id=session_id,
    )
    return {
        "is_correct": True,
        "is_completed": True,
        "opponent_move": None,
        "next_fen": board.fen(),
        "message": "Tuyệt vời! Con đã hoàn thành tất cả các nước đi chính xác!",
    }


async def get_puzzle_solution(
    db: AsyncSession,
    puzzle_id: uuid.UUID,
    user_id: uuid.UUID,
    session_id: Optional[uuid.UUID] = None,
) -> dict[str, Any]:
    """Retrieve full official solution line for a puzzle when student requests it."""
    stmt = (
        select(Puzzle)
        .options(selectinload(Puzzle.solutions))
        .where(Puzzle.id == puzzle_id)
    )
    res = await db.execute(stmt)
    puzzle = res.scalar_one_or_none()
    if not puzzle:
        raise ValueError("Thế cờ không tồn tại.")

    sorted_solutions = sorted(puzzle.solutions, key=lambda s: s.move_order)

    # Record that student opened the solution
    await record_puzzle_attempt(
        db=db,
        user_id=user_id,
        puzzle_id=puzzle_id,
        is_correct=False,
        session_id=session_id,
        increment_attempt=False,
    )

    return {
        "puzzle_id": str(puzzle.id),
        "title": puzzle.title or "Bài tập cờ thế",
        "theme": puzzle.puzzle_type or "Chiến thuật",
        "fen": puzzle.fen,
        "moves": [
            {
                "move_order": s.move_order,
                "uci": s.move_uci,
                "san": s.move_san,
                "side": s.side or ("w" if s.move_order % 2 != 0 else "b"),
                "explanation": s.explanation or f"Nước {s.move_san}",
            }
            for s in sorted_solutions
        ],
    }


async def explain_puzzle_solution(
    db: AsyncSession,
    puzzle_id: uuid.UUID,
) -> str:
    """Generate LLM tactical explanation grounded strictly on the DB solution."""
    from app.services.ai_tutor.provider import get_llm_provider

    stmt = (
        select(Puzzle)
        .options(selectinload(Puzzle.solutions))
        .where(Puzzle.id == puzzle_id)
    )
    res = await db.execute(stmt)
    puzzle = res.scalar_one_or_none()
    if not puzzle:
        raise ValueError("Thế cờ không tồn tại.")

    sorted_solutions = sorted(puzzle.solutions, key=lambda s: s.move_order)
    moves_desc = []
    for s in sorted_solutions:
        who = "Trắng" if s.side == "w" else "Đen"
        moves_desc.append(f"Nước {s.move_order} ({who}): {s.move_san}")

    moves_str = "\n".join(moves_desc) if moves_desc else "Chiếu hết hoặc đòn chiến thuật."

    system_instruction = (
        "Bạn là Huấn luyện viên Cờ vua tại Học viện CAMS. "
        "Hãy giải thích ngắn gọn, dễ hiểu và truyền cảm hứng (3-5 câu) cho học viên nhỏ tuổi "
        "về ý đồ chiến thuật cốt lõi của bài tập cờ thế này. "
        "QUAN TRỌNG: Bám sát ĐÚNG chuỗi nước đi thực tế được cung cấp, không bịa thêm nước đi ngoài chuỗi."
    )

    user_prompt = (
        f"Thế cờ xuất phát: {puzzle.fen}\n"
        f"Chủ đề chiến thuật: {puzzle.puzzle_type or 'Chiến thuật'}\n"
        f"Chuỗi nước đi đáp án chuẩn xác từ kho bài tập CAMS:\n{moves_str}\n\n"
        "Hãy giải thích ý nghĩa chiến thuật đằng sau chuỗi nước đi trên cho học viên."
    )

    provider = get_llm_provider()
    chunks = []
    async for chunk in provider.stream_chat(
        messages=[{"role": "user", "content": user_prompt}],
        system_instruction=system_instruction,
        max_tokens=500,
    ):
        chunks.append(chunk)

    return "".join(chunks).strip()
