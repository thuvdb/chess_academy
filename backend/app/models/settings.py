"""
Models: settings, catalog_items — System configuration and dynamic lookup catalogs.
"""

import uuid
from sqlalchemy import Boolean, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDMixin


class CatalogItem(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "catalog_items"
    __table_args__ = (
        UniqueConstraint("catalog_type", "code", "center_id", name="uq_catalog_type_code_center"),
    )

    center_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("centers.id", ondelete="CASCADE"), nullable=True, index=True,
    )
    catalog_type: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    code: Mapped[str] = mapped_column(String(50), nullable=False)
    label: Mapped[str] = mapped_column(String(100), nullable=False)
    order_index: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    # Relationships
    center = relationship("Center", lazy="selectin")


class Setting(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "settings"
    __table_args__ = (
        UniqueConstraint("key", "center_id", name="uq_setting_key_center"),
    )

    center_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("centers.id", ondelete="CASCADE"), nullable=True, index=True,
    )
    key: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    value: Mapped[str] = mapped_column(Text, nullable=False)
    value_type: Mapped[str] = mapped_column(String(20), default="string", nullable=False)  # string, int, float, bool, json
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    category: Mapped[str] = mapped_column(String(50), default="general", nullable=False)  # general, rating, engine, scanner, security
    is_overridable: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    # Relationships
    center = relationship("Center", lazy="selectin")
