"""
CAMS Model Base — Shared base class, mixins, and enum definitions.

Enum strategy: VARCHAR + CheckConstraint (không dùng native PostgreSQL ENUM
vì khó ALTER sau này). Validate bằng Python enum, lưu DB dưới dạng VARCHAR.
"""

import enum
import uuid
from datetime import datetime, timezone

from sqlalchemy import CheckConstraint, Column, DateTime, String, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    """Base class cho tất cả SQLAlchemy models."""
    pass


class TimestampMixin:
    """Mixin thêm created_at và updated_at tự động."""

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=text("NOW()"),
        nullable=False,
    )
    updated_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        server_default=text("NOW()"),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=True,
    )


class UUIDMixin:
    """Mixin thêm UUID primary key."""

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )


# ============================================================
# ENUM definitions — dùng Python enum, lưu DB dưới dạng VARCHAR
# ============================================================

class SubscriptionPlan(str, enum.Enum):
    FREE = "free"
    BASIC = "basic"
    PREMIUM = "premium"


class UserRole(str, enum.Enum):
    SUPER_ADMIN = "super_admin"
    ADMIN = "admin"
    TEACHER = "teacher"
    STUDENT = "student"
    PARENT = "parent"


class ClassLevel(str, enum.Enum):
    BEGINNER = "beginner"
    INTERMEDIATE = "intermediate"
    ADVANCED = "advanced"
    EXPERT = "expert"


class EnrollmentStatus(str, enum.Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"
    GRADUATED = "graduated"


class PuzzleDifficulty(str, enum.Enum):
    EASY = "easy"
    MEDIUM = "medium"
    HARD = "hard"
    EXPERT = "expert"


class PuzzleType(str, enum.Enum):
    TACTIC = "tactic"
    ENDGAME = "endgame"
    OPENING = "opening"
    STRATEGY = "strategy"
    CUSTOM = "custom"
    MATE_IN_1 = "mate_in_1"
    MATE_IN_2 = "mate_in_2"
    MATE_IN_3 = "mate_in_3"


class PuzzleSource(str, enum.Enum):
    MANUAL_FEN = "manual_fen"
    MANUAL_PGN = "manual_pgn"
    AI_SCANNED = "ai_scanned"
    IMPORTED = "imported"


class ProgressStatus(str, enum.Enum):
    NOT_STARTED = "not_started"
    IN_PROGRESS = "in_progress"
    SOLVED = "solved"
    FAILED = "failed"


class GradingMethod(str, enum.Enum):
    AUTO_AI = "auto_ai"
    MANUAL_TEACHER = "manual_teacher"


class PaymentMethod(str, enum.Enum):
    BANK_TRANSFER = "bank_transfer"
    CASH = "cash"
    CARD = "card"
    EWALLET = "ewallet"


class PaymentProvider(str, enum.Enum):
    VIETQR = "vietqr"
    PAYOS = "payos"
    VNPAY = "vnpay"
    MOMO = "momo"
    ZALOPAY = "zalopay"


class PaymentLevel(str, enum.Enum):
    LEVEL1_MANUAL = "level1_manual"
    LEVEL2_WEBHOOK = "level2_webhook"
    LEVEL3_GATEWAY = "level3_gateway"


class PaymentStatus(str, enum.Enum):
    PENDING = "pending"
    SUCCESS = "success"
    FAILED = "failed"
    REFUNDED = "refunded"


class InvoiceStatus(str, enum.Enum):
    DRAFT = "draft"
    SENT = "sent"
    PAID = "paid"
    OVERDUE = "overdue"
    CANCELLED = "cancelled"


class ScanStatus(str, enum.Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class ReviewStatus(str, enum.Enum):
    PENDING = "pending"
    APPROVED = "approved"
    CORRECTED = "corrected"
    REJECTED = "rejected"
    AUTO_APPROVED = "auto_approved"


class TournamentStatus(str, enum.Enum):
    DRAFT = "draft"
    REGISTRATION = "registration"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class TournamentFormat(str, enum.Enum):
    SWISS = "swiss"
    ROUND_ROBIN = "round_robin"
    ELIMINATION = "elimination"


class GameResult(str, enum.Enum):
    WHITE_WINS = "white_wins"
    BLACK_WINS = "black_wins"
    DRAW = "draw"
    NOT_PLAYED = "not_played"


class NotificationType(str, enum.Enum):
    ASSIGNMENT = "assignment"
    GRADE = "grade"
    PAYMENT = "payment"
    TOURNAMENT = "tournament"
    SYSTEM = "system"


class BillingCycle(str, enum.Enum):
    MONTHLY = "monthly"
    QUARTERLY = "quarterly"
    SEMESTER = "semester"
    YEARLY = "yearly"


def enum_check_constraint(column_name: str, enum_class: type[enum.Enum]) -> CheckConstraint:
    """
    Tạo CheckConstraint cho VARCHAR column dựa trên Python Enum values.

    Ví dụ: enum_check_constraint("role", UserRole)
    → CHECK (role IN ('super_admin', 'admin', 'teacher', 'student', 'parent'))
    """
    values = ", ".join(f"'{e.value}'" for e in enum_class)
    return CheckConstraint(
        f"{column_name} IN ({values})",
        name=f"ck_{column_name}_enum",
    )
