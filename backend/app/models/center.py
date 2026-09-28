"""
Models: centers, branches — Root entities, no FK dependencies.
"""

from sqlalchemy import Boolean, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import (
    Base,
    TimestampMixin,
    UUIDMixin,
    SubscriptionPlan,
    enum_check_constraint,
)


class Center(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "centers"
    __table_args__ = (
        enum_check_constraint("subscription_plan", SubscriptionPlan),
    )

    name: Mapped[str] = mapped_column(String(200), nullable=False)
    address: Mapped[str | None] = mapped_column(Text)
    logo_url: Mapped[str | None] = mapped_column(String(500))
    phone: Mapped[str | None] = mapped_column(String(20))
    email: Mapped[str | None] = mapped_column(String(200))
    facebook_page_url: Mapped[str | None] = mapped_column(String(500))
    subscription_plan: Mapped[str] = mapped_column(
        String(20), default=SubscriptionPlan.FREE.value,
    )

    # Relationships
    branches: Mapped[list["Branch"]] = relationship(
        back_populates="center", lazy="selectin",
    )


class Branch(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "branches"

    center_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("centers.id"), nullable=False,
    )
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    address: Mapped[str | None] = mapped_column(Text)
    phone: Mapped[str | None] = mapped_column(String(20))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    # Relationships
    center: Mapped["Center"] = relationship(back_populates="branches")


import uuid  # noqa: E402 — needed for UUID type hints
