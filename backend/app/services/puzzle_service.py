"""
Puzzle Service — Sprint 4
Handles Puzzle CRUD, solution management, FEN validation, and Puzzle Rating calculation.
"""

import logging
import uuid
from typing import Optional

import chess
from sqlalchemy import desc, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.base import PuzzleDifficulty, PuzzleSource, PuzzleType, ReviewStatus
from app.models.puzzle import Puzzle, PuzzleSolution
from app.models.scan import ScanResult
from app.schemas.puzzle import (
    CreatePuzzleFromScanRequest,
    PuzzleCreate,
    PuzzleSolutionCreate,
    PuzzleUpdate,
)

logger = logging.getLogger(__name__)


# ── Rating Calculation ───────────────────────────────────────

def calculate_new_puzzle_rating(
    user_rating: int, puzzle_rating: int, solved: bool
) -> tuple[int, int]:
    """
    K-factor formula per Sprint 4 spec:
      - K = 32 if rating < 1200
      - K = 24 if rating < 2000
      - K = 16 if rating >= 2000
    Lưu ý: Puzzle Rating KHÔNG phải ELO. ELO chỉ thay đổi qua Tournament.
    """
    if user_rating < 1200:
        k = 32
    elif user_rating < 2000:
        k = 24
    else:
        k = 16

    expected_user = 1.0 / (1.0 + 10.0 ** ((puzzle_rating - user_rating) / 400.0))
    actual_user = 1.0 if solved else 0.0

    delta_user = round(k * (actual_user - expected_user))
    new_user_rating = max(100, user_rating + delta_user)

    # Adjust puzzle rating inversely (K_puzzle = 16)
    k_puzzle = 16
    expected_puzzle = 1.0 - expected_user
    actual_puzzle = 1.0 - actual_user
    delta_puzzle = round(k_puzzle * (actual_puzzle - expected_puzzle))
    new_puzzle_rating = max(100, puzzle_rating + delta_puzzle)

    return new_user_rating, new_puzzle_rating


# ── FEN Validation ───────────────────────────────────────────

def validate_puzzle_fen(fen: str) -> tuple[bool, str | None]:
    """Validates if FEN can be parsed and is legal."""
    try:
        board = chess.Board(fen)
        if not board.is_valid():
            return False, "Invalid board position according to chess rules"
        return True, None
    except ValueError as exc:
        return False, str(exc)


DIFFICULTY_MAP = {
    "beginner": "easy",
    "easy": "easy",
    "intermediate": "medium",
    "medium": "medium",
    "advanced": "hard",
    "hard": "hard",
    "master": "expert",
    "expert": "expert",
}

PUZZLE_TYPE_MAP = {
    "tactics": "tactic",
    "tactic": "tactic",
    "endgame": "endgame",
    "opening": "opening",
    "strategy": "strategy",
    "custom": "custom",
    "mate_in_1": "mate_in_1",
    "mate_in_2": "mate_in_2",
    "mate_in_3": "mate_in_3",
    "fork": "tactic",
    "pin": "tactic",
}

SOURCE_MAP = {
    "manual_fen": "manual_fen",
    "manual_pgn": "manual_pgn",
    "ai_scanned": "ai_scanned",
    "book_scan": "ai_scanned",
    "imported": "imported",
}


# ── CRUD Operations ──────────────────────────────────────────

async def create_puzzle(
    db: AsyncSession,
    created_by: uuid.UUID,
    data: PuzzleCreate,
) -> Puzzle:
    valid, err = validate_puzzle_fen(data.fen)
    if not valid:
        raise ValueError(f"Invalid FEN: {err}")

    diff = DIFFICULTY_MAP.get((data.difficulty or "").lower(), "easy")
    p_type = PUZZLE_TYPE_MAP.get((data.puzzle_type or "").lower(), "tactic")
    src = SOURCE_MAP.get((data.source or "").lower(), "manual_fen")

    puzzle = Puzzle(
        center_id=data.center_id,
        created_by=created_by,
        title=data.title,
        description=data.description,
        fen=data.fen,
        pgn=data.pgn,
        difficulty=diff,
        puzzle_type=p_type,
        source=src,
        tags=data.tags,
        rating=data.rating,
        board_image_url=data.board_image_url,
    )
    db.add(puzzle)
    await db.flush()

    # Add solutions if any
    if data.solutions:
        for sol in data.solutions:
            solution = PuzzleSolution(
                puzzle_id=puzzle.id,
                move_order=sol.move_order,
                move_uci=sol.move_uci,
                move_san=sol.move_san,
                is_best_move=sol.is_best_move,
                alternative_moves=sol.alternative_moves,
                explanation=sol.explanation,
            )
            db.add(solution)
    else:
        # Auto-generate solutions with Stockfish if not provided
        try:
            from app.services.stockfish_service import generate_puzzle_solutions
            auto_sols = generate_puzzle_solutions(data.fen)
            for s in auto_sols:
                solution = PuzzleSolution(
                    puzzle_id=puzzle.id,
                    move_order=s["move_order"],
                    move_uci=s["move_uci"],
                    move_san=s["move_san"],
                    is_best_move=s["is_best_move"],
                    explanation=s.get("explanation"),
                )
                db.add(solution)
        except Exception as exc:
            logger.warning(f"Could not auto-generate solutions: {exc}")

    await db.flush()
    await db.refresh(puzzle)
    return puzzle


async def get_puzzle(
    db: AsyncSession, puzzle_id: uuid.UUID
) -> Puzzle | None:
    stmt = (
        select(Puzzle)
        .options(selectinload(Puzzle.solutions))
        .where(Puzzle.id == puzzle_id)
    )
    result = await db.execute(stmt)
    puzzle = result.scalar_one_or_none()
    if puzzle and (not puzzle.solutions or len(puzzle.solutions) == 0):
        try:
            from app.services.stockfish_service import generate_puzzle_solutions
            auto_sols = generate_puzzle_solutions(puzzle.fen)
            if auto_sols:
                for s in auto_sols:
                    solution = PuzzleSolution(
                        puzzle_id=puzzle.id,
                        move_order=s["move_order"],
                        move_uci=s["move_uci"],
                        move_san=s["move_san"],
                        is_best_move=s["is_best_move"],
                        explanation=s.get("explanation"),
                    )
                    db.add(solution)
                await db.commit()
                stmt_reload = (
                    select(Puzzle)
                    .options(selectinload(Puzzle.solutions))
                    .where(Puzzle.id == puzzle_id)
                )
                res_reload = await db.execute(stmt_reload)
                puzzle = res_reload.scalar_one_or_none()
        except Exception as exc:
            logger.warning(f"Could not auto-generate solutions on get_puzzle: {exc}")
    return puzzle


async def list_puzzles(
    db: AsyncSession,
    difficulty: Optional[str] = None,
    puzzle_type: Optional[str] = None,
    search: Optional[str] = None,
    center_id: Optional[uuid.UUID] = None,
    skip: int = 0,
    limit: int = 50,
) -> list[Puzzle]:
    stmt = select(Puzzle).options(selectinload(Puzzle.solutions))

    if difficulty:
        norm_diff = DIFFICULTY_MAP.get(difficulty.lower(), difficulty.lower())
        stmt = stmt.where(Puzzle.difficulty == norm_diff)
    if puzzle_type:
        norm_type = PUZZLE_TYPE_MAP.get(puzzle_type.lower(), puzzle_type.lower())
        stmt = stmt.where(Puzzle.puzzle_type == norm_type)
    if center_id:
        stmt = stmt.where(or_(Puzzle.center_id == center_id, Puzzle.center_id.is_(None)))
    if search:
        search_fmt = f"%{search}%"
        stmt = stmt.where(
            or_(
                Puzzle.title.ilike(search_fmt),
                Puzzle.description.ilike(search_fmt),
            )
        )

    stmt = stmt.order_by(desc(Puzzle.created_at)).offset(skip).limit(limit)
    result = await db.execute(stmt)
    return list(result.scalars().all())


async def update_puzzle(
    db: AsyncSession,
    puzzle: Puzzle,
    data: PuzzleUpdate,
) -> Puzzle:
    if data.fen is not None:
        valid, err = validate_puzzle_fen(data.fen)
        if not valid:
            raise ValueError(f"Invalid FEN: {err}")
        puzzle.fen = data.fen

    if data.title is not None:
        puzzle.title = data.title
    if data.description is not None:
        puzzle.description = data.description
    if data.pgn is not None:
        puzzle.pgn = data.pgn
    if data.difficulty is not None:
        puzzle.difficulty = DIFFICULTY_MAP.get(data.difficulty.lower(), "easy")
    if data.puzzle_type is not None:
        puzzle.puzzle_type = PUZZLE_TYPE_MAP.get(data.puzzle_type.lower(), "tactic")
    if data.tags is not None:
        puzzle.tags = data.tags
    if data.rating is not None:
        puzzle.rating = data.rating
    if data.board_image_url is not None:
        puzzle.board_image_url = data.board_image_url

    if data.solutions is not None:
        # Clear existing solutions
        existing_stmt = select(PuzzleSolution).where(PuzzleSolution.puzzle_id == puzzle.id)
        existing = await db.execute(existing_stmt)
        for old in existing.scalars().all():
            await db.delete(old)

        for sol in data.solutions:
            new_sol = PuzzleSolution(
                puzzle_id=puzzle.id,
                move_order=sol.move_order,
                move_uci=sol.move_uci,
                move_san=sol.move_san,
                is_best_move=sol.is_best_move,
                alternative_moves=sol.alternative_moves,
                explanation=sol.explanation,
            )
            db.add(new_sol)

    await db.flush()
    await db.refresh(puzzle)
    return puzzle


async def delete_puzzle(db: AsyncSession, puzzle: Puzzle) -> None:
    # Delete solutions
    stmt = select(PuzzleSolution).where(PuzzleSolution.puzzle_id == puzzle.id)
    solutions = await db.execute(stmt)
    for s in solutions.scalars().all():
        await db.delete(s)

    await db.delete(puzzle)
    await db.flush()


async def create_puzzle_from_scan(
    db: AsyncSession,
    user_id: uuid.UUID,
    req: CreatePuzzleFromScanRequest,
    center_id: Optional[uuid.UUID] = None,
) -> Puzzle:
    """Converts an approved ScanResult into a Puzzle."""
    scan_stmt = select(ScanResult).where(ScanResult.id == req.scan_result_id)
    res = await db.execute(scan_stmt)
    scan_res = res.scalar_one_or_none()
    if not scan_res:
        raise ValueError("Scan result not found")

    # If already created, return existing
    if scan_res.puzzle_id:
        existing = await get_puzzle(db, scan_res.puzzle_id)
        if existing:
            return existing

    target_fen = scan_res.fen_final or scan_res.fen_candidate
    if not target_fen:
        raise ValueError("Scan result has no FEN")

    puzzle_data = PuzzleCreate(
        title=req.title,
        description=req.description,
        fen=target_fen,
        difficulty=req.difficulty,
        puzzle_type=req.puzzle_type,
        source=PuzzleSource.AI_SCANNED.value,
        tags=req.tags,
        board_image_url=scan_res.board_image_url,
        solutions=req.solutions,
        center_id=center_id,
    )

    puzzle = await create_puzzle(db, created_by=user_id, data=puzzle_data)

    # Link back to scan result
    scan_res.puzzle_id = puzzle.id
    scan_res.review_status = ReviewStatus.APPROVED.value
    await db.flush()

    return puzzle
