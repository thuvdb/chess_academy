"""
Smoke test for Sprint 3A pipeline: PDF rendering + Board Detection.
Run: python tests/test_scan_pipeline.py

Creates a synthetic chessboard-like image, passes it through board_detector,
and validates the output contract.
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import numpy as np


def create_synthetic_chessboard_image(size=640, border=40):
    """Create a synthetic image with a chessboard pattern for testing."""
    import cv2

    # White background
    img = np.ones((size + border * 2, size + border * 2, 3), dtype=np.uint8) * 220

    cell_size = size // 8
    for row in range(8):
        for col in range(8):
            if (row + col) % 2 == 1:
                x1 = border + col * cell_size
                y1 = border + row * cell_size
                cv2.rectangle(img, (x1, y1), (x1 + cell_size, y1 + cell_size), (60, 60, 60), -1)
            else:
                x1 = border + col * cell_size
                y1 = border + row * cell_size
                cv2.rectangle(img, (x1, y1), (x1 + cell_size, y1 + cell_size), (240, 240, 240), -1)

    # Draw board border
    cv2.rectangle(img, (border, border), (border + size, border + size), (30, 30, 30), 3)

    return img


def test_board_detector():
    """Test board detection on synthetic chessboard image."""
    import cv2
    from app.services.board_detector import detect_boards

    print("=" * 60)
    print("TEST: Board Detector")
    print("=" * 60)

    # Create synthetic image
    img = create_synthetic_chessboard_image(640, 40)
    _, png_bytes = cv2.imencode(".png", img)
    png_bytes = png_bytes.tobytes()

    print(f"  Image size: {img.shape[1]}x{img.shape[0]}")
    print(f"  PNG bytes: {len(png_bytes)}")

    # Detect boards
    boards = detect_boards(png_bytes)

    print(f"  Boards found: {len(boards)}")
    assert len(boards) >= 1, "Expected at least 1 board detected"

    for b in boards:
        print(f"    Board {b['board_index']}: "
              f"({b['x']},{b['y']}) {b['width']}x{b['height']} "
              f"conf={b['confidence']:.4f}")

        # Validate output contract
        assert "x" in b and isinstance(b["x"], int)
        assert "y" in b and isinstance(b["y"], int)
        assert "width" in b and isinstance(b["width"], int)
        assert "height" in b and isinstance(b["height"], int)
        assert "confidence" in b and isinstance(b["confidence"], float)
        assert "board_index" in b and isinstance(b["board_index"], int)
        assert 0.0 <= b["confidence"] <= 1.0

    print("  ✓ Board detection PASSED")
    return True


def test_pdf_rendering():
    """Test PDF rendering with a synthetic single-page PDF."""
    import asyncio

    print("\n" + "=" * 60)
    print("TEST: PDF Rendering (PyMuPDF)")
    print("=" * 60)

    try:
        try:
            import pymupdf as fitz
        except ImportError:
            import fitz
    except ImportError:
        print("  ✗ PyMuPDF not installed — SKIPPED")
        return False

    # Create a minimal PDF with a drawn chessboard pattern
    doc = fitz.open()
    page = doc.new_page(width=595, height=842)  # A4

    # Draw a simple 8x8 grid (chessboard-like)
    board_x, board_y = 100, 200
    cell = 50
    for row in range(8):
        for col in range(8):
            x0 = board_x + col * cell
            y0 = board_y + row * cell
            rect = fitz.Rect(x0, y0, x0 + cell, y0 + cell)
            if (row + col) % 2 == 1:
                page.draw_rect(rect, color=(0, 0, 0), fill=(0.2, 0.2, 0.2))
            else:
                page.draw_rect(rect, color=(0, 0, 0), fill=(0.95, 0.95, 0.95))

    # Draw border
    border = fitz.Rect(board_x, board_y, board_x + 8 * cell, board_y + 8 * cell)
    page.draw_rect(border, color=(0, 0, 0), width=2)

    pdf_bytes = doc.tobytes()
    doc.close()

    print(f"  Synthetic PDF: {len(pdf_bytes)} bytes, 1 page")

    # Test render
    from app.services.pdf_service import render_pdf_pages

    pages = asyncio.run(render_pdf_pages(pdf_bytes, "test-job-001", dpi=150))

    print(f"  Rendered pages: {len(pages)}")
    assert len(pages) == 1, f"Expected 1 page, got {len(pages)}"

    p = pages[0]
    print(f"    Page {p['page_number']}: {p['width']}x{p['height']} → {p['image_url']}")
    assert p["page_number"] == 1
    assert p["width"] > 0 and p["height"] > 0
    assert p["image_url"].endswith(".png")

    print("  ✓ PDF rendering PASSED")
    return True


def test_pipeline_integration():
    """Integration: PDF → render page → detect boards."""
    import asyncio

    print("\n" + "=" * 60)
    print("TEST: Pipeline Integration (PDF → Render → Detect)")
    print("=" * 60)

    try:
        try:
            import pymupdf as fitz
        except ImportError:
            import fitz
    except ImportError:
        print("  ✗ PyMuPDF not installed — SKIPPED")
        return False

    # Create PDF with chessboard
    doc = fitz.open()
    page = doc.new_page(width=595, height=842)
    board_x, board_y = 80, 180
    cell = 55
    for row in range(8):
        for col in range(8):
            x0 = board_x + col * cell
            y0 = board_y + row * cell
            rect = fitz.Rect(x0, y0, x0 + cell, y0 + cell)
            if (row + col) % 2 == 1:
                page.draw_rect(rect, color=(0, 0, 0), fill=(0.15, 0.15, 0.15))
            else:
                page.draw_rect(rect, color=(0, 0, 0), fill=(1.0, 1.0, 0.9))
    border = fitz.Rect(board_x, board_y, board_x + 8 * cell, board_y + 8 * cell)
    page.draw_rect(border, color=(0, 0, 0), width=3)
    pdf_bytes = doc.tobytes()
    doc.close()

    # Step 1: Render PDF pages
    from app.services.pdf_service import render_pdf_pages, get_local_file_bytes
    from app.services.board_detector import detect_boards

    pages = asyncio.run(render_pdf_pages(pdf_bytes, "test-integration-001", dpi=200))
    print(f"  Pages rendered: {len(pages)}")

    total_boards = 0
    for p in pages:
        page_bytes = get_local_file_bytes(p["image_url"])
        boards = detect_boards(page_bytes)
        total_boards += len(boards)
        for b in boards:
            print(f"    Page {p['page_number']}, Board {b['board_index']}: "
                  f"({b['x']},{b['y']}) {b['width']}x{b['height']} "
                  f"conf={b['confidence']:.4f}")

    print(f"  Total boards detected: {total_boards}")
    assert total_boards >= 1, "Expected at least 1 board in pipeline"

    print("  ✓ Pipeline integration PASSED")
    return True


if __name__ == "__main__":
    results = []

    results.append(("Board Detector", test_board_detector()))
    results.append(("PDF Rendering", test_pdf_rendering()))
    results.append(("Pipeline Integration", test_pipeline_integration()))

    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    all_pass = True
    for name, passed in results:
        status = "✓ PASS" if passed else "✗ FAIL"
        print(f"  {status} — {name}")
        if not passed:
            all_pass = False

    print()
    if all_pass:
        print("All tests PASSED ✓")
    else:
        print("Some tests FAILED ✗")
        sys.exit(1)
