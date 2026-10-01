"""
Board Detector — Sprint 3A
Detects chessboard bounding boxes in an image using OpenCV contour analysis.

Algorithm:
  1. Preprocess: grayscale → adaptive threshold → morphological closing
  2. Find external contours → filter by aspect ratio ≈ 1.0 and min area
  3. Approximate polygon → accept quadrilaterals (4 corners)
  4. Score by area and squareness → pick top-N candidates
  5. Compute confidence from how close aspect ratio is to 1.0 and relative area

Output contract (per board):
  {
    "x": int,         # top-left column
    "y": int,         # top-left row
    "width": int,
    "height": int,
    "confidence": float,   # 0.0 – 1.0
    "board_index": int,    # 0-based order on page
  }
"""

import logging
import time
from typing import Optional

import numpy as np

logger = logging.getLogger(__name__)

# ── Tunable constants ──────────────────────────────────────────
MIN_BOARD_AREA_RATIO = 0.02      # Board must be ≥ 2% of image area
MAX_BOARD_AREA_RATIO = 0.98      # Board must be ≤ 98% of image area
ASPECT_RATIO_TOLERANCE = 0.25    # |w/h - 1| < 0.25 to be "square"
MAX_BOARDS_PER_PAGE = 8          # Safety cap
# ─────────────────────────────────────────────────────────────


def _load_image_bytes(source) -> np.ndarray:
    """Load image from bytes or filepath into a numpy BGR array."""
    import cv2

    if isinstance(source, (bytes, bytearray)):
        arr = np.frombuffer(source, np.uint8)
        img = cv2.imdecode(arr, cv2.IMREAD_COLOR)
    else:
        img = cv2.imread(str(source))

    if img is None:
        raise ValueError("Could not decode image — invalid bytes or unsupported format")
    return img


def _preprocess(gray: np.ndarray) -> np.ndarray:
    """Convert grayscale to binary mask good for contour detection."""
    import cv2

    # Adaptive threshold handles uneven lighting
    binary = cv2.adaptiveThreshold(
        gray, 255,
        cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
        cv2.THRESH_BINARY_INV,
        blockSize=15,
        C=4,
    )
    # Close small gaps in board lines
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (5, 5))
    closed = cv2.morphologyEx(binary, cv2.MORPH_CLOSE, kernel, iterations=2)
    return closed


def _contour_to_bounding_box(contour) -> tuple[int, int, int, int]:
    import cv2
    x, y, w, h = cv2.boundingRect(contour)
    return x, y, w, h


def _compute_confidence(w: int, h: int, area: int, img_area: int) -> float:
    """
    Confidence score based on:
      - How square the bounding box is (aspect ratio closeness to 1.0)
      - Relative area within the page (penalise too small or too large)
    """
    aspect = min(w, h) / max(w, h)                        # 0..1, 1.0 = perfect square
    area_ratio = area / img_area                           # 0..1
    # Penalise extremes: ideal board occupies 5–70% of page
    area_score = 1.0 - abs(area_ratio - 0.3) / 0.7       # peaks at 30%, gentle slope
    area_score = max(0.0, min(1.0, area_score))
    # Weighted combination
    confidence = 0.7 * aspect + 0.3 * area_score
    return round(confidence, 4)


def detect_boards(image_source, max_boards: int = MAX_BOARDS_PER_PAGE) -> list[dict]:
    """
    Detect chessboard bounding boxes in an image.

    Args:
        image_source: bytes, bytearray, or file path (str/Path)
        max_boards:   maximum number of boards to return

    Returns:
        List of board dicts sorted by confidence descending.
        Empty list if no board found.

    Raises:
        ImportError  if OpenCV is not installed
        ValueError   if image cannot be decoded
    """
    try:
        import cv2
    except ImportError:
        raise ImportError(
            "opencv-python is required for board detection. "
            "Install with: pip install opencv-python-headless"
        )

    t0 = time.monotonic()

    img = _load_image_bytes(image_source)
    img_h, img_w = img.shape[:2]
    img_area = img_h * img_w

    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    binary = _preprocess(gray)

    contours, _ = cv2.findContours(binary, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    candidates = []

    for cnt in contours:
        area = cv2.contourArea(cnt)
        if area < img_area * MIN_BOARD_AREA_RATIO:
            continue
        if area > img_area * MAX_BOARD_AREA_RATIO:
            continue

        # Approximate polygon
        peri = cv2.arcLength(cnt, True)
        approx = cv2.approxPolyDP(cnt, 0.04 * peri, True)

        # Accept 4-corner polygons (quadrilateral)
        if len(approx) < 4 or len(approx) > 8:
            continue

        x, y, w, h = _contour_to_bounding_box(cnt)

        # Check aspect ratio (squareness)
        if w == 0 or h == 0:
            continue
        aspect = min(w, h) / max(w, h)
        if abs(aspect - 1.0) > ASPECT_RATIO_TOLERANCE:
            continue

        confidence = _compute_confidence(w, h, w * h, img_area)
        candidates.append({"x": x, "y": y, "width": w, "height": h, "confidence": confidence})

    # De-duplicate overlapping boxes (keep highest confidence)
    candidates = _nms(candidates, iou_threshold=0.5)

    # Sort by confidence desc, take top-N
    candidates.sort(key=lambda c: c["confidence"], reverse=True)
    candidates = candidates[:max_boards]

    # Add board_index
    for i, c in enumerate(candidates):
        c["board_index"] = i

    elapsed_ms = int((time.monotonic() - t0) * 1000)
    logger.info(
        "Board detection: found %d board(s) in %d ms (image %dx%d)",
        len(candidates), elapsed_ms, img_w, img_h,
    )
    return candidates


def _iou(a: dict, b: dict) -> float:
    """Compute Intersection over Union for two bounding boxes."""
    ax1, ay1 = a["x"], a["y"]
    ax2, ay2 = ax1 + a["width"], ay1 + a["height"]
    bx1, by1 = b["x"], b["y"]
    bx2, by2 = bx1 + b["width"], by1 + b["height"]

    ix1, iy1 = max(ax1, bx1), max(ay1, by1)
    ix2, iy2 = min(ax2, bx2), min(ay2, by2)

    if ix2 <= ix1 or iy2 <= iy1:
        return 0.0

    inter = (ix2 - ix1) * (iy2 - iy1)
    area_a = (ax2 - ax1) * (ay2 - ay1)
    area_b = (bx2 - bx1) * (by2 - by1)
    return inter / (area_a + area_b - inter)


def _nms(boxes: list[dict], iou_threshold: float = 0.5) -> list[dict]:
    """Non-Maximum Suppression — remove duplicate overlapping boxes."""
    if not boxes:
        return []
    boxes = sorted(boxes, key=lambda b: b["confidence"], reverse=True)
    kept = []
    for box in boxes:
        if all(_iou(box, kept_box) < iou_threshold for kept_box in kept):
            kept.append(box)
    return kept
