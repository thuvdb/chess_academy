"""
Models: assignments — Depends on classes, users, puzzles.
"""

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Index, Integer, String, Text
from sqlalchemy.dialects.postgresql import ARRAY, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import (
    Base,
    SubmissionStatus,
    TimestampMixin,
    UUIDMixin,
    enum_check_constraint,
)


class Assignment(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "assignments"

    class_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("classes.id"), nullable=False,
    )
    teacher_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=False,
    )
    title: Mapped[str] = mapped_column(String(300), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    puzzle_ids: Mapped[list[str] | None] = mapped_column(ARRAY(UUID(as_uuid=True)))
    due_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    max_attempts: Mapped[int | None] = mapped_column(default=3)

    # Relationships
    class_: Mapped["Class"] = relationship(lazy="selectin")
    teacher: Mapped["User"] = relationship(lazy="selectin")


class AssignmentSubmission(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "assignment_submissions"
    __table_args__ = (
        enum_check_constraint("status", SubmissionStatus),
        Index(
            "uq_assignment_submission_attempt",
            "assignment_id",
            "student_id",
            "attempt_no",
            unique=True,
        ),
    )

    assignment_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("assignments.id", ondelete="CASCADE"), nullable=False,
    )
    student_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=False,
    )
    attempt_no: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    version: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    status: Mapped[str] = mapped_column(
        String(30), default=SubmissionStatus.IN_PROGRESS.value, nullable=False,
    )
    submitted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    total_points: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    completed_puzzles: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    # Audit log khi giáo viên mở lại bài
    reopened_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    reopened_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"),
    )
    reopen_reason: Mapped[str | None] = mapped_column(Text)

    # Chấm bài & Trả bài của giáo viên
    teacher_feedback: Mapped[str | None] = mapped_column(Text)
    graded_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    graded_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"),
    )
    teacher_adjustment: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    # Relationships
    assignment: Mapped["Assignment"] = relationship(lazy="selectin")
    student: Mapped["User"] = relationship(foreign_keys=[student_id], lazy="selectin")
    reopened_by_user: Mapped["User | None"] = relationship(foreign_keys=[reopened_by], lazy="selectin")
    graded_by_user: Mapped["User | None"] = relationship(foreign_keys=[graded_by], lazy="selectin")



from typing import TYPE_CHECKING  # noqa: E402

if TYPE_CHECKING:
    from app.models.class_ import Class
    from app.models.user import User
