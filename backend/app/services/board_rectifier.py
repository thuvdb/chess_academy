"""
Board Rectifier — Sprint 3B
Takes a detected board region and produces a rectified 640×640 image,
then slices it into 64 cells (80×80 each).

Algorithm:
  1. Crop board from source image using bounding box
  2. Detect 4 corners via corner refinement (Harris / Shi-Tomasi)
  3. Perspective transform → square 640×640
  4. Slice into 8×8 grid → 64 cells (80×80 each)

Output contract:
  {
    "rectified_image": np.ndarray (640×640×3 BGR),
    "rectified_url": str | None,
    "cells": [
      {
        "square": "a8",  # algebraic notation
        "row": 0,        # 0=top (rank 8), 7=bottom (rank 1)
        "col": 0,        # 0=left (file a), 7=right (file h)
        "image": np.ndarray (80×80×3 BGR),
        "cell_url": str | None,
      },
      ...  # 64 entries
    ]
  }
"""

import logging
import time
from typing import Optional

import numpy as np

logger = logging.getLogger(__name__)

# ── Constants ──────────────────────────────────────────────
RECTIFIED_SIZE = 640       # Output square dimension
CELL_SIZE = RECTIFIED_SIZE // 8   # 80 px per cell

# Algebraic notation: row 0 = rank 8 (top), row 7 = rank 1 (bottom)
FILES = "abcdefgh"
RANKS = "87654321"   # top-to-bottom


def _crop_board(img: np.ndarray, bbox: dict) -> np.ndarray:
    """Crop bounding box region from image with boundary clamping."""
    h, w = img.shape[:2]
    x = max(0, bbox["x"])
    y = max(0, bbox["y"])
    x2 = min(w, x + bbox["width"])
    y2 = min(h, y + bbox["height"])

    crop = img[y:y2, x:x2]
    if crop.size == 0:
        raise ValueError(f"Empty crop region: bbox={bbox}, image={w}x{h}")
    return crop


def _detect_corners(crop: np.ndarray) -> np.ndarray:
    """
    Detect and order the 4 corners of the chessboard in the cropped image.

    Returns:
        4×2 float32 array ordered: [top-left, top-right, bottom-right, bottom-left]
    """
    import cv2

    gray = cv2.cvtColor(crop, cv2.COLOR_BGR2GRAY)
    h, w = gray.shape

    # Try Shi-Tomasi corner detection on the board border
    # First, detect edges to find the board border
    blurred = cv2.GaussianBlur(gray, (5, 5), 0)
    edges = cv2.Canny(blurred, 50, 150)

    # Morphological closing to connect edge fragments
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (5, 5))
    edges = cv2.morphologyEx(edges, cv2.MORPH_CLOSE, kernel, iterations=2)

    # Find contours
    contours, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    if contours:
        # Find the largest contour (should be the board border)
        largest = max(contours, key=cv2.contourArea)
        peri = cv2.arcLength(largest, True)
        approx = cv2.approxPolyDP(largest, 0.02 * peri, True)

        if len(approx) == 4:
            # Got exactly 4 corners — order them
            corners = approx.reshape(4, 2).astype(np.float32)
            return _order_corners(corners)

    # Fallback: use image corners as the bounding rectangle
    logger.debug("Corner detection fallback: using image boundary corners")
    corners = np.array([
        [0, 0],
        [w - 1, 0],
        [w - 1, h - 1],
        [0, h - 1],
    ], dtype=np.float32)
    return corners


def _order_corners(pts: np.ndarray) -> np.ndarray:
    """
    Order 4 points as: top-left, top-right, bottom-right, bottom-left.

    Uses sum (x+y) and diff (y-x) heuristics.
    """
    rect = np.zeros((4, 2), dtype=np.float32)
    s = pts.sum(axis=1)
    d = np.diff(pts, axis=1).flatten()

    rect[0] = pts[np.argmin(s)]   # top-left: smallest sum
    rect[2] = pts[np.argmax(s)]   # bottom-right: largest sum
    rect[1] = pts[np.argmin(d)]   # top-right: smallest diff
    rect[3] = pts[np.argmax(d)]   # bottom-left: largest diff

    return rect


def _perspective_transform(crop: np.ndarray, corners: np.ndarray) -> np.ndarray:
    """Apply perspective warp to produce a RECTIFIED_SIZE × RECTIFIED_SIZE image."""
    import cv2

    dst = np.array([
        [0, 0],
        [RECTIFIED_SIZE - 1, 0],
        [RECTIFIED_SIZE - 1, RECTIFIED_SIZE - 1],
        [0, RECTIFIED_SIZE - 1],
    ], dtype=np.float32)

    M = cv2.getPerspectiveTransform(corners, dst)
    warped = cv2.warpPerspective(crop, M, (RECTIFIED_SIZE, RECTIFIED_SIZE))
    return warped


def _slice_cells(rectified: np.ndarray) -> list[dict]:
    """
    Slice rectified 640×640 image into 64 cells of 80×80.

    Returns list of dicts with square name, row, col, and image array.
    Convention: row 0 = rank 8 (top), col 0 = file a (left).
    """
    cells = []
    for row in range(8):
        for col in range(8):
            y1 = row * CELL_SIZE
            y2 = y1 + CELL_SIZE
            x1 = col * CELL_SIZE
            x2 = x1 + CELL_SIZE

            cell_img = rectified[y1:y2, x1:x2].copy()
            square = f"{FILES[col]}{RANKS[row]}"

            cells.append({
                "square": square,
                "row": row,
                "col": col,
                "image": cell_img,
                "cell_url": None,  # Populated by save_cells()
            })

    return cells


def rectify_board(
    source_image: np.ndarray | bytes,
    bounding_box: dict,
    save_dir: Optional[str] = None,
    job_id: Optional[str] = None,
    page_number: int = 1,
    board_index: int = 0,
) -> dict:
    """
    Full rectification pipeline for one detected board.

    Args:
        source_image: BGR numpy array or image bytes
        bounding_box: {"x", "y", "width", "height"} from board_detector
        save_dir: Optional directory to save rectified + cell images
        job_id: For generating storage paths
        page_number: Page number (1-based)
        board_index: Board index on page (0-based)

    Returns:
        dict with rectified_image, rectified_url, cells
    """
    import cv2

    t0 = time.monotonic()

    # Load image if bytes
    if isinstance(source_image, (bytes, bytearray)):
        arr = np.frombuffer(source_image, np.uint8)
        source_image = cv2.imdecode(arr, cv2.IMREAD_COLOR)
        if source_image is None:
            raise ValueError("Could not decode image bytes")

    # 1. Crop board region
    crop = _crop_board(source_image, bounding_box)
    logger.debug("Cropped board: %dx%d", crop.shape[1], crop.shape[0])

    # 2. Detect corners
    corners = _detect_corners(crop)

    # 3. Perspective transform → 640×640
    rectified = _perspective_transform(crop, corners)

    # 4. Slice into 64 cells
    cells = _slice_cells(rectified)

    # 5. Optionally save to disk
    rectified_url = None
    if save_dir:
        from app.services.pdf_service import _save_local

        # Save rectified board image
        _, rectified_png = cv2.imencode(".png", rectified)
        rel_path = f"{job_id}/boards/page{page_number:03d}_board{board_index:02d}_rectified.png"
        rectified_url = _save_local(rectified_png.tobytes(), rel_path)

        # Save each cell
        for cell in cells:
            _, cell_png = cv2.imencode(".png", cell["image"])
            cell_rel = (
                f"{job_id}/cells/page{page_number:03d}_board{board_index:02d}_{cell['square']}.png"
            )
            cell["cell_url"] = _save_local(cell_png.tobytes(), cell_rel)

    elapsed_ms = int((time.monotonic() - t0) * 1000)
    logger.info(
        "Rectified board: page=%d board=%d → %dx%d, 64 cells, %d ms",
        page_number, board_index, RECTIFIED_SIZE, RECTIFIED_SIZE, elapsed_ms,
    )

    return {
        "rectified_image": rectified,
        "rectified_url": rectified_url,
        "cells": cells,
    }
