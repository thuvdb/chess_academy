"""
Piece Classifier — Sprint 3C
Classifies each of the 64 cells into one of 13 labels:
  K, Q, R, B, N, P  (white)
  k, q, r, b, n, p  (black)
  empty

Strategy:
  - Production: YOLOv8 model (models/chess_yolov8.pt)
  - Dev/fallback: rule-based stub using brightness analysis

Output per cell:
  {"piece": "K", "confidence": 0.95}
"""

import logging
import time
from pathlib import Path
from typing import Optional

import numpy as np

logger = logging.getLogger(__name__)

# ── Constants ──────────────────────────────────────────────
LABELS = ["K", "Q", "R", "B", "N", "P", "k", "q", "r", "b", "n", "p", "empty"]
MODEL_PATH = Path(__file__).parent.parent.parent / "models" / "chess_yolov8.pt"

# Brightness thresholds for stub classifier
DARK_SQUARE_THRESHOLD = 140      # avg brightness below → dark square
PIECE_PRESENCE_STD_THRESHOLD = 25  # std > threshold → likely has a piece


def _load_yolo_model():
    """Load YOLOv8 model if available."""
    if not MODEL_PATH.exists():
        logger.info("YOLOv8 model not found at %s — using stub classifier", MODEL_PATH)
        return None

    try:
        from ultralytics import YOLO
        model = YOLO(str(MODEL_PATH))
        logger.info("YOLOv8 model loaded: %s", MODEL_PATH)
        return model
    except ImportError:
        logger.warning("ultralytics not installed — using stub classifier")
        return None
    except Exception as exc:
        logger.warning("Failed to load YOLO model: %s — using stub classifier", exc)
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


def classify_cell_stub(cell_image: np.ndarray, square: str) -> dict:
    """
    Stub classifier: uses brightness/texture heuristics.

    NOT accurate — placeholder until YOLOv8 model is trained.
    Returns {"piece": "empty", "confidence": 0.50} for all cells.
    In a real implementation, this would be replaced by the YOLO model.
    """
    gray = np.mean(cell_image)  # average brightness
    std = np.std(cell_image)    # texture variation

    # Simple heuristic: cells with high texture variation likely have a piece
    if std > PIECE_PRESENCE_STD_THRESHOLD:
        # Cannot distinguish which piece without a real model
        return {"piece": "empty", "confidence": 0.35, "method": "stub"}
    else:
        return {"piece": "empty", "confidence": 0.90, "method": "stub"}


def classify_cell_yolo(model, cell_image: np.ndarray) -> dict:
    """Classify a single cell using the YOLOv8 model."""
    results = model(cell_image, verbose=False)

    if not results or not results[0].boxes or len(results[0].boxes) == 0:
        return {"piece": "empty", "confidence": 0.85, "method": "yolo"}

    # Take highest confidence prediction
    boxes = results[0].boxes
    confidences = boxes.conf.cpu().numpy()
    classes = boxes.cls.cpu().numpy().astype(int)

    best_idx = np.argmax(confidences)
    class_id = classes[best_idx]
    confidence = float(confidences[best_idx])

    # Map class ID to label
    names = results[0].names
    piece_label = names.get(class_id, "empty")

    return {"piece": piece_label, "confidence": round(confidence, 4), "method": "yolo"}


def classify_cells(cells: list[dict]) -> list[dict]:
    """
    Classify all 64 cells from a rectified board.

    Args:
        cells: list of dicts from board_rectifier, each with "square" and "image" keys

    Returns:
        list of dicts: {square, piece, confidence, method}
    """
    t0 = time.monotonic()
    model = _get_model()

    results = []
    for cell in cells:
        if model is not None:
            prediction = classify_cell_yolo(model, cell["image"])
        else:
            prediction = classify_cell_stub(cell["image"], cell["square"])

        results.append({
            "square": cell["square"],
            "row": cell["row"],
            "col": cell["col"],
            "piece": prediction["piece"],
            "confidence": prediction["confidence"],
            "method": prediction.get("method", "unknown"),
        })

    elapsed_ms = int((time.monotonic() - t0) * 1000)
    method = "yolo" if model else "stub"
    non_empty = sum(1 for r in results if r["piece"] != "empty")
    logger.info(
        "Classified 64 cells (%s): %d pieces, %d empty, %d ms",
        method, non_empty, 64 - non_empty, elapsed_ms,
    )

    return results
