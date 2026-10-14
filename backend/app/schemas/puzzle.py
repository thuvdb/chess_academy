"""
Pydantic schemas for Puzzle API — Sprint 4
"""

import uuid
from datetime import datetime
from typing import Any, Literal
from pydantic import BaseModel, ConfigDict, Field, field_serializer


# ── Puzzle Solution ──────────────────────────────────────────

class PuzzleSolutionBase(BaseModel):
    move_order: int
    move_uci: str
    # SAN do backend sinh khi replay trên bàn cờ — client không cần gửi
    # (trước đây frontend gửi move_san = move_uci, hiển thị sai ký hiệu cờ).
    move_san: str = ""
    side: Literal["w", "b"] | None = None
    is_best_move: bool = True
    alternative_moves: list[str] | None = None
    explanation: str | None = None


class PuzzleSolutionCreate(PuzzleSolutionBase):
    pass


class PuzzleSolutionRead(PuzzleSolutionBase):
    id: uuid.UUID
    puzzle_id: uuid.UUID

    model_config = ConfigDict(from_attributes=True)


# ── Puzzle ───────────────────────────────────────────────────

class PuzzleBase(BaseModel):
    title: str = Field(..., max_length=300)
    description: str | None = None
    fen: str = Field(..., max_length=200)
    pgn: str | None = None
    difficulty: str | None = "easy"
    puzzle_type: str | None = "tactic"
    source: str | None = "manual_fen"
    tags: list[str] | None = None
    rating: int = 1200
    board_image_url: str | None = None


class PuzzleCreate(PuzzleBase):
    center_id: uuid.UUID | None = None
    solutions: list[PuzzleSolutionCreate] = []


class PuzzleUpdate(BaseModel):
    title: str | None = None
    description: str | None = None
    fen: str | None = None
    pgn: str | None = None
    difficulty: str | None = None
    puzzle_type: str | None = None
    tags: list[str] | None = None
    rating: int | None = None
    board_image_url: str | None = None
    solutions: list[PuzzleSolutionCreate] | None = None


class PuzzleRead(PuzzleBase):
    id: uuid.UUID
    center_id: uuid.UUID | None = None
    created_by: uuid.UUID | None = None
    play_count: int = 0
    success_rate: int | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None
    solutions: list[PuzzleSolutionRead] = []

    # Cây biến thể: tách nước của bên tấn công khỏi mọi đáp trả của đối phương.
    # Xem app/services/mate_solver.py để biết cấu trúc nút.
    solution_tree: dict[str, Any] | None = None
    mate_in: int | None = None
    solution_verified: bool = False
    solution_verified_at: datetime | None = None
    verification_error: str | None = None

    model_config = ConfigDict(from_attributes=True)

    @field_serializer("board_image_url")
    def _ser_board_image_url(self, v: str | None) -> str | None:
        from app.services.storage_service import get_access_url
        return get_access_url(v)


class CreatePuzzleFromScanRequest(BaseModel):
    scan_result_id: uuid.UUID
    title: str
    description: str | None = None
    difficulty: str = "easy"
    puzzle_type: str = "tactic"
    tags: list[str] | None = None
    solutions: list[PuzzleSolutionCreate] = []


# ── Kiểm tra lời giải trước khi lưu ──────────────────────────

class ValidateSolutionRequest(BaseModel):
    fen: str = Field(..., max_length=200)
    moves_uci: list[str] = Field(default_factory=list)
    puzzle_type: str | None = None


class PlyCheckRead(BaseModel):
    index: int
    uci: str
    san: str | None = None
    side: Literal["w", "b"] | None = None
    legal: bool = False
    is_player_move: bool = False
    forces_mate: bool | None = None
    error: str | None = None


class ValidateSolutionResponse(BaseModel):
    ok: bool
    fen: str
    player_color: Literal["w", "b"]
    plies: list[PlyCheckRead] = []
    ends_in_mate: bool = False
    mate_in: int | None = None
    declared_mate_in: int | None = None
    expected_plies: int | None = None
    errors: list[str] = []
    warnings: list[str] = []
    # Hai danh sách tách riêng — thay cho một mảng chung trộn lẫn hai bên
    player_moves: list[PlyCheckRead] = []
    opponent_moves: list[PlyCheckRead] = []
    solution_tree: dict[str, Any] | None = None
