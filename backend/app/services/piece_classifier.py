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

from app.core.config import settings

import numpy as np

logger = logging.getLogger(__name__)

# ── Constants ──────────────────────────────────────────────
CHESS_LABELS = {"K", "Q", "R", "B", "N", "P", "k", "q", "r", "b", "n", "p", "empty"}


def get_yolo_model_path() -> Path:
    p = Path(settings.YOLO_MODEL_PATH)
    if not p.is_absolute():
        p = Path(__file__).resolve().parent.parent.parent / p
    return p

# Detector label -> FEN letter (supports wP/bK, white-king/black-pawn, and raw FEN letters)
_COLOR_WORDS = {"white": True, "black": False, "w": True, "b": False}
_PIECE_WORDS = {
    "king": "k", "queen": "q", "rook": "r", "bishop": "b", "knight": "n", "pawn": "p",
    "k": "k", "q": "q", "r": "r", "b": "b", "n": "n", "p": "p",
}
DETECT_CONF = 0.25


def _label_to_fen(label: str) -> Optional[str]:
    """Map a detector class name to a FEN letter, or None if unknown."""
    s = str(label)
    if s in CHESS_LABELS and s != "empty":
        return s
    parts = s.replace("_", "-").lower().split("-")
    if len(parts) == 2 and parts[0] in _COLOR_WORDS and parts[1] in _PIECE_WORDS:
        letter = _PIECE_WORDS[parts[1]]
        return letter.upper() if _COLOR_WORDS[parts[0]] else letter
    if len(parts) == 1 and len(parts[0]) == 2 and parts[0][0] in ("w", "b") and parts[0][1] in _PIECE_WORDS:
        letter = _PIECE_WORDS[parts[0][1]]
        return letter.upper() if parts[0][0] == "w" else letter
    return None

# CV Heuristic thresholds (tuned on real chess book scans)
EDGE_DENSITY_THRESHOLD = 0.08   # Canny edge pixel fraction > this -> likely piece present
STD_THRESHOLD = 35              # Pixel std > this -> likely piece present


def _load_yolo_model():
    """Load YOLOv8 model only if it is actually trained for chess pieces."""
    model_path = get_yolo_model_path()
    if not model_path.exists():
        logger.info("YOLOv8 model not found at %s - using CV heuristic", model_path)
        return None

    try:
        from ultralytics import YOLO
        model = YOLO(str(model_path))

        # Validate model labels to ensure it is a chess model, not ImageNet etc.
        names = model.names if hasattr(model, "names") else {}
        chess_variants = {
            "K", "Q", "R", "B", "N", "P", "k", "q", "r", "b", "n", "p",
            "white-king", "white-queen", "white-rook", "white-bishop", "white-knight", "white-pawn",
            "black-king", "black-queen", "black-rook", "black-bishop", "black-knight", "black-pawn",
            "wp", "wq", "wr", "wb", "wn", "wk", "bp", "bq", "br", "bb", "bn", "bk",
        }
        model_labels = set(str(v) for v in names.values())
        overlap = {l for l in model_labels if l in chess_variants or _label_to_fen(l) is not None}

        if not overlap:
            logger.warning(
                "Model at %s is NOT a chess piece model (labels: %s...). "
                "Falling back to CV heuristic. Replace chess_yolov8.pt with a "
                "properly trained chess piece detection model.",
                model_path, list(names.values())[:5]
            )
            return None

        logger.info("Chess YOLOv8 model loaded: %s (labels: %s)", model_path, list(names.values())[:6])
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


def _stitch_board(cells: list[dict]) -> Optional[np.ndarray]:
    """Rebuild the full rectified board image from its 64 cell images."""
    try:
        ch, cw = cells[0]["image"].shape[:2]
        board = np.zeros((ch * 8, cw * 8, 3), dtype=np.uint8)
        for c in cells:
            r, col = int(c["row"]), int(c["col"])
            board[r * ch:(r + 1) * ch, col * cw:(col + 1) * cw] = c["image"]
        return board
    except Exception as exc:
        logger.warning("Cannot stitch board: %s", exc)
        return None


def _detect_board_pieces(model, cells: list[dict]) -> Optional[dict]:
    """
    Whole-board detection: run detector once on the stitched board and map each
    box centre to a (row, col). Returns {(row, col): (fen_letter, conf)} or None
    if the model is not a detection model / detection failed.
    """
    if getattr(model, "task", None) != "detect":
        return None
    board = _stitch_board(cells)
    if board is None:
        return None
    try:
        res = model.predict(board, conf=DETECT_CONF, verbose=False)[0]
    except Exception as exc:
        logger.warning("YOLO board detection error: %s", exc)
        return None

    h, w = board.shape[:2]
    found: dict = {}
    for b in res.boxes:
        letter = _label_to_fen(res.names.get(int(b.cls), ""))
        if letter is None:
            continue
        x1, y1, x2, y2 = b.xyxy[0].tolist()
        col = min(7, max(0, int(((x1 + x2) / 2) / (w / 8))))
        row = min(7, max(0, int(((y1 + y2) / 2) / (h / 8))))
        conf = float(b.conf)
        if (row, col) not in found or conf > found[(row, col)][1]:
            found[(row, col)] = (letter, conf)
    return found


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

    detections = _detect_board_pieces(model, cells) if model is not None else None

    results = []
    for cell in cells:
        if detections is not None:
            hit = detections.get((int(cell["row"]), int(cell["col"])))
            if hit:
                prediction = {"piece": hit[0], "confidence": round(hit[1], 4), "method": "yolo"}
            else:
                prediction = {"piece": "empty", "confidence": 0.95, "method": "yolo"}
        elif model is not None:
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
