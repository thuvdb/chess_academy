"""
Models: scan_jobs, scan_results — Depends on users, centers, puzzles.
"""

import uuid

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import (
    Base,
    TimestampMixin,
    UUIDMixin,
    ReviewStatus,
    ScanStatus,
    enum_check_constraint,
)


class ScanJob(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "scan_jobs"
    __table_args__ = (
        enum_check_constraint("status", ScanStatus),
    )

    center_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("centers.id"), nullable=False,
    )
    uploaded_by: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=False,
    )
    file_name: Mapped[str] = mapped_column(String(500), nullable=False)
    file_url: Mapped[str] = mapped_column(String(500), nullable=False)
    file_size: Mapped[int | None] = mapped_column(Integer)
    total_pages: Mapped[int | None] = mapped_column(Integer)
    boards_found: Mapped[int] = mapped_column(Integer, default=0)
    boards_approved: Mapped[int] = mapped_column(Integer, default=0)
    status: Mapped[str] = mapped_column(
        String(20), default=ScanStatus.PENDING.value,
    )
    error_message: Mapped[str | None] = mapped_column(Text)
    processing_time_ms: Mapped[int | None] = mapped_column(Integer)

    # Relationships
    results: Mapped[list["ScanResult"]] = relationship(
        back_populates="job", lazy="selectin", cascade="all, delete-orphan"
    )
    uploader: Mapped["User"] = relationship(lazy="selectin")


class ScanResult(UUIDMixin, Base):
    __tablename__ = "scan_results"
    __table_args__ = (
        enum_check_constraint("review_status", ReviewStatus),
        UniqueConstraint(
            "job_id", "page_number", "board_index",
            name="uq_scan_result_page_board",
        ),
    )

    job_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("scan_jobs.id"), nullable=False,
    )
    page_number: Mapped[int] = mapped_column(Integer, nullable=False)
    board_index: Mapped[int] = mapped_column(Integer, nullable=False)
    board_image_url: Mapped[str | None] = mapped_column(String(500))
    bounding_box: Mapped[dict | None] = mapped_column(JSONB)
    confidence_board: Mapped[float | None] = mapped_column(Numeric(4, 2))

    # FEN fields — Board FEN (từ AI) + metadata (từ Human Review)
    fen_candidate: Mapped[str | None] = mapped_column(String(200))
    fen_final: Mapped[str | None] = mapped_column(String(200))
    side_to_move: Mapped[str] = mapped_column(String(1), default="w")
    castling_rights: Mapped[str] = mapped_column(String(4), default="-")
    en_passant: Mapped[str] = mapped_column(String(2), default="-")

    # Per-cell confidence
    cell_confidence: Mapped[dict | None] = mapped_column(JSONB)

    # Review
    review_status: Mapped[str] = mapped_column(
        String(20), default=ReviewStatus.PENDING.value,
    )
    reviewed_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"),
    )
    reviewed_at: Mapped[str | None] = mapped_column(DateTime(timezone=True))

    # Link to created puzzle (sau khi approve)
    puzzle_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("puzzles.id"),
    )

    # Relationships
    job: Mapped["ScanJob"] = relationship(back_populates="results")
    reviewer: Mapped["User"] = relationship(lazy="selectin")
    puzzle: Mapped["Puzzle"] = relationship(lazy="selectin")


from typing import TYPE_CHECKING  # noqa: E402

if TYPE_CHECKING:
    from app.models.puzzle import Puzzle
    from app.models.user import User
