import json
import logging
from typing import Dict, Optional
from uuid import UUID
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
import redis.asyncio as redis
import chess

from app.core.config import settings
from app.api.deps import get_db, get_current_user_from_token

router = APIRouter()
logger = logging.getLogger(__name__)

# Basic connection manager for in-memory tracking
class ConnectionManager:
    def __init__(self):
        # game_id -> list of active connections
        self.active_connections: Dict[str, list[WebSocket]] = {}
        # game_id -> fen
        self.game_states: Dict[str, str] = {}

    async def connect(self, websocket: WebSocket, game_id: str):
        await websocket.accept()
        if game_id not in self.active_connections:
            self.active_connections[game_id] = []
            self.game_states[game_id] = chess.STARTING_FEN
        self.active_connections[game_id].append(websocket)
        
        # Send current state
        await self.send_state(game_id, websocket)

    def disconnect(self, websocket: WebSocket, game_id: str):
        if game_id in self.active_connections:
            if websocket in self.active_connections[game_id]:
                self.active_connections[game_id].remove(websocket)
            if not self.active_connections[game_id]:
                del self.active_connections[game_id]

    async def broadcast(self, game_id: str, message: dict):
        if game_id in self.active_connections:
            for connection in self.active_connections[game_id]:
                try:
                    await connection.send_json(message)
                except Exception as e:
                    logger.error(f"Error broadcasting to ws: {e}")

    async def send_state(self, game_id: str, websocket: WebSocket):
        fen = self.game_states.get(game_id, chess.STARTING_FEN)
        await websocket.send_json({
            "type": "game_state",
            "fen": fen,
        })
        
    def get_board(self, game_id: str) -> chess.Board:
        fen = self.game_states.get(game_id, chess.STARTING_FEN)
        return chess.Board(fen)
        
    def update_fen(self, game_id: str, fen: str):
        self.game_states[game_id] = fen


manager = ConnectionManager()

# NOTE: In a real distributed system, we would use Redis Pub/Sub here.
# For MVP, we will use in-memory ConnectionManager + basic Redis fallback later if needed.

@router.websocket("/ws/game/{game_id}")
async def websocket_endpoint(
    websocket: WebSocket,
    game_id: str,
    token: str = Query(...),
    db: AsyncSession = Depends(get_db)
):
    try:
        user = await get_current_user_from_token(token, db)
    except Exception as e:
        logger.error(f"WebSocket auth failed: {e}")
        await websocket.close(code=1008)
        return

    await manager.connect(websocket, game_id)
    
    try:
        while True:
            data = await websocket.receive_text()
            try:
                message = json.loads(data)
                msg_type = message.get("type")
                
                if msg_type == "move":
                    san_move = message.get("san")
                    board = manager.get_board(game_id)
                    try:
                        # Validate move
                        move = board.parse_san(san_move)
                        board.push(move)
                        manager.update_fen(game_id, board.fen())
                        
                        # Broadcast new state
                        await manager.broadcast(game_id, {
                            "type": "move",
                            "san": san_move,
                            "fen": board.fen()
                        })
                        
                        if board.is_game_over():
                            await manager.broadcast(game_id, {
                                "type": "game_over",
                                "result": board.result()
                            })
                            
                    except ValueError:
                        await websocket.send_json({
                            "type": "error",
                            "message": "Invalid move"
                        })
                        
            except json.JSONDecodeError:
                pass
                
    except WebSocketDisconnect:
        manager.disconnect(websocket, game_id)
