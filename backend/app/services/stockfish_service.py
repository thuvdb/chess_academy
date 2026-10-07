import logging
import chess
from stockfish import Stockfish

logger = logging.getLogger(__name__)

def evaluate_alternate_solution(fen: str, user_moves: list[str]) -> bool:
    """
    Evaluates if the user's sequence of moves leads to a forced mate or a +5 advantage.
    Returns True if it's a valid alternate solution, False otherwise.
    """
    try:
        # 1. Replay the moves on the board
        board = chess.Board(fen)
        for move_uci in user_moves:
            # If the move is invalid, it's immediately incorrect
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

        # 2. Evaluate the final position with Stockfish
        # Fast, lightweight config for backend auto-grading
        stockfish = Stockfish(
            path="stockfish", # Should be in system PATH since we installed via apt-get
            depth=15,         # Enough to find tactical mates within 1-3 moves quickly
            parameters={
                "Threads": 1,
                "Hash": 32,
                "MultiPV": 1,
                "Use NNUE": True
            }
        )

        stockfish.set_fen_position(board.fen())
        eval_result = stockfish.get_evaluation()
        
        logger.info(f"Stockfish evaluation for alternate solution: {eval_result}")
        
        # eval_result looks like: {'type': 'mate', 'value': 2} or {'type': 'cp', 'value': 600}
        
        # If it's a forced mate for the side that just moved (which is now the opponent's turn, so mate should be for the side we played as)
        # Wait, if we just moved, it's now the opponent's turn. 
        # If we played a mating move, the game is already over (board.is_checkmate()).
        if board.is_checkmate():
            return True
            
        # If not checkmate immediately, but it's a forced mate sequence
        # 'value' is positive if White is winning, negative if Black is winning.
        # However, stockfish.get_evaluation() is always relative to the side to move.
        # Since it's the opponent's turn now, if the evaluation is negative (or mate negative), it means the opponent is losing (we are winning).
        if eval_result['type'] == 'mate':
            # If mate value is negative, it means the side to move is getting mated.
            # Which is exactly what we want!
            if eval_result['value'] < 0:
                return True
                
        if eval_result['type'] == 'cp':
            # +5 pawn advantage equivalent (-500 cp for the side to move)
            if eval_result['value'] <= -500:
                return True

        return False
        
    except Exception as e:
        logger.error(f"Failed to evaluate alternative solution: {e}")
        return False
