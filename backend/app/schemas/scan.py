"""
Pydantic schemas for Scan API — Sprint 3A
"""

import uuid
from datetime import datetime
from pydantic import BaseModel, ConfigDict


# ── ScanJob ─────────────────────────────────────────────────

class ScanJobRead(BaseModel):
    id: uuid.UUID
    center_id: uuid.UUID
    uploaded_by: uuid.UUID
    file_name: str
    file_url: str
    file_size: int | None = None
    total_pages: int | None = None
    boards_found: int = 0
    boards_approved: int = 0
    status: str
    error_message: str | None = None
    processing_time_ms: int | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None

    model_config = ConfigDict(from_attributes=True)


# ── ScanResult ──────────────────────────────────────────────

class ScanResultRead(BaseModel):
    id: uuid.UUID
    job_id: uuid.UUID
    page_number: int
    board_index: int
    board_image_url: str | None = None
    bounding_box: dict | None = None
    confidence_board: float | None = None
    fen_candidate: str | None = None
    fen_final: str | None = None
    side_to_move: str = "w"
    castling_rights: str = "-"
    en_passant: str = "-"
    cell_confidence: dict | None = None
    review_status: str = "pending"
    reviewed_by: uuid.UUID | None = None
    reviewed_at: datetime | None = None
    puzzle_id: uuid.UUID | None = None

    model_config = ConfigDict(from_attributes=True)


# ── Review Request ──────────────────────────────────────────

class ScanResultReviewRequest(BaseModel):
    """Body for PUT /scan/results/{id}/review — teacher corrects FEN."""
    fen_final: str
    side_to_move: str = "w"
    castling_rights: str = "-"
    en_passant: str = "-"
