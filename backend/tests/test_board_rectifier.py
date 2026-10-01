"""
Smoke test for Sprint 3B: Board Rectifier.
Run: $env:PYTHONIOENCODING='utf-8'; python tests/test_board_rectifier.py
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import numpy as np


def create_synthetic_chessboard(size=640, border=40):
    """Create a synthetic chessboard image for testing."""
    import cv2

    img = np.ones((size + border * 2, size + border * 2, 3), dtype=np.uint8) * 200
    cell = size // 8

    for row in range(8):
        for col in range(8):
            x1 = border + col * cell
            y1 = border + row * cell
            color = (60, 60, 60) if (row + col) % 2 == 1 else (240, 240, 240)
            cv2.rectangle(img, (x1, y1), (x1 + cell, y1 + cell), color, -1)

    cv2.rectangle(img, (border, border), (border + size, border + size), (30, 30, 30), 3)
    return img


def test_rectify_basic():
    """Test rectification on a synthetic chessboard."""
    from app.services.board_rectifier import rectify_board, RECTIFIED_SIZE, CELL_SIZE

    print("=" * 60)
    print("TEST: Board Rectifier — Basic")
    print("=" * 60)

    img = create_synthetic_chessboard(640, 40)
    bbox = {"x": 38, "y": 38, "width": 644, "height": 644}  # ~where board is

    result = rectify_board(img, bbox)

    # Check rectified image dimensions
    rectified = result["rectified_image"]
    assert rectified.shape == (RECTIFIED_SIZE, RECTIFIED_SIZE, 3), \
        f"Expected {RECTIFIED_SIZE}x{RECTIFIED_SIZE}x3, got {rectified.shape}"
    print(f"  Rectified image: {rectified.shape[1]}x{rectified.shape[0]}")

    # Check cells
    cells = result["cells"]
    assert len(cells) == 64, f"Expected 64 cells, got {len(cells)}"

    # Check cell dimensions and naming
    for cell in cells:
        assert cell["image"].shape == (CELL_SIZE, CELL_SIZE, 3), \
            f"Cell {cell['square']}: expected {CELL_SIZE}x{CELL_SIZE}x3, got {cell['image'].shape}"
        assert len(cell["square"]) == 2
        assert cell["square"][0] in "abcdefgh"
        assert cell["square"][1] in "12345678"

    # Verify corner cells
    corners_expected = ["a8", "h8", "a1", "h1"]
    corner_squares = [cells[0]["square"], cells[7]["square"],
                      cells[56]["square"], cells[63]["square"]]
    assert corner_squares == corners_expected, \
        f"Corner cells: expected {corners_expected}, got {corner_squares}"

    print(f"  Cells: {len(cells)} (all {CELL_SIZE}x{CELL_SIZE})")
    print(f"  Corner cells: {corner_squares}")

    # Check that dark/light cells have different average brightness
    a8 = cells[0]["image"]  # should be light (a8 is light square)
    b8 = cells[1]["image"]  # should be dark
    a8_brightness = np.mean(a8)
    b8_brightness = np.mean(b8)
    print(f"  a8 avg brightness: {a8_brightness:.1f}")
    print(f"  b8 avg brightness: {b8_brightness:.1f}")

    # They should be distinctly different
    assert abs(a8_brightness - b8_brightness) > 30, \
        f"Expected distinct light/dark difference, got delta={abs(a8_brightness - b8_brightness):.1f}"

    print("  [PASS] Board Rectifier basic test")
    return True


def test_rectify_with_save():
    """Test rectification with saving to disk."""
    from app.services.board_rectifier import rectify_board

    print("\n" + "=" * 60)
    print("TEST: Board Rectifier — Save to disk")
    print("=" * 60)

    img = create_synthetic_chessboard(640, 40)
    bbox = {"x": 38, "y": 38, "width": 644, "height": 644}

    result = rectify_board(
        img, bbox,
        save_dir="test",
        job_id="test-rectifier-001",
        page_number=1,
        board_index=0,
    )

    assert result["rectified_url"] is not None
    print(f"  Rectified URL: {result['rectified_url']}")

    saved_cells = [c for c in result["cells"] if c["cell_url"]]
    print(f"  Saved cells: {len(saved_cells)}/64")
    assert len(saved_cells) == 64

    # Spot check a few cell URLs
    print(f"    a8: {result['cells'][0]['cell_url']}")
    print(f"    e4: {result['cells'][36]['cell_url']}")

    print("  [PASS] Board Rectifier save test")
    return True


def test_pipeline_detect_then_rectify():
    """Integration: detect boards then rectify each one."""
    import cv2
    from app.services.board_detector import detect_boards
    from app.services.board_rectifier import rectify_board

    print("\n" + "=" * 60)
    print("TEST: Pipeline — Detect then Rectify")
    print("=" * 60)

    img = create_synthetic_chessboard(640, 40)
    _, png_bytes = cv2.imencode(".png", img)
    png_bytes = png_bytes.tobytes()

    # Step 1: Detect
    boards = detect_boards(png_bytes)
    print(f"  Detected boards: {len(boards)}")
    assert len(boards) >= 1

    # Step 2: Rectify each
    for b in boards:
        result = rectify_board(img, b)
        rectified = result["rectified_image"]
        cells = result["cells"]
        print(f"    Board {b['board_index']}: "
              f"rectified {rectified.shape[1]}x{rectified.shape[0]}, "
              f"{len(cells)} cells")
        assert rectified.shape[:2] == (640, 640)
        assert len(cells) == 64

    print("  [PASS] Pipeline detect-then-rectify test")
    return True


if __name__ == "__main__":
    results = []

    results.append(("Rectifier Basic", test_rectify_basic()))
    results.append(("Rectifier Save", test_rectify_with_save()))
    results.append(("Detect + Rectify Pipeline", test_pipeline_detect_then_rectify()))

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
