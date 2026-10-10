import logging
import os
import chess
from stockfish import Stockfish
from app.core.config import settings

logger = logging.getLogger(__name__)


def get_stockfish_path() -> str:
    if hasattr(settings, "STOCKFISH_PATH") and os.path.exists(settings.STOCKFISH_PATH):
        return settings.STOCKFISH_PATH
    if os.path.exists("/usr/games/stockfish"):
        return "/usr/games/stockfish"
    return "stockfish"


def get_stockfish(depth: int = 15) -> Stockfish:
    return Stockfish(
        path=get_stockfish_path(),
        depth=depth,
        parameters={
            "Threads": 1,
            "Hash": 32,
            "MultiPV": 1,
        },
    )


def generate_puzzle_solutions(fen: str, depth: int = 18, max_plies: int = 8) -> list[dict]:
    """
    Analyzes a FEN position using Stockfish and generates the expected move sequence.
    Returns list of dicts:
      [
        {"move_order": 1, "move_uci": "a5d8", "move_san": "Qxd8+", "is_best_move": True, "explanation": "Nước đi 1: Qxd8+"},
        {"move_order": 2, "move_uci": "d5d8", "move_san": "Rxd8", "is_best_move": True, "explanation": "Phản ứng của đối phương: Rxd8"},
        {"move_order": 3, "move_uci": "d1d8", "move_san": "Rxd8#", "is_best_move": True, "explanation": "Nước đi 2 (Chiếu hết): Rxd8#"},
      ]
    """
    try:
        board = chess.Board(fen)
        sf = get_stockfish(depth=depth)
        sf.set_fen_position(board.fen())

        eval_res = sf.get_evaluation()
        is_mate_puzzle = eval_res.get("type") == "mate"
        # If it's a mate puzzle, mate value is turns (plies = turns * 2 - 1 or turns * 2)
        if is_mate_puzzle:
            mate_turns = abs(eval_res.get("value", 2))
            limit_plies = min(max_plies, mate_turns * 2)
        else:
            limit_plies = min(max_plies, 4)

        solutions = []
        order = 1

        while order <= limit_plies and not board.is_game_over():
            best_uci = sf.get_best_move()
            if not best_uci:
                break
            try:
                move = chess.Move.from_uci(best_uci)
                if move not in board.legal_moves:
                    break
                san = board.san(move)
                is_player = (order % 2 == 1)
                exp = f"Nước đi {(order + 1) // 2}: {san}" if is_player else f"Phản ứng đối phương: {san}"
                solutions.append({
                    "move_order": order,
                    "move_uci": best_uci.lower(),
                    "move_san": san,
                    "is_best_move": True,
                    "explanation": exp,
                })
                board.push(move)
                order += 1
                if board.is_game_over():
                    break
                sf.set_fen_position(board.fen())
            except Exception as exc:
                logger.error(f"Error generating move {order} for FEN {fen}: {exc}")
                break

        return solutions
    except Exception as exc:
        logger.error(f"Failed to generate solutions with Stockfish: {exc}")
        return []


def evaluate_alternate_solution(fen: str, user_moves: list[str]) -> bool:
    """
    Evaluates if the user's sequence of moves leads to a forced mate or a +5 advantage.
    Returns True if it's a valid alternate solution, False otherwise.
    """
    try:
        # 1. Replay the moves on the board
        board = chess.Board(fen)
        for move_uci in user_moves:
            try:
                move = chess.Move.from_uci(move_uci)
                if move in board.legal_moves:
                    board.push(move)
                else:
                    logger.warning(f"Illegal move {move_uci} for FEN {board.fen()}")
                    return False
            except Exception as e:
                logger.error(f"Error parsing move {move_uci}: {e}")
                return False

        # If it played a mating move, checkmate is already reached!
        if board.is_checkmate():
            return True

        # 2. Evaluate the final position with Stockfish
        stockfish = get_stockfish(depth=15)
        stockfish.set_fen_position(board.fen())
        eval_result = stockfish.get_evaluation()

        logger.info(f"Stockfish evaluation for alternate solution: {eval_result}")

        # If it's a forced mate for the side that just moved:
        if eval_result.get("type") == "mate":
            if eval_result.get("value", 0) < 0:
                return True

        if eval_result.get("type") == "cp":
            if eval_result.get("value", 0) <= -500:
                return True

        return False

    except Exception as e:
        logger.error(f"Failed to evaluate alternative solution: {e}")
        return False
