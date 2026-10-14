"""
Models: users, parent_student — Depends on centers, branches.
"""

import uuid

from sqlalchemy import (
    Boolean,
    Date,
    DateTime,
    ForeignKey,
    Integer,
    String,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import (
    Base,
    TimestampMixin,
    UUIDMixin,
    UserRole,
    enum_check_constraint,
)


class User(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "users"
    __table_args__ = (
        enum_check_constraint("role", UserRole),
    )

    center_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("centers.id"),
    )
    primary_branch_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("branches.id"),
    )
    email: Mapped[str] = mapped_column(String(200), unique=True, nullable=False)
    password_hash: Mapped[str | None] = mapped_column(String(255))
    full_name: Mapped[str] = mapped_column(String(200), nullable=False)
    avatar_url: Mapped[str | None] = mapped_column(String(500))
    role: Mapped[str] = mapped_column(String(20), nullable=False)
    date_of_birth: Mapped[str | None] = mapped_column(Date)
    phone: Mapped[str | None] = mapped_column(String(20))
    elo_rating: Mapped[int] = mapped_column(Integer, default=800)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    google_id: Mapped[str | None] = mapped_column(String(200))
    facebook_id: Mapped[str | None] = mapped_column(String(200))
    last_login: Mapped[str | None] = mapped_column(DateTime(timezone=True))
    username: Mapped[str | None] = mapped_column(String(100), unique=True)
    bio: Mapped[str | None] = mapped_column(String(500))
    location: Mapped[str | None] = mapped_column(String(200))
    country: Mapped[str | None] = mapped_column(String(100))
    language: Mapped[str | None] = mapped_column(String(50))
    timezone: Mapped[str | None] = mapped_column(String(100))

    # Relationships
    center: Mapped["Center"] = relationship(lazy="selectin")
    primary_branch: Mapped["Branch"] = relationship(lazy="selectin")

    # Parent-student relationships
    children: Mapped[list["User"]] = relationship(
        secondary="parent_student",
        primaryjoin="User.id == parent_student.c.parent_id",
        secondaryjoin="User.id == parent_student.c.student_id",
        lazy="selectin",
    )
    parents: Mapped[list["User"]] = relationship(
        secondary="parent_student",
        primaryjoin="User.id == parent_student.c.student_id",
        secondaryjoin="User.id == parent_student.c.parent_id",
        lazy="selectin",
        viewonly=True,
    )

    @property
    def center_name(self) -> str | None:
        return self.center.name if self.center else None


# Association table — parent ↔ student (many-to-many)
from sqlalchemy import Column, Table  # noqa: E402

parent_student = Table(
    "parent_student",
    Base.metadata,
    Column("parent_id", UUID(as_uuid=True), ForeignKey("users.id"), primary_key=True),
    Column("student_id", UUID(as_uuid=True), ForeignKey("users.id"), primary_key=True),
)


# Avoid circular import — type hints only
from typing import TYPE_CHECKING  # noqa: E402

if TYPE_CHECKING:
    from app.models.center import Branch, Center
