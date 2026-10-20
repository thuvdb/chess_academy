"""
CAMS AI Tutor — Board Move Validator using python-chess.
Extracts SAN moves from LLM <board> tags, validates legal moves,
and generates corresponding FENs for interactive step-by-step playback.
"""
import json
import logging
import re
from typing import Any

import chess

logger = logging.getLogger(__name__)

BOARD_BLOCK_REGEX = re.compile(r"<board>(.*?)</board>", re.DOTALL | re.IGNORECASE)


def validate_board_moves(payload: dict[str, Any]) -> dict[str, Any] | None:
    """
    Validate a board payload containing SAN moves.
    Returns structured data with sequence of FENs, or None if invalid.
    """
    if not isinstance(payload, dict):
        return None

    raw_moves = payload.get("moves")
    caption = str(payload.get("caption", "Minh họa thế cờ")).strip()
    initial_fen = payload.get("initial_fen", chess.STARTING_FEN)

    if not isinstance(raw_moves, list) or not raw_moves:
        logger.info("Board validation skipped: 'moves' is not a non-empty list.")
        return None

    # Limit move count to protect against overly long animations or abusive tokens
    if len(raw_moves) > 50:
        raw_moves = raw_moves[:50]

    # Initialize board from starting FEN
    try:
        board = chess.Board(initial_fen)
    except Exception as e:
        logger.warning("Invalid initial_fen in AI board: %s: %s", initial_fen, e)
        return None

    validated_moves: list[dict[str, str]] = []
    fens: list[str] = [board.fen()]

    for move_index, move_san in enumerate(raw_moves):
        if not isinstance(move_san, str):
            logger.warning("Move at index %d is not a string: %r", move_index, move_san)
            return None

        clean_san = move_san.strip()
        if not clean_san:
            continue

        try:
            # Parse SAN into Move object
            move = board.parse_san(clean_san)
            if move not in board.legal_moves:
                logger.warning("Move %s is not legal in position %s", clean_san, board.fen())
                return None

            board.push(move)
            current_fen = board.fen()
            fens.append(current_fen)
            validated_moves.append({
                "move_number": move_index + 1,
                "san": clean_san,
                "fen": current_fen,
            })
        except (chess.IllegalMoveError, chess.InvalidMoveError, chess.AmbiguousMoveError, ValueError) as err:
            logger.warning("Invalid SAN move %r at step %d: %s", clean_san, move_index + 1, err)
            return None

    if not validated_moves:
        return None

    return {
        "initial_fen": initial_fen,
        "caption": caption,
        "total_moves": len(validated_moves),
        "moves": [m["san"] for m in validated_moves],
        "positions": fens,
        "steps": validated_moves,
        "is_checkmate": board.is_checkmate(),
        "is_stalemate": board.is_stalemate(),
    }


def extract_and_validate_board(raw_text: str) -> tuple[str, dict[str, Any] | None]:
    """
    Extracts the <board>...</board> tag from the raw AI response text,
    validates the moves using python-chess, and returns (clean_text, board_data).
    If validation fails or tag is malformed, board_data will be None.
    """
    match = BOARD_BLOCK_REGEX.search(raw_text)
    if not match:
        return raw_text, None

    board_json_str = match.group(1).strip()
    clean_text = BOARD_BLOCK_REGEX.sub("", raw_text).strip()

    try:
        payload = json.loads(board_json_str)
        board_data = validate_board_moves(payload)
        return clean_text, board_data
    except Exception as e:
        logger.warning("Failed to parse board JSON: %s (Content: %r)", e, board_json_str)
        return clean_text, None
