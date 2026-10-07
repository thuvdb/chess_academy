"""
Pydantic schemas for Puzzle API — Sprint 4
"""

import uuid
from datetime import datetime
from pydantic import BaseModel, ConfigDict, Field, field_serializer


# ── Puzzle Solution ──────────────────────────────────────────

class PuzzleSolutionBase(BaseModel):
    move_order: int
    move_uci: str
    move_san: str
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
    difficulty: str | None = "beginner"
    puzzle_type: str | None = "tactics"
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

    model_config = ConfigDict(from_attributes=True)

    @field_serializer("board_image_url")
    def _ser_board_image_url(self, v: str | None) -> str | None:
        from app.services.storage_service import get_access_url
        return get_access_url(v)


class CreatePuzzleFromScanRequest(BaseModel):
    scan_result_id: uuid.UUID
    title: str
    description: str | None = None
    difficulty: str = "beginner"
    puzzle_type: str = "tactics"
    tags: list[str] | None = None
    solutions: list[PuzzleSolutionCreate] = []
