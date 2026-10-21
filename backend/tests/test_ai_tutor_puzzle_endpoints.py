"""
Tests for AI Tutor Puzzle Interactive Endpoints (Giai đoạn 3).
"""
import uuid
import pytest
from unittest.mock import AsyncMock, MagicMock

import chess
from app.models.ai_tutor import AIPuzzleAttempt
from app.models.puzzle import Puzzle, PuzzleSolution
from app.services.ai_tutor.puzzle_bank import (
    check_puzzle_move,
    get_puzzle_solution,
    record_puzzle_attempt,
)


@pytest.mark.asyncio
async def test_check_puzzle_move_correct_with_opponent_reply():
    """Verify correct player move returns opponent counter-move and updated FEN."""
    puzzle_id = uuid.uuid4()
    user_id = uuid.uuid4()

    # Position: White to move and mate in 2
    # 1. Qh7+ Kf8 2. Qh8#
    fen = "r4rk1/5ppp/8/8/8/8/8/4Q1K1 w - - 0 1"
    board = chess.Board(fen)

    sol1 = PuzzleSolution(
        puzzle_id=puzzle_id,
        move_order=1,
        move_uci="e1h4",  # or say move 1
        move_san="Qh4",
        side="w",
        is_best_move=True,
    )
    sol2 = PuzzleSolution(
        puzzle_id=puzzle_id,
        move_order=2,
        move_uci="h7h6",
        move_san="h6",
        side="b",
        is_best_move=True,
    )

    puzzle = MagicMock(spec=Puzzle)
    puzzle.id = puzzle_id
    puzzle.fen = fen
    puzzle.solutions = [sol1, sol2]

    mock_db = AsyncMock()
    mock_res = MagicMock()
    mock_res.scalar_one_or_none.return_value = puzzle
    mock_db.execute.return_value = mock_res

    # Player plays Qh4 (UCI e1h4)
    result = await check_puzzle_move(
        db=mock_db,
        puzzle_id=puzzle_id,
        user_id=user_id,
        move_str="e1h4",
        current_fen=fen,
        step_index=0,
    )

    assert result["is_correct"] is True
    assert result["is_completed"] is False
    assert result["opponent_move"] is not None
    assert result["opponent_move"]["uci"] == "h7h6"
    assert result["next_fen"] != fen


@pytest.mark.asyncio
async def test_check_puzzle_move_wrong_move():
    """Verify wrong player move returns is_correct=False and maintains current FEN."""
    puzzle_id = uuid.uuid4()
    user_id = uuid.uuid4()
    fen = chess.STARTING_FEN

    sol1 = PuzzleSolution(
        puzzle_id=puzzle_id,
        move_order=1,
        move_uci="e2e4",
        move_san="e4",
        side="w",
        is_best_move=True,
    )

    puzzle = MagicMock(spec=Puzzle)
    puzzle.id = puzzle_id
    puzzle.fen = fen
    puzzle.solutions = [sol1]

    mock_db = AsyncMock()
    mock_res = MagicMock()
    mock_res.scalar_one_or_none.return_value = puzzle
    mock_db.execute.return_value = mock_res

    # Player plays d2d4 instead of e2e4
    result = await check_puzzle_move(
        db=mock_db,
        puzzle_id=puzzle_id,
        user_id=user_id,
        move_str="d2d4",
        current_fen=fen,
        step_index=0,
    )

    assert result["is_correct"] is False
    assert result["is_completed"] is False
    assert result["opponent_move"] is None
    assert result["next_fen"] == fen
    assert "chưa chính xác" in result["message"]


@pytest.mark.asyncio
async def test_get_puzzle_solution_returns_ordered_moves():
    """Verify get_puzzle_solution returns full ordered solution lines."""
    puzzle_id = uuid.uuid4()
    user_id = uuid.uuid4()

    sol1 = PuzzleSolution(
        puzzle_id=puzzle_id,
        move_order=1,
        move_uci="d5d7",
        move_san="Qd7+",
        side="w",
        explanation="Nước 1 của Trắng: Qd7+",
    )
    sol2 = PuzzleSolution(
        puzzle_id=puzzle_id,
        move_order=2,
        move_uci="c8b8",
        move_san="Kb8",
        side="b",
        explanation="Đáp trả của Đen: Kb8",
    )

    puzzle = MagicMock(spec=Puzzle)
    puzzle.id = puzzle_id
    puzzle.title = "Bài tập thí Hậu"
    puzzle.puzzle_type = "mate_in_2"
    puzzle.fen = chess.STARTING_FEN
    puzzle.solutions = [sol2, sol1]  # Out of order in list

    mock_db = AsyncMock()
    mock_res = MagicMock()
    mock_res.scalar_one_or_none.return_value = puzzle
    mock_db.execute.return_value = mock_res

    res = await get_puzzle_solution(
        db=mock_db,
        puzzle_id=puzzle_id,
        user_id=user_id,
    )

    assert res["puzzle_id"] == str(puzzle_id)
    assert res["title"] == "Bài tập thí Hậu"
    assert len(res["moves"]) == 2
    # Verify sorted by move_order
    assert res["moves"][0]["move_order"] == 1
    assert res["moves"][0]["san"] == "Qd7+"
    assert res["moves"][1]["move_order"] == 2
    assert res["moves"][1]["san"] == "Kb8"


@pytest.mark.asyncio
async def test_record_puzzle_attempt_tracks_stats():
    """Verify record_puzzle_attempt records and updates attempts_count and hints_used."""
    puzzle_id = uuid.uuid4()
    user_id = uuid.uuid4()

    mock_db = AsyncMock()
    mock_res = MagicMock()
    # Initially no attempt exists
    mock_res.scalars.return_value.first.return_value = None
    mock_db.execute.return_value = mock_res

    attempt = await record_puzzle_attempt(
        db=mock_db,
        user_id=user_id,
        puzzle_id=puzzle_id,
        is_correct=False,
        increment_attempt=True,
    )

    assert attempt.user_id == user_id
    assert attempt.puzzle_id == puzzle_id
    assert attempt.attempts_count == 1
    assert attempt.hints_used == 0
    assert attempt.is_correct is False
    assert mock_db.commit.called
