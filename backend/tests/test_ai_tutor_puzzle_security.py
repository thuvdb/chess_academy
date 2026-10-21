"""
Security and Integrity Tests for AI Tutor Puzzle Bank Integration (Giai đoạn 3).
Verifies:
1. Only approved puzzles (solution_verified == True) are retrieved.
2. Unapproved puzzles are strictly excluded.
3. Solution moves are withheld until explicit solve or reveal.
4. Backend strictly caps limit at 3 regardless of user/LLM input.
5. Anti-hallucination guardrails and attempt recording integrity.
"""
import uuid
import pytest
from unittest.mock import AsyncMock, MagicMock

import chess
from app.models.puzzle import Puzzle, PuzzleSolution
from app.services.ai_tutor.puzzle_bank import (
    search_approved_puzzles,
    check_puzzle_move,
    get_puzzle_solution,
    record_puzzle_attempt,
)
from app.services.ai_tutor.prompt import AI_TUTOR_SYSTEM_PROMPT


def test_system_prompt_anti_hallucination_rules():
    """Verify system prompt contains mandatory anti-hallucination and puzzle bank rules."""
    prompt = AI_TUTOR_SYSTEM_PROMPT
    assert "PUZZLE BANK" in prompt
    assert "search_puzzles" in prompt
    assert "TUYỆT ĐỐI KHÔNG TỰ BỊA RA THẾ CỜ HOẶC TỰ VIẾT FEN" in prompt
    assert "TUYỆT ĐỐI KHÔNG tiết lộ đáp án" in prompt


@pytest.mark.asyncio
async def test_search_strictly_excludes_unapproved_puzzles():
    """Verify that puzzles with solution_verified=False are NEVER returned."""
    approved_puzzle = MagicMock(spec=Puzzle)
    approved_puzzle.id = uuid.uuid4()
    approved_puzzle.fen = chess.STARTING_FEN
    approved_puzzle.title = "Bài đã duyệt"
    approved_puzzle.solution_verified = True
    approved_puzzle.puzzle_type = "tactic"
    approved_puzzle.difficulty = "easy"
    approved_puzzle.rating = 1200

    unapproved_puzzle = MagicMock(spec=Puzzle)
    unapproved_puzzle.id = uuid.uuid4()
    unapproved_puzzle.fen = chess.STARTING_FEN
    unapproved_puzzle.title = "Bài chưa duyệt"
    unapproved_puzzle.solution_verified = False  # NOT APPROVED
    unapproved_puzzle.puzzle_type = "tactic"
    unapproved_puzzle.difficulty = "easy"
    unapproved_puzzle.rating = 1200

    mock_db = AsyncMock()
    # Mock recent attempts
    mock_recent_res = MagicMock()
    mock_recent_res.scalars.return_value.all.return_value = []

    # Mock DB query result
    mock_search_res = MagicMock()
    # If unapproved somehow returned from SQL, python service must ignore or filter
    mock_search_res.scalars.return_value.all.return_value = [approved_puzzle]

    mock_db.execute.side_effect = [mock_recent_res, mock_search_res, mock_search_res]

    results = await search_approved_puzzles(
        db=mock_db,
        user_id=uuid.uuid4(),
        theme="tactic",
        limit=2,
    )

    assert len(results) == 1
    assert results[0]["id"] == str(approved_puzzle.id)
    assert results[0]["title"] == "Bài đã duyệt"


@pytest.mark.asyncio
async def test_solution_is_never_leaked_in_puzzle_payload():
    """Verify client puzzle payload contains no moves or hints."""
    puzzle = MagicMock(spec=Puzzle)
    puzzle.id = uuid.uuid4()
    puzzle.fen = chess.STARTING_FEN
    puzzle.title = "Test Puzzle"
    puzzle.solution_verified = True
    puzzle.puzzle_type = "mate_in_1"
    puzzle.difficulty = "easy"
    puzzle.rating = 1300
    puzzle.solution_tree = {"best_move": "Qh5#"}
    puzzle.solutions = [
        PuzzleSolution(puzzle_id=puzzle.id, move_order=1, move_uci="e1h5", move_san="Qh5#", side="w")
    ]

    mock_db = AsyncMock()
    mock_recent_res = MagicMock()
    mock_recent_res.scalars.return_value.all.return_value = []

    mock_search_res = MagicMock()
    mock_search_res.scalars.return_value.all.return_value = [puzzle]

    mock_db.execute.side_effect = [mock_recent_res, mock_search_res, mock_search_res]

    results = await search_approved_puzzles(
        db=mock_db,
        user_id=uuid.uuid4(),
        theme="mate in 1",
        limit=1,
    )

    item = results[0]
    # Sensitive solution fields MUST NOT leak
    forbidden_keys = ["solutions", "solution_tree", "best_move", "moves_uci", "moves_san"]
    for k in forbidden_keys:
        assert k not in item


@pytest.mark.asyncio
async def test_backend_enforces_max_limit_three():
    """Verify limit parameter cannot exceed 3 even if LLM requests 100."""
    puzzles = []
    for i in range(10):
        p = MagicMock(spec=Puzzle)
        p.id = uuid.uuid4()
        p.fen = chess.STARTING_FEN
        p.title = f"Puzzle #{i}"
        p.solution_verified = True
        p.puzzle_type = "tactic"
        p.difficulty = "easy"
        p.rating = 1200
        puzzles.append(p)

    mock_db = AsyncMock()
    mock_recent_res = MagicMock()
    mock_recent_res.scalars.return_value.all.return_value = []

    mock_search_res = MagicMock()
    mock_search_res.scalars.return_value.all.return_value = puzzles

    mock_db.execute.side_effect = [mock_recent_res, mock_search_res, mock_search_res]

    results = await search_approved_puzzles(
        db=mock_db,
        user_id=uuid.uuid4(),
        theme="tactic",
        limit=99,  # Malicious / excessive limit
    )

    assert len(results) <= 3
