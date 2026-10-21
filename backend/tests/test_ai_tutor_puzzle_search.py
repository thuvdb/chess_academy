"""
Tests for AI Tutor Puzzle Search & Tool Calling (Giai đoạn 3).
"""
import uuid
import pytest
from unittest.mock import AsyncMock, MagicMock

import chess
from app.models.puzzle import Puzzle
from app.services.ai_tutor.puzzle_bank import search_approved_puzzles, normalize_difficulty
from app.services.ai_tutor.provider import MockLLMProvider


@pytest.mark.asyncio
async def test_search_approved_puzzles_enforces_limit_and_withholds_solution():
    """Verify search_approved_puzzles caps limit at 3 and does not reveal solutions."""
    # Mock db session with 5 verified puzzles
    mock_puzzles = []
    for i in range(5):
        p = MagicMock(spec=Puzzle)
        p.id = uuid.uuid4()
        # Valid starting position FEN
        p.fen = chess.STARTING_FEN
        p.title = f"Bài tập #{i}"
        p.difficulty = "easy"
        p.puzzle_type = "tactic"
        p.tags = ["pin", "tactic"]
        p.solution_verified = True
        p.rating = 1200
        mock_puzzles.append(p)

    mock_db = AsyncMock()
    # Mock recent attempts execution (empty)
    mock_recent_res = MagicMock()
    mock_recent_res.scalars.return_value.all.return_value = []
    
    # Mock candidate search execution
    mock_search_res = MagicMock()
    mock_search_res.scalars.return_value.all.return_value = mock_puzzles

    mock_db.execute.side_effect = [mock_recent_res, mock_search_res, mock_search_res]

    # Request limit 10 -> MUST be capped at 3
    results = await search_approved_puzzles(
        db=mock_db,
        user_id=uuid.uuid4(),
        theme="ghim",
        level="easy",
        limit=10,
    )

    assert len(results) <= 3
    for item in results:
        assert "fen" in item
        assert "side_to_move" in item
        assert "theme" in item
        assert "id" in item
        # Crucial security check: solution lines MUST NOT be present
        assert "moves_uci" not in item
        assert "solutions" not in item
        assert "solution_tree" not in item


@pytest.mark.asyncio
async def test_search_approved_puzzles_discards_invalid_fen():
    """Verify invalid FEN positions are safely filtered out using python-chess."""
    valid_p = MagicMock(spec=Puzzle)
    valid_p.id = uuid.uuid4()
    valid_p.fen = chess.STARTING_FEN
    valid_p.title = "Valid FEN"
    valid_p.difficulty = "easy"
    valid_p.puzzle_type = "tactic"
    valid_p.solution_verified = True
    valid_p.rating = 1200

    invalid_p = MagicMock(spec=Puzzle)
    invalid_p.id = uuid.uuid4()
    invalid_p.fen = "invalid/chess/fen/string"
    invalid_p.title = "Corrupt FEN"
    invalid_p.difficulty = "easy"
    invalid_p.puzzle_type = "tactic"
    invalid_p.solution_verified = True
    invalid_p.rating = 1200

    mock_db = AsyncMock()
    mock_recent_res = MagicMock()
    mock_recent_res.scalars.return_value.all.return_value = []
    
    mock_search_res = MagicMock()
    mock_search_res.scalars.return_value.all.return_value = [invalid_p, valid_p]

    mock_db.execute.side_effect = [mock_recent_res, mock_search_res, mock_search_res]

    results = await search_approved_puzzles(
        db=mock_db,
        user_id=uuid.uuid4(),
        theme="ghim",
        limit=2,
    )

    assert len(results) == 1
    assert results[0]["id"] == str(valid_p.id)


def test_normalize_difficulty():
    """Verify Vietnamese and English difficulty normalization."""
    assert normalize_difficulty("beginner") == "easy"
    assert normalize_difficulty("dễ") == "easy"
    assert normalize_difficulty("intermediate") == "medium"
    assert normalize_difficulty("trung bình") == "medium"
    assert normalize_difficulty("advanced") == "hard"
    assert normalize_difficulty("khó") == "hard"
    assert normalize_difficulty(None) is None


@pytest.mark.asyncio
async def test_mock_llm_provider_tool_handling():
    """Verify MockLLMProvider triggers tool handler when user asks for puzzles."""
    provider = MockLLMProvider()
    tool_called = False

    async def mock_tool_handler(name: str, args: dict):
        nonlocal tool_called
        if name == "search_puzzles":
            tool_called = True
            return {"puzzles_found": 2, "theme": args.get("theme", "ghim")}
        return {}

    chunks = []
    async for chunk in provider.stream_chat(
        messages=[{"role": "user", "content": "Thầy cho em xin 2 bài tập đòn ghim với ạ"}],
        system_instruction="System prompt",
        tool_handler=mock_tool_handler,
    ):
        chunks.append(chunk)

    assert tool_called is True
    full_text = "".join(chunks)
    assert "2 thế cờ" in full_text
    assert "ghim" in full_text.lower()
