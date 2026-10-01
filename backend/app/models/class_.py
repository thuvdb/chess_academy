"""
Models: classes, class_enrollments — Depends on centers, branches, users.
"""

import uuid
import sqlalchemy

from sqlalchemy import Boolean, ForeignKey, Integer, String
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import (
    Base,
    TimestampMixin,
    UUIDMixin,
    ClassLevel,
    EnrollmentStatus,
    enum_check_constraint,
)


class Class(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "classes"
    __table_args__ = (
        enum_check_constraint("level", ClassLevel),
    )

    center_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("centers.id"),
    )
    branch_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("branches.id"),
    )
    teacher_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"),
    )
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    level: Mapped[str | None] = mapped_column(String(20))
    max_students: Mapped[int] = mapped_column(Integer, default=30)
    schedule_json: Mapped[dict | None] = mapped_column(JSONB)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    # Relationships
    teacher: Mapped["User"] = relationship(lazy="selectin")
    enrollments: Mapped[list["ClassEnrollment"]] = relationship(
        back_populates="class_", lazy="selectin",
    )


class ClassEnrollment(UUIDMixin, Base):
    __tablename__ = "class_enrollments"
    __table_args__ = (
        enum_check_constraint("status", EnrollmentStatus),
    )

    class_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("classes.id"), nullable=False,
    )
    student_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=False,
    )
    enrolled_at: Mapped[str] = mapped_column(
        sqlalchemy.DateTime(timezone=True),
        server_default=sqlalchemy.text("NOW()"),
    )
    status: Mapped[str] = mapped_column(
        String(20), default=EnrollmentStatus.ACTIVE.value,
    )

    # Relationships
    class_: Mapped["Class"] = relationship(back_populates="enrollments")
    student: Mapped["User"] = relationship(lazy="selectin")


from typing import TYPE_CHECKING  # noqa: E402

if TYPE_CHECKING:
    from app.models.user import User
