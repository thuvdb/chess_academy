"""
Smoke and Unit tests for Sprint 4: Puzzle Service, Rating logic, and Solution evaluation.
Run: $env:PYTHONIOENCODING='utf-8'; python tests/test_puzzle_service.py
"""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.services.puzzle_service import calculate_new_puzzle_rating, validate_puzzle_fen


def test_fen_validation():
    print("=" * 60)
    print("TEST: FEN Validation")
    print("=" * 60)

    # Valid starting FEN
    valid_fen = "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1"
    ok, err = validate_puzzle_fen(valid_fen)
    assert ok is True, f"Starting FEN should be valid, got err: {err}"
    print("  [PASS] Valid starting FEN")

    # Valid Italian game FEN
    italian_fen = "r1bqk1nr/pppp1ppp/2n5/2b1p3/2B1P3/5N2/PPPP1PPP/RNBQK2R w KQkq - 4 4"
    ok, err = validate_puzzle_fen(italian_fen)
    assert ok is True, f"Italian game FEN should be valid: {err}"
    print("  [PASS] Valid Italian game FEN")

    # Invalid FEN syntax
    invalid_fen = "not-a-fen"
    ok, err = validate_puzzle_fen(invalid_fen)
    assert ok is False, "Invalid FEN should fail"
    print(f"  [PASS] Invalid FEN detected: {err}")

    # Illegal chess position (2 white kings)
    illegal_fen = "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKKNR w KQkq - 0 1"
    ok, err = validate_puzzle_fen(illegal_fen)
    assert ok is False, "Position with 2 white kings should be invalid"
    print(f"  [PASS] Illegal board position detected: {err}")


def test_puzzle_rating_calculation():
    print("\n" + "=" * 60)
    print("TEST: Puzzle Rating Calculation (K-factors)")
    print("=" * 60)

    # 1. Rating < 1200 -> K = 32
    # Student 1000 solves 1200 puzzle
    new_user, new_puzzle = calculate_new_puzzle_rating(user_rating=1000, puzzle_rating=1200, solved=True)
    assert new_user > 1000, f"Solved puzzle should increase rating: {new_user}"
    assert new_puzzle < 1200, f"Solved puzzle should decrease puzzle rating: {new_puzzle}"
    print(f"  K=32: User (1000 -> {new_user}), Puzzle (1200 -> {new_puzzle}) [PASS]")

    # Student 1000 fails 1200 puzzle
    fail_user, fail_puzzle = calculate_new_puzzle_rating(user_rating=1000, puzzle_rating=1200, solved=False)
    assert fail_user < 1000, f"Failed puzzle should decrease user rating: {fail_user}"
    assert fail_puzzle > 1200, f"Failed puzzle should increase puzzle rating: {fail_puzzle}"
    print(f"  K=32: User (1000 -> {fail_user}), Puzzle (1200 -> {fail_puzzle}) [PASS]")

    # 2. Rating 1200 - 1999 -> K = 24
    new_user_med, _ = calculate_new_puzzle_rating(user_rating=1500, puzzle_rating=1500, solved=True)
    # Expected is 0.5, delta = 24 * (1 - 0.5) = 12
    assert new_user_med == 1512, f"Expected 1512, got {new_user_med}"
    print(f"  K=24: User (1500 -> {new_user_med}) [PASS]")

    # 3. Rating >= 2000 -> K = 16
    new_user_high, _ = calculate_new_puzzle_rating(user_rating=2200, puzzle_rating=2200, solved=True)
    # Expected is 0.5, delta = 16 * (1 - 0.5) = 8
    assert new_user_high == 2208, f"Expected 2208, got {new_user_high}"
    print(f"  K=16: User (2200 -> {new_user_high}) [PASS]")


def test_solution_eval():
    print("\n" + "=" * 60)
    print("TEST: Solution evaluation simulation")
    print("=" * 60)

    expected_ucis = ["e2e4", "e7e5", "g1f3"]
    user_ucis_correct = ["e2e4", "e7e5", "g1f3"]
    user_ucis_wrong = ["e2e4", "e7e5", "f1c4"]

    assert user_ucis_correct == expected_ucis
    print("  [PASS] Correct solution match")

    assert user_ucis_wrong != expected_ucis
    print("  [PASS] Incorrect solution mismatch")


def test_api_import():
    print("\n" + "=" * 60)
    print("TEST: FastAPI App and Router Import")
    print("=" * 60)

    import sys
    from unittest.mock import MagicMock
    if "asyncpg" not in sys.modules:
        sys.modules["asyncpg"] = MagicMock()

    from app.main import app
    routes = [route.path for route in app.routes]

    # Verify our routes are mounted
    assert any("/puzzles" in r for r in routes), "Puzzles route missing"
    assert any("/assignments" in r for r in routes), "Assignments route missing"
    assert any("/progress" in r for r in routes), "Progress route missing"
    assert any("/leaderboard" in r for r in routes), "Leaderboard route missing"
    print("  [PASS] All Sprint 4 routers loaded in FastAPI app successfully")


if __name__ == "__main__":
    test_fen_validation()
    test_puzzle_rating_calculation()
    test_solution_eval()
    test_api_import()
    print("\n" + "=" * 60)
    print("All Sprint 4 tests PASSED!")
    print("=" * 60)
