"""
Models: fee_plans, invoices, payments, payment_webhook_logs.
Depends on centers, users, classes.
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
    BillingCycle,
    InvoiceStatus,
    PaymentLevel,
    PaymentMethod,
    PaymentProvider,
    PaymentStatus,
    enum_check_constraint,
)


class FeePlan(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "fee_plans"
    __table_args__ = (
        enum_check_constraint("billing_cycle", BillingCycle),
    )

    center_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("centers.id"), nullable=False,
    )
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    amount: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False)
    currency: Mapped[str] = mapped_column(String(3), default="VND")
    billing_cycle: Mapped[str] = mapped_column(
        String(20), default=BillingCycle.MONTHLY.value,
    )
    description: Mapped[str | None] = mapped_column(Text)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)


class Invoice(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "invoices"
    __table_args__ = (
        enum_check_constraint("status", InvoiceStatus),
    )

    center_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("centers.id"), nullable=False,
    )
    student_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=False,
    )
    class_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("classes.id"),
    )
    fee_plan_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("fee_plans.id"),
    )
    invoice_number: Mapped[str] = mapped_column(
        String(50), unique=True, nullable=False,
    )
    amount: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False)
    currency: Mapped[str] = mapped_column(String(3), default="VND")
    description: Mapped[str | None] = mapped_column(Text)
    status: Mapped[str] = mapped_column(
        String(20), default=InvoiceStatus.DRAFT.value,
    )
    due_date: Mapped[str | None] = mapped_column(DateTime(timezone=True))
    period_start: Mapped[str | None] = mapped_column(DateTime(timezone=True))
    period_end: Mapped[str | None] = mapped_column(DateTime(timezone=True))

    # Relationships
    student: Mapped["User"] = relationship(lazy="selectin")
    payments: Mapped[list["Payment"]] = relationship(
        back_populates="invoice", lazy="selectin",
    )


class Payment(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "payments"
    __table_args__ = (
        enum_check_constraint("payment_method", PaymentMethod),
        enum_check_constraint("payment_provider", PaymentProvider),
        enum_check_constraint("payment_level", PaymentLevel),
        enum_check_constraint("status", PaymentStatus),
        UniqueConstraint(
            "payment_provider", "provider_transaction_id",
            name="uq_payment_provider_txn",
        ),
    )

    invoice_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("invoices.id"),
    )
    payer_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"),
    )
    amount: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False)
    currency: Mapped[str] = mapped_column(String(3), default="VND")
    payment_method: Mapped[str | None] = mapped_column(String(20))
    payment_provider: Mapped[str | None] = mapped_column(String(20))
    payment_level: Mapped[str] = mapped_column(
        String(20), default=PaymentLevel.LEVEL1_MANUAL.value,
    )
    transaction_id: Mapped[str | None] = mapped_column(String(200))
    provider_order_id: Mapped[str | None] = mapped_column(String(200))
    provider_transaction_id: Mapped[str | None] = mapped_column(String(200))
    payment_link_id: Mapped[str | None] = mapped_column(String(200))
    reference: Mapped[str | None] = mapped_column(String(200))
    idempotency_key: Mapped[str | None] = mapped_column(String(200), unique=True)
    signature_verified: Mapped[bool] = mapped_column(Boolean, default=False)
    status: Mapped[str] = mapped_column(
        String(20), default=PaymentStatus.PENDING.value,
    )
    confirmed_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"),
    )
    payment_data: Mapped[dict | None] = mapped_column(JSONB)
    paid_at: Mapped[str | None] = mapped_column(DateTime(timezone=True))

    # Relationships
    invoice: Mapped["Invoice"] = relationship(back_populates="payments")
    payer: Mapped["User"] = relationship(
        foreign_keys=[payer_id], lazy="selectin",
    )


class PaymentWebhookLog(UUIDMixin, Base):
    """Audit trail: log tất cả webhook calls (kể cả duplicates, failures)."""

    __tablename__ = "payment_webhook_logs"

    provider: Mapped[str] = mapped_column(String(50), nullable=False)
    raw_payload: Mapped[dict] = mapped_column(JSONB, nullable=False)
    signature_verified: Mapped[bool | None] = mapped_column(Boolean)
    processing_result: Mapped[str | None] = mapped_column(String(50))
    payment_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("payments.id"),
    )
    created_at: Mapped[str] = mapped_column(
        DateTime(timezone=True),
        server_default=__import__("sqlalchemy").text("NOW()"),
    )


from typing import TYPE_CHECKING  # noqa: E402

if TYPE_CHECKING:
    from app.models.user import User
