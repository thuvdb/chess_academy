"""
FEN Builder — Sprint 3C
Converts piece classification results (8×8 grid) into a FEN string.

Validation pipeline:
  1. Build raw FEN from classification grid
  2. Parse with python-chess → syntax check
  3. Position validation (king count, pawn count, etc.)
  4. Stockfish sanity check (has legal moves?)

Output:
  {
    "fen_candidate": "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1",
    "validation": "valid" | "invalid_syntax" | "invalid_position" | "no_legal_moves",
    "errors": [...],
    "low_confidence_cells": [{"square": "d8", "piece": "q", "confidence": 0.63}, ...],
  }
"""

import logging
from typing import Optional

logger = logging.getLogger(__name__)

# Minimum confidence for a cell to be considered "reliable"
LOW_CONFIDENCE_THRESHOLD = 0.70


def build_fen_from_grid(
    cell_results: list[dict],
    side_to_move: str = "w",
    castling: str = "-",
    en_passant: str = "-",
    halfmove: int = 0,
    fullmove: int = 1,
) -> dict:
    """
    Convert classified cells into a FEN string with validation.

    Args:
        cell_results: list of 64 dicts from piece_classifier.classify_cells()
            Each must have: square, row, col, piece, confidence
        side_to_move: "w" or "b"
        castling: castling rights string
        en_passant: en passant target square or "-"
        halfmove: halfmove clock
        fullmove: fullmove number

    Returns:
        dict with fen_candidate, validation status, errors, and low_confidence_cells
    """
    errors = []

    # Sort cells by row then col
    sorted_cells = sorted(cell_results, key=lambda c: (c["row"], c["col"]))
    if len(sorted_cells) != 64:
        errors.append(f"Expected 64 cells, got {len(sorted_cells)}")
        return {
            "fen_candidate": None,
            "validation": "invalid_syntax",
            "errors": errors,
            "low_confidence_cells": [],
        }

    # Build piece placement string (rows separated by /)
    rows = []
    for rank in range(8):  # rank 0 = top = rank 8
        row_cells = sorted_cells[rank * 8:(rank + 1) * 8]
        row_str = ""
        empty_count = 0

        for cell in row_cells:
            piece = cell["piece"]
            if piece == "empty" or piece == "":
                empty_count += 1
            else:
                if empty_count > 0:
                    row_str += str(empty_count)
                    empty_count = 0
                row_str += piece

        if empty_count > 0:
            row_str += str(empty_count)

        rows.append(row_str)

    piece_placement = "/".join(rows)
    fen = f"{piece_placement} {side_to_move} {castling} {en_passant} {halfmove} {fullmove}"

    # Collect low-confidence cells
    low_conf = [
        {
            "square": c["square"],
            "piece": c["piece"],
            "confidence": c["confidence"],
        }
        for c in sorted_cells
        if c["piece"] != "empty" and c["confidence"] < LOW_CONFIDENCE_THRESHOLD
    ]

    # Validate
    validation = _validate_fen(fen, errors)

    return {
        "fen_candidate": fen,
        "validation": validation,
        "errors": errors,
        "low_confidence_cells": low_conf,
    }


def _validate_fen(fen: str, errors: list[str]) -> str:
    """
    Validate FEN through multiple stages:
      1. python-chess syntax check
      2. Position sanity check
      3. Optional Stockfish legal moves check
    """
    # Stage 1: python-chess parse
    try:
        import chess
    except ImportError:
        logger.warning("python-chess not installed — skipping FEN validation")
        return "unvalidated"

    try:
        board = chess.Board(fen)
    except ValueError as exc:
        errors.append(f"FEN syntax error: {exc}")
        return "invalid_syntax"

    # Stage 2: Position validation
    position_errors = _validate_position(board)
    if position_errors:
        errors.extend(position_errors)
        return "invalid_position"

    # Stage 3: Legal moves check
    if not list(board.legal_moves):
        # Check if it's checkmate or stalemate (which are valid positions)
        if board.is_checkmate():
            pass  # Valid — checkmate
        elif board.is_stalemate():
            pass  # Valid — stalemate
        else:
            errors.append("Position has no legal moves and is not checkmate/stalemate")
            return "no_legal_moves"

    return "valid"


def _validate_position(board) -> list[str]:
    """Check position sanity rules."""
    import chess

    errors = []

    # Must have exactly 1 king per side
    white_kings = len(board.pieces(chess.KING, chess.WHITE))
    black_kings = len(board.pieces(chess.KING, chess.BLACK))
    if white_kings != 1:
        errors.append(f"White has {white_kings} king(s), expected 1")
    if black_kings != 1:
        errors.append(f"Black has {black_kings} king(s), expected 1")

    # Max 8 pawns per side
    white_pawns = len(board.pieces(chess.PAWN, chess.WHITE))
    black_pawns = len(board.pieces(chess.PAWN, chess.BLACK))
    if white_pawns > 8:
        errors.append(f"White has {white_pawns} pawns, max 8")
    if black_pawns > 8:
        errors.append(f"Black has {black_pawns} pawns, max 8")

    # Pawns cannot be on rank 1 or rank 8
    for sq in board.pieces(chess.PAWN, chess.WHITE):
        rank = chess.square_rank(sq)
        if rank == 0 or rank == 7:
            errors.append(f"White pawn on illegal rank: {chess.square_name(sq)}")
    for sq in board.pieces(chess.PAWN, chess.BLACK):
        rank = chess.square_rank(sq)
        if rank == 0 or rank == 7:
            errors.append(f"Black pawn on illegal rank: {chess.square_name(sq)}")

    # Max 16 pieces per side
    white_total = bin(board.occupied_co[chess.WHITE]).count('1')
    black_total = bin(board.occupied_co[chess.BLACK]).count('1')
    if white_total > 16:
        errors.append(f"White has {white_total} pieces, max 16")
    if black_total > 16:
        errors.append(f"Black has {black_total} pieces, max 16")

    # Check side to move is not in check by opponent
    # (i.e., the position must be reachable)
    if board.was_into_check():
        errors.append("Opponent's king is in check (position unreachable)")

    return errors


def build_cell_confidence_map(cell_results: list[dict]) -> dict:
    """
    Build a JSONB-ready confidence map for storage.

    Returns:
        {"a8": {"piece": "r", "confidence": 0.95}, ...}
    """
    return {
        c["square"]: {
            "piece": c["piece"],
            "confidence": c["confidence"],
        }
        for c in cell_results
    }
