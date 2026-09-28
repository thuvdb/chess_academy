"""
Models: student_progress, student_attempts — Depends on users, puzzles, assignments.
"""

import uuid

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import ARRAY, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import (
    Base,
    TimestampMixin,
    UUIDMixin,
    GradingMethod,
    ProgressStatus,
    enum_check_constraint,
)


class StudentProgress(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "student_progress"
    __table_args__ = (
        enum_check_constraint("status", ProgressStatus),
        enum_check_constraint("grading_method", GradingMethod),
    )

    student_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=False,
    )
    puzzle_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("puzzles.id"), nullable=False,
    )
    assignment_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("assignments.id"),
    )
    status: Mapped[str] = mapped_column(
        String(20), default=ProgressStatus.NOT_STARTED.value,
    )
    attempts: Mapped[int] = mapped_column(Integer, default=0)
    hints_used: Mapped[int] = mapped_column(Integer, default=0)
    time_spent_seconds: Mapped[int] = mapped_column(Integer, default=0)
    error_moves: Mapped[list[str] | None] = mapped_column(ARRAY(String))

    # Chấm điểm
    points_earned: Mapped[int] = mapped_column(Integer, default=0)
    grading_method: Mapped[str | None] = mapped_column(String(20))
    graded_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"),
    )
    teacher_feedback: Mapped[str | None] = mapped_column(Text)
    graded_at: Mapped[str | None] = mapped_column(DateTime(timezone=True))

    solved_at: Mapped[str | None] = mapped_column(DateTime(timezone=True))

    # Relationships
    student: Mapped["User"] = relationship(
        foreign_keys=[student_id], lazy="selectin",
    )
    puzzle: Mapped["Puzzle"] = relationship(lazy="selectin")
    attempt_details: Mapped[list["StudentAttempt"]] = relationship(
        back_populates="progress", lazy="selectin",
    )


class StudentAttempt(UUIDMixin, Base):
    """Chi tiết từng lần làm bài (replay nước đi)."""

    __tablename__ = "student_attempts"
    __table_args__ = (
        UniqueConstraint("progress_id", "attempt_no", name="uq_attempt_progress_no"),
    )

    progress_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("student_progress.id"), nullable=False,
    )
    attempt_no: Mapped[int] = mapped_column(Integer, nullable=False)
    moves_uci: Mapped[list[str] | None] = mapped_column(ARRAY(String))
    moves_san: Mapped[list[str] | None] = mapped_column(ARRAY(String))
    pgn: Mapped[str | None] = mapped_column(Text)
    is_correct: Mapped[bool | None] = mapped_column(Boolean)
    hint_used: Mapped[bool] = mapped_column(Boolean, default=False)
    points_earned: Mapped[int] = mapped_column(Integer, default=0)
    result: Mapped[str | None] = mapped_column(String(30))
    started_at: Mapped[str | None] = mapped_column(DateTime(timezone=True))
    completed_at: Mapped[str | None] = mapped_column(DateTime(timezone=True))

    # Relationships
    progress: Mapped["StudentProgress"] = relationship(back_populates="attempt_details")


from typing import TYPE_CHECKING  # noqa: E402

if TYPE_CHECKING:
    from app.models.puzzle import Puzzle
    from app.models.user import User
