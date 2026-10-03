"""
Smoke test for Sprint 3C: Piece Classifier + FEN Builder.
Run: $env:PYTHONIOENCODING='utf-8'; python tests/test_fen_builder.py
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))


def make_cell(square, row, col, piece="empty", confidence=0.95):
    """Helper to create a cell result dict."""
    return {
        "square": square,
        "row": row,
        "col": col,
        "piece": piece,
        "confidence": confidence,
        "method": "test",
    }


def make_starting_position():
    """Build 64 cell results for the standard starting position."""
    FILES = "abcdefgh"
    RANKS = "87654321"

    # Standard starting position from top (rank 8) to bottom (rank 1)
    board = [
        ["r", "n", "b", "q", "k", "b", "n", "r"],  # rank 8
        ["p", "p", "p", "p", "p", "p", "p", "p"],  # rank 7
        ["empty"] * 8,                                # rank 6
        ["empty"] * 8,                                # rank 5
        ["empty"] * 8,                                # rank 4
        ["empty"] * 8,                                # rank 3
        ["P", "P", "P", "P", "P", "P", "P", "P"],  # rank 2
        ["R", "N", "B", "Q", "K", "B", "N", "R"],  # rank 1
    ]

    cells = []
    for row in range(8):
        for col in range(8):
            square = f"{FILES[col]}{RANKS[row]}"
            piece = board[row][col]
            cells.append(make_cell(square, row, col, piece))
    return cells


def test_starting_position():
    """Test FEN generation for the standard starting position."""
    from app.services.fen_builder import build_fen_from_grid

    print("=" * 60)
    print("TEST: FEN Builder — Starting Position")
    print("=" * 60)

    cells = make_starting_position()
    result = build_fen_from_grid(cells, castling="KQkq")

    expected_fen = "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1"
    print(f"  Generated FEN: {result['fen_candidate']}")
    print(f"  Expected FEN:  {expected_fen}")
    print(f"  Validation:    {result['validation']}")
    print(f"  Errors:        {result['errors']}")

    assert result["fen_candidate"] == expected_fen, \
        f"FEN mismatch: {result['fen_candidate']}"
    assert result["validation"] == "valid", \
        f"Expected valid, got {result['validation']}: {result['errors']}"
    assert len(result["low_confidence_cells"]) == 0

    # Default: castling rights cannot be inferred from a scan -> "-"
    default_result = build_fen_from_grid(cells)
    assert default_result["fen_candidate"].split()[2] == "-", \
        f"Default castling should be '-': {default_result['fen_candidate']}"

    print("  [PASS] Starting position FEN")
    return True


def test_italian_game():
    """Test FEN for Italian Game position."""
    from app.services.fen_builder import build_fen_from_grid

    print("\n" + "=" * 60)
    print("TEST: FEN Builder — Italian Game")
    print("=" * 60)

    FILES = "abcdefgh"
    RANKS = "87654321"

    # Italian Game: 1.e4 e5 2.Nf3 Nc6 3.Bc4
    board = [
        ["r", "empty", "b", "q", "k", "b", "n", "r"],
        ["p", "p", "p", "p", "empty", "p", "p", "p"],
        ["empty", "empty", "n", "empty", "empty", "empty", "empty", "empty"],
        ["empty", "empty", "empty", "empty", "p", "empty", "empty", "empty"],
        ["empty", "empty", "B", "empty", "P", "empty", "empty", "empty"],
        ["empty", "empty", "empty", "empty", "empty", "N", "empty", "empty"],
        ["P", "P", "P", "P", "empty", "P", "P", "P"],
        ["R", "N", "B", "Q", "K", "empty", "empty", "R"],
    ]

    cells = []
    for row in range(8):
        for col in range(8):
            square = f"{FILES[col]}{RANKS[row]}"
            cells.append(make_cell(square, row, col, board[row][col]))

    result = build_fen_from_grid(cells, side_to_move="b", castling="KQkq")

    expected_fen = "r1bqkbnr/pppp1ppp/2n5/4p3/2B1P3/5N2/PPPP1PPP/RNBQK2R b KQkq - 0 1"
    print(f"  Generated FEN: {result['fen_candidate']}")
    print(f"  Expected FEN:  {expected_fen}")
    print(f"  Validation:    {result['validation']}")

    assert result["fen_candidate"] == expected_fen
    assert result["validation"] == "valid"

    print("  [PASS] Italian Game FEN")
    return True


def test_invalid_position():
    """Test FEN validation catches invalid positions."""
    from app.services.fen_builder import build_fen_from_grid

    print("\n" + "=" * 60)
    print("TEST: FEN Builder — Invalid Position (no king)")
    print("=" * 60)

    FILES = "abcdefgh"
    RANKS = "87654321"

    # Invalid: no black king
    board = [
        ["r", "n", "b", "q", "empty", "b", "n", "r"],  # no king!
        ["p", "p", "p", "p", "p", "p", "p", "p"],
        ["empty"] * 8,
        ["empty"] * 8,
        ["empty"] * 8,
        ["empty"] * 8,
        ["P", "P", "P", "P", "P", "P", "P", "P"],
        ["R", "N", "B", "Q", "K", "B", "N", "R"],
    ]

    cells = []
    for row in range(8):
        for col in range(8):
            square = f"{FILES[col]}{RANKS[row]}"
            cells.append(make_cell(square, row, col, board[row][col]))

    result = build_fen_from_grid(cells)
    print(f"  Generated FEN: {result['fen_candidate']}")
    print(f"  Validation:    {result['validation']}")
    print(f"  Errors:        {result['errors']}")

    # Should be invalid
    assert result["validation"] in ("invalid_position", "invalid_syntax"), \
        f"Expected invalid, got {result['validation']}"

    print("  [PASS] Invalid position detected")
    return True


def test_low_confidence_cells():
    """Test low confidence cell detection."""
    from app.services.fen_builder import build_fen_from_grid

    print("\n" + "=" * 60)
    print("TEST: FEN Builder — Low Confidence Cells")
    print("=" * 60)

    cells = make_starting_position()

    # Set some cells to low confidence
    cells[0]["confidence"] = 0.55   # a8 = r
    cells[3]["confidence"] = 0.63   # d8 = q
    cells[60]["confidence"] = 0.45  # e1 = K

    result = build_fen_from_grid(cells)
    print(f"  Low confidence cells: {len(result['low_confidence_cells'])}")
    for lc in result["low_confidence_cells"]:
        print(f"    {lc['square']} = {lc['piece']} ({lc['confidence']:.2f})")

    assert len(result["low_confidence_cells"]) == 3
    squares = [lc["square"] for lc in result["low_confidence_cells"]]
    assert "a8" in squares
    assert "d8" in squares
    assert "e1" in squares

    print("  [PASS] Low confidence detection")
    return True


def test_cell_confidence_map():
    """Test cell confidence map generation."""
    from app.services.fen_builder import build_cell_confidence_map

    print("\n" + "=" * 60)
    print("TEST: FEN Builder — Cell Confidence Map")
    print("=" * 60)

    cells = make_starting_position()
    cmap = build_cell_confidence_map(cells)

    assert len(cmap) == 64
    assert "a8" in cmap
    assert cmap["a8"]["piece"] == "r"
    assert cmap["a8"]["confidence"] == 0.95
    assert cmap["e4"]["piece"] == "empty"

    print(f"  Map size: {len(cmap)} entries")
    print(f"  a8: {cmap['a8']}")
    print(f"  e4: {cmap['e4']}")

    print("  [PASS] Cell confidence map")
    return True


if __name__ == "__main__":
    results = []

    results.append(("Starting Position", test_starting_position()))
    results.append(("Italian Game", test_italian_game()))
    results.append(("Invalid Position", test_invalid_position()))
    results.append(("Low Confidence Cells", test_low_confidence_cells()))
    results.append(("Cell Confidence Map", test_cell_confidence_map()))

    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    all_pass = True
    for name, passed in results:
        status = "[PASS]" if passed else "[FAIL]"
        print(f"  {status} -- {name}")
        if not passed:
            all_pass = False

    print()
    if all_pass:
        print("All tests PASSED")
    else:
        print("Some tests FAILED")
        sys.exit(1)
