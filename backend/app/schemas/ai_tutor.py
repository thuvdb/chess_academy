"""
CAMS AI Tutor Schemas — Pydantic models for chat requests and responses.
"""
import uuid
from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=1000, description="Nội dung câu hỏi của học viên")
    session_id: Optional[uuid.UUID] = Field(None, description="ID phiên trò chuyện (nếu tiếp tục hội thoại)")


class ChatMessageOut(BaseModel):
    id: uuid.UUID
    session_id: uuid.UUID
    role: str
    content: str
    board_data: Optional[dict[str, Any]] = None
    puzzle_data: Optional[Any] = None
    created_at: datetime

    class Config:
        from_attributes = True


class ChatSessionOut(BaseModel):
    id: uuid.UUID
    title: str
    created_at: datetime
    last_message: Optional[str] = None

    class Config:
        from_attributes = True


class ChatSessionDetailOut(ChatSessionOut):
    messages: list[ChatMessageOut] = []


class TTSRequest(BaseModel):
    message_id: uuid.UUID = Field(..., description="ID tin nhắn của trợ lý AI cần phát giọng đọc")
    voice: Optional[str] = Field(None, description="Tên giọng đọc (vi-VN-HoaiMyNeural hoặc vi-VN-NamMinhNeural)")


class PuzzleCheckRequest(BaseModel):
    move: str = Field(..., description="Nước đi của học viên (dạng UCI như 'e2e4' hoặc SAN như 'e4')")
    current_fen: str = Field(..., description="Thế cờ FEN hiện tại trước khi học viên đi")
    step_index: int = Field(0, ge=0, description="Thứ tự nước đi của học viên (0 cho nước đầu tiên)")
    session_id: Optional[uuid.UUID] = Field(None, description="ID phiên trò chuyện AI nếu có")


class OpponentMoveData(BaseModel):
    uci: str
    san: str


class PuzzleCheckResponse(BaseModel):
    is_correct: bool
    is_completed: bool
    opponent_move: Optional[OpponentMoveData] = None
    next_fen: str
    message: str


class PuzzleSolutionMove(BaseModel):
    move_order: int
    uci: str
    san: str
    side: str
    explanation: Optional[str] = None


class PuzzleSolutionResponse(BaseModel):
    puzzle_id: uuid.UUID
    title: str
    theme: str
    fen: str
    moves: list[PuzzleSolutionMove]


class PuzzleExplainResponse(BaseModel):
    puzzle_id: uuid.UUID
    explanation: str


