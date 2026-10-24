"""
CAMS AI Settings Models — Dynamic LLM Providers and Configurations.
Allows superadmins to configure and switch AI providers, models, and fallbacks at runtime.
"""
import uuid
from datetime import datetime, timezone
from typing import Any, Optional

from sqlalchemy import (
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    JSON,
    String,
    Text,
    text,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDMixin


class AIProvider(Base, UUIDMixin, TimestampMixin):
    """LLM Provider definition (Google Gemini, OpenAI compatible, etc.)."""

    __tablename__ = "ai_providers"

    name: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    type: Mapped[str] = mapped_column(String(50), nullable=False)  # 'gemini' | 'openai_compatible'
    base_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    api_key_encrypted: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    models: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    reasoning_effort: Mapped[Optional[str]] = mapped_column(String(20), nullable=True, default=None)

    def __repr__(self) -> str:
        return f"<AIProvider name={self.name} type={self.type} enabled={self.enabled}>"


class AISettings(Base):
    """
    Singleton AI configuration table for CAMS AI Tutor.
    Controls default provider, fallback provider, generation params, and resilience.
    """

    __tablename__ = "ai_settings"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    default_provider_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("ai_providers.id", ondelete="SET NULL"),
        nullable=True,
    )
    default_model: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        default="gemini-3.8-flash",
    )
    fallback_provider_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("ai_providers.id", ondelete="SET NULL"),
        nullable=True,
    )
    fallback_model: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    temperature: Mapped[float] = mapped_column(Float, default=0.7, nullable=False)
    max_output_tokens: Mapped[int] = mapped_column(Integer, default=1500, nullable=False)
    request_timeout_seconds: Mapped[int] = mapped_column(Integer, default=30, nullable=False)
    max_retries: Mapped[int] = mapped_column(Integer, default=2, nullable=False)
    updated_by: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=text("NOW()"),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    default_provider = relationship("AIProvider", foreign_keys=[default_provider_id])
    fallback_provider = relationship("AIProvider", foreign_keys=[fallback_provider_id])
    updater = relationship("User", foreign_keys=[updated_by])

    def __repr__(self) -> str:
        return f"<AISettings default_model={self.default_model} fallback_model={self.fallback_model}>"


class AISettingsAudit(Base):
    """Audit log for changes made to AI providers and settings."""

    __tablename__ = "ai_settings_audit"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    user_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    action: Mapped[str] = mapped_column(String(50), nullable=False)
    details: Mapped[Optional[dict[str, Any]]] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=text("NOW()"),
        nullable=False,
    )

    user = relationship("User", foreign_keys=[user_id])

    def __repr__(self) -> str:
        return f"<AISettingsAudit action={self.action} user_id={self.user_id}>"
