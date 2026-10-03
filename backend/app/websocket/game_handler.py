import json
import logging
from typing import Dict, List
from uuid import UUID
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
import chess

from app.api.deps import get_db, get_current_user_from_token
from app.core.database import async_session_factory
from app.services.tournament_service import TournamentService

router = APIRouter()
logger = logging.getLogger(__name__)


class ConnectionManager:
    def __init__(self):
        self.active_connections: Dict[str, List[WebSocket]] = {}
        self.game_states: Dict[str, str] = {}
        self.move_history: Dict[str, List[str]] = {}  # Track SAN history per game

    async def connect(self, websocket: WebSocket, game_id: str):
        await websocket.accept()
        if game_id not in self.active_connections:
            self.active_connections[game_id] = []
            self.game_states[game_id] = chess.STARTING_FEN
            self.move_history[game_id] = []
        self.active_connections[game_id].append(websocket)
        # Send current state + history
        try:
            await websocket.send_json({
                "type": "game_state",
                "fen": self.game_states.get(game_id, chess.STARTING_FEN),
                "history": self.move_history.get(game_id, []),
            })
        except Exception as e:
            logger.warning(f"Failed to send initial state: {e}")

    def disconnect(self, websocket: WebSocket, game_id: str):
        conns = self.active_connections.get(game_id)
        if conns and websocket in conns:
            conns.remove(websocket)

    async def broadcast(self, game_id: str, message: dict):
        conns = self.active_connections.get(game_id, [])
        dead: List[WebSocket] = []
        for ws in conns:
            try:
                await ws.send_json(message)
            except Exception:
                dead.append(ws)
        for ws in dead:
            self.disconnect(ws, game_id)

    def get_board(self, game_id: str) -> chess.Board:
        fen = self.game_states.get(game_id, chess.STARTING_FEN)
        return chess.Board(fen)

    def update_state(self, game_id: str, fen: str, san: str):
        self.game_states[game_id] = fen
        if game_id not in self.move_history:
            self.move_history[game_id] = []
        self.move_history[game_id].append(san)


manager = ConnectionManager()


async def save_game_result(game_id_str: str, chess_result: str):
    """Save game result to DB in a separate session."""
    try:
        game_uuid = UUID(game_id_str)
        async with async_session_factory() as session:
            service = TournamentService(session)
            await service.record_game_result(game_uuid, chess_result)
            logger.info(f"Saved result {chess_result} for game {game_id_str}")
    except Exception as e:
        logger.error(f"Failed to save game result: {e}", exc_info=True)


@router.websocket("/ws/game/{game_id}")
async def websocket_endpoint(
    websocket: WebSocket,
    game_id: str,
    token: str = Query(...),
    db: AsyncSession = Depends(get_db),
):
    # Authenticate — MUST accept before close
    user = None
    try:
        user = await get_current_user_from_token(token, db)
    except Exception as e:
        logger.warning(f"WS auth failed for game {game_id}: {e}")

    if user is None:
        await websocket.accept()
        try:
            await websocket.send_json({"type": "error", "message": "Authentication failed"})
        except Exception:
            pass
        await websocket.close(code=1008)
        return

    await manager.connect(websocket, game_id)
    logger.info(f"User {user.id} role={user.role} joined game {game_id}")

    try:
        while True:
            raw = await websocket.receive_text()

            try:
                msg = json.loads(raw)
            except json.JSONDecodeError:
                continue

            if msg.get("type") != "move":
                continue

            board = manager.get_board(game_id)

            if board.is_game_over():
                try:
                    await websocket.send_json({"type": "error", "message": "Game is already over"})
                except Exception:
                    pass
                continue

            move_obj = None

            # Method 1: from/to (UCI)
            from_sq = msg.get("from")
            to_sq = msg.get("to")
            promo = msg.get("promotion") or ""

            if from_sq and to_sq:
                uci = from_sq + to_sq + promo.lower()
                try:
                    candidate = chess.Move.from_uci(uci)
                    if candidate in board.legal_moves:
                        move_obj = candidate
                except Exception:
                    pass

            # Method 2: SAN fallback
            if move_obj is None and msg.get("san"):
                try:
                    candidate = board.parse_san(msg["san"])
                    if candidate in board.legal_moves:
                        move_obj = candidate
                except Exception:
                    pass

            if move_obj is None:
                try:
                    await websocket.send_json({"type": "error", "message": "Illegal move"})
                except Exception:
                    pass
                continue

            # Apply
            san_str = board.san(move_obj)
            board.push(move_obj)
            new_fen = board.fen()
            manager.update_state(game_id, new_fen, san_str)

            # Is king in check?
            in_check = board.is_check()

            await manager.broadcast(game_id, {
                "type": "move",
                "fen": new_fen,
                "san": san_str,
                "uci": move_obj.uci(),
                "history": manager.move_history.get(game_id, []),
                "in_check": in_check,
            })

            if board.is_game_over():
                result_str = board.result()  # '1-0', '0-1', '1/2-1/2'
                is_checkmate = board.is_checkmate()

                await manager.broadcast(game_id, {
                    "type": "game_over",
                    "result": result_str,
                    "is_checkmate": is_checkmate,
                })

                # Save to database
                await save_game_result(game_id, result_str)

    except WebSocketDisconnect:
        logger.info(f"User {user.id} left game {game_id}")
    except Exception as e:
        logger.error(f"WS error game={game_id}: {e}", exc_info=True)
    finally:
        manager.disconnect(websocket, game_id)
