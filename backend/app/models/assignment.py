"""
Models: assignments — Depends on classes, users, puzzles.
"""

import uuid

from sqlalchemy import DateTime, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import ARRAY, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDMixin


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
    due_date: Mapped[str | None] = mapped_column(DateTime(timezone=True))
    max_attempts: Mapped[int | None] = mapped_column(default=3)

    # Relationships
    class_: Mapped["Class"] = relationship(lazy="selectin")
    teacher: Mapped["User"] = relationship(lazy="selectin")


from typing import TYPE_CHECKING  # noqa: E402

if TYPE_CHECKING:
    from app.models.class_ import Class
    from app.models.user import User
