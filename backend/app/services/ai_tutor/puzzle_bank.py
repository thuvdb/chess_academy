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
