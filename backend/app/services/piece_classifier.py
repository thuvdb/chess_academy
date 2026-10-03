"""
Piece Classifier - Sprint 3C (Revised)
Classifies each of the 64 cells into one of 13 labels:
  K, Q, R, B, N, P  (white pieces)
  k, q, r, b, n, p  (black pieces)
  empty

Strategy:
  1. YOLOv8 model if properly trained for chess (validates labels first)
  2. Enhanced CV heuristic: edge density + color analysis
     - Detects presence (has piece or empty)
     - Estimates color (white piece = P, black piece = p)
     - NOTE: Cannot distinguish piece type without trained model
"""

import logging
import time
from pathlib import Path
from typing import Optional

import numpy as np

logger = logging.getLogger(__name__)

# ── Constants ──────────────────────────────────────────────
CHESS_LABELS = {"K", "Q", "R", "B", "N", "P", "k", "q", "r", "b", "n", "p", "empty"}
MODEL_PATH = Path(__file__).parent.parent.parent / "models" / "chess_yolov8.pt"

# CV Heuristic thresholds (tuned on real chess book scans)
EDGE_DENSITY_THRESHOLD = 0.08   # Canny edge pixel fraction > this -> likely piece present
STD_THRESHOLD = 35              # Pixel std > this -> likely piece present


def _load_yolo_model():
    """Load YOLOv8 model only if it is actually trained for chess pieces."""
    if not MODEL_PATH.exists():
        logger.info("YOLOv8 model not found at %s - using CV heuristic", MODEL_PATH)
        return None

    try:
        from ultralytics import YOLO
        model = YOLO(str(MODEL_PATH))

        # Validate model labels to ensure it is a chess model, not ImageNet etc.
        names = model.names if hasattr(model, "names") else {}
        chess_variants = {
            "K", "Q", "R", "B", "N", "P", "k", "q", "r", "b", "n", "p",
            "white-king", "white-queen", "white-rook", "white-bishop", "white-knight", "white-pawn",
            "black-king", "black-queen", "black-rook", "black-bishop", "black-knight", "black-pawn",
            "wp", "wq", "wr", "wb", "wn", "wk", "bp", "bq", "br", "bb", "bn", "bk",
        }
        model_labels = set(str(v) for v in names.values())
        overlap = model_labels & chess_variants

        if not overlap:
            logger.warning(
                "Model at %s is NOT a chess piece model (labels: %s...). "
                "Falling back to CV heuristic. Replace chess_yolov8.pt with a "
                "properly trained chess piece detection model.",
                MODEL_PATH, list(names.values())[:5]
            )
            return None

        logger.info("Chess YOLOv8 model loaded: %s (labels: %s)", MODEL_PATH, list(names.values())[:6])
        return model
    except ImportError:
        logger.warning("ultralytics not installed - using CV heuristic")
        return None
    except Exception as exc:
        logger.warning("Failed to load YOLO model: %s - using CV heuristic", exc)
        return None


# Lazy-loaded model singleton
_model = None
_model_loaded = False


def _get_model():
    global _model, _model_loaded
    if not _model_loaded:
        _model = _load_yolo_model()
        _model_loaded = True
    return _model


def _has_stripe_texture(gray_inner: np.ndarray) -> bool:
    """
    Detect diagonal stripe texture of empty dark squares in chess diagrams.
    Stripes have concentrated gradient direction; pieces have complex varied directions.
    """
    import cv2
    sobelx = cv2.Sobel(gray_inner, cv2.CV_64F, 1, 0, ksize=3)
    sobely = cv2.Sobel(gray_inner, cv2.CV_64F, 0, 1, ksize=3)
    angles = np.arctan2(sobely, sobelx)
    hist, _ = np.histogram(angles, bins=8, range=(-np.pi, np.pi))
    hist = hist.astype(float) / (hist.sum() + 1e-8)
    max_bin = float(hist.max())
    return max_bin > 0.40  # >40% edges in same direction = uniform stripe = empty square


def classify_cell_cv(cell_image: np.ndarray, square: str) -> dict:
    """
    Enhanced CV heuristic: edge density + pixel brightness analysis.
    Trims border pixels first to ignore chessboard grid lines.

    Returns:
      - "empty" when no piece detected
      - "P" (white piece placeholder) or "p" (black piece placeholder) when detected
      NOTE: Cannot distinguish between K/Q/R/B/N/P without a trained model.
    """
    import cv2

    h, w = cell_image.shape[:2]

    # Trim 15% border to remove chessboard grid lines
    trim = max(2, int(min(h, w) * 0.15))
    inner = cell_image[trim:h-trim, trim:w-trim]

    if inner.size == 0:
        inner = cell_image  # fallback if too small

    gray = cv2.cvtColor(inner, cv2.COLOR_BGR2GRAY)
    mean_full = float(cv2.cvtColor(cell_image, cv2.COLOR_BGR2GRAY).mean())

    std = float(gray.std())

    # Low texture -> definitely empty
    if std < 30:
        return {"piece": "empty", "confidence": round(min(0.95, 0.80 + (30 - std) / 100), 3), "method": "cv_heuristic"}

    # Check for uniform-direction stripe texture (empty dark squares in chess diagrams)
    if _has_stripe_texture(gray):
        return {"piece": "empty", "confidence": 0.82, "method": "cv_heuristic"}

    # High non-uniform texture -> piece detected
    # Key threshold: empty dark squares have std ~70-75, pieces have std > 80
    if std < 80:
        return {"piece": "empty", "confidence": 0.70, "method": "cv_heuristic"}

    # Estimate piece color based on square background vs piece pixels
    square_is_light = mean_full > 150
    gray_flat = np.mean(cell_image, axis=2).flatten()

    if square_is_light:
        # Light square: dark pixels indicate a black piece
        dark_ratio = float(np.sum(gray_flat < 100)) / len(gray_flat)
        piece_is_black = dark_ratio > 0.08
    else:
        # Dark square: bright pixels indicate a white piece
        bright_ratio = float(np.sum(gray_flat > 190)) / len(gray_flat)
        piece_is_black = bright_ratio <= 0.06

    piece_label = "p" if piece_is_black else "P"
    confidence = round(min(0.78, 0.50 + std / 200), 3)

    return {"piece": piece_label, "confidence": confidence, "method": "cv_heuristic"}


def classify_cell_yolo(model, cell_image: np.ndarray) -> dict:
    """Classify a single cell using a validated chess YOLOv8 model."""
    try:
        results = model(cell_image, verbose=False)
        if not results:
            return {"piece": "empty", "confidence": 0.85, "method": "yolo"}

        res = results[0]

        # Classification model (.probs)
        if hasattr(res, "probs") and res.probs is not None:
            top_class = int(res.probs.top1)
            confidence = float(res.probs.top1conf)
            raw_label = res.names.get(top_class, "empty")
            piece_label = raw_label if raw_label in CHESS_LABELS else "empty"
            return {"piece": piece_label, "confidence": round(confidence, 4), "method": "yolo"}

        # Detection model (.boxes)
        if hasattr(res, "boxes") and res.boxes is not None and len(res.boxes) > 0:
            boxes = res.boxes
            confidences = boxes.conf.cpu().numpy()
            classes = boxes.cls.cpu().numpy().astype(int)
            best_idx = np.argmax(confidences)
            class_id = classes[best_idx]
            confidence = float(confidences[best_idx])
            raw_label = res.names.get(class_id, "empty")
            piece_label = raw_label if raw_label in CHESS_LABELS else "empty"
            return {"piece": piece_label, "confidence": round(confidence, 4), "method": "yolo"}

        return {"piece": "empty", "confidence": 0.85, "method": "yolo"}
    except Exception as exc:
        logger.warning("YOLO classification error: %s - fallback to CV heuristic", exc)
        return classify_cell_cv(cell_image, "unknown")


def classify_cells(cells: list[dict]) -> list[dict]:
    """
    Classify all 64 cells from a rectified board.

    Args:
        cells: list of dicts with "square" and "image" keys (from board_rectifier)

    Returns:
        list of dicts: {square, row, col, piece, confidence, method}
    """
    t0 = time.monotonic()
    model = _get_model()

    results = []
    for cell in cells:
        if model is not None:
            prediction = classify_cell_yolo(model, cell["image"])
        else:
            prediction = classify_cell_cv(cell["image"], cell["square"])

        results.append({
            "square": cell["square"],
            "row": cell["row"],
            "col": cell["col"],
            "piece": prediction["piece"],
            "confidence": prediction["confidence"],
            "method": prediction.get("method", "unknown"),
        })

    elapsed_ms = int((time.monotonic() - t0) * 1000)
    method = "yolo" if model else "cv_heuristic"
    non_empty = sum(1 for r in results if r["piece"] != "empty")
    logger.info(
        "Classified 64 cells (%s): %d pieces, %d empty, %d ms",
        method, non_empty, 64 - non_empty, elapsed_ms,
    )

    return results
