"""
Models: notifications — Depends on users.
"""

import uuid

from sqlalchemy import Boolean, DateTime, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import (
    Base,
    UUIDMixin,
    NotificationType,
    enum_check_constraint,
)
import sqlalchemy


class Notification(UUIDMixin, Base):
    __tablename__ = "notifications"
    __table_args__ = (
        enum_check_constraint("type", NotificationType),
    )

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=False,
    )
    type: Mapped[str] = mapped_column(String(20), nullable=False)
    title: Mapped[str] = mapped_column(String(300), nullable=False)
    body: Mapped[str | None] = mapped_column(Text)
    is_read: Mapped[bool] = mapped_column(Boolean, default=False)
    ref_id: Mapped[str | None] = mapped_column(String(200))   # ID của entity liên quan
    ref_type: Mapped[str | None] = mapped_column(String(50))  # "assignment", "invoice", ...
    created_at: Mapped[str] = mapped_column(
        DateTime(timezone=True),
        server_default=sqlalchemy.text("NOW()"),
    )
    read_at: Mapped[str | None] = mapped_column(DateTime(timezone=True))

    # Relationships
    user: Mapped["User"] = relationship(lazy="selectin")


from typing import TYPE_CHECKING  # noqa: E402

if TYPE_CHECKING:
    from app.models.user import User
