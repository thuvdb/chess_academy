"""
Models: tournaments, tournament_participants, tournament_games, tournament_standings.
Depends on centers, users.
"""

import uuid

from sqlalchemy import (
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import (
    Base,
    TimestampMixin,
    UUIDMixin,
    GameResult,
    TournamentFormat,
    TournamentStatus,
    enum_check_constraint,
)


class Tournament(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "tournaments"
    __table_args__ = (
        enum_check_constraint("status", TournamentStatus),
        enum_check_constraint("format", TournamentFormat),
    )

    center_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("centers.id"), nullable=True,
    )
    created_by: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=False,
    )
    name: Mapped[str] = mapped_column(String(300), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    format: Mapped[str] = mapped_column(
        String(20), default=TournamentFormat.SWISS.value,
    )
    max_rounds: Mapped[int] = mapped_column(Integer, default=5)
    time_control: Mapped[str | None] = mapped_column(String(50))
    status: Mapped[str] = mapped_column(
        String(20), default=TournamentStatus.DRAFT.value,
    )
    start_date: Mapped[str | None] = mapped_column(DateTime(timezone=True))
    end_date: Mapped[str | None] = mapped_column(DateTime(timezone=True))

    # Relationships
    participants: Mapped[list["TournamentParticipant"]] = relationship(
        back_populates="tournament", lazy="selectin",
    )
    games: Mapped[list["TournamentGame"]] = relationship(
        back_populates="tournament", lazy="selectin",
    )
    standings: Mapped[list["TournamentStanding"]] = relationship(
        back_populates="tournament", lazy="selectin",
    )


class TournamentParticipant(UUIDMixin, Base):
    __tablename__ = "tournament_participants"

    tournament_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tournaments.id"), nullable=False,
    )
    student_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=False,
    )
    seed: Mapped[int | None] = mapped_column(Integer)
    registered_at: Mapped[str] = mapped_column(
        DateTime(timezone=True),
        server_default=__import__("sqlalchemy").text("NOW()"),
    )

    # Relationships
    tournament: Mapped["Tournament"] = relationship(back_populates="participants")
    student: Mapped["User"] = relationship(lazy="selectin")


class TournamentGame(UUIDMixin, Base):
    __tablename__ = "tournament_games"
    __table_args__ = (
        enum_check_constraint("result", GameResult),
    )

    tournament_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tournaments.id"), nullable=False,
    )
    round: Mapped[int] = mapped_column(Integer, nullable=False)
    white_player_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=False,
    )
    black_player_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=False,
    )
    result: Mapped[str] = mapped_column(
        String(20), default=GameResult.NOT_PLAYED.value,
    )
    pgn: Mapped[str | None] = mapped_column(Text)
    time_control: Mapped[str | None] = mapped_column(String(50))
    scheduled_at: Mapped[str | None] = mapped_column(DateTime(timezone=True))
    played_at: Mapped[str | None] = mapped_column(DateTime(timezone=True))

    # Relationships
    tournament: Mapped["Tournament"] = relationship(back_populates="games")
    white_player: Mapped["User"] = relationship(
        foreign_keys=[white_player_id], lazy="selectin",
    )
    black_player: Mapped["User"] = relationship(
        foreign_keys=[black_player_id], lazy="selectin",
    )


class TournamentStanding(UUIDMixin, Base):
    __tablename__ = "tournament_standings"

    tournament_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tournaments.id"), nullable=False,
    )
    student_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=False,
    )
    rank: Mapped[int | None] = mapped_column(Integer)
    points: Mapped[float] = mapped_column(Numeric(5, 1), default=0)
    wins: Mapped[int] = mapped_column(Integer, default=0)
    draws: Mapped[int] = mapped_column(Integer, default=0)
    losses: Mapped[int] = mapped_column(Integer, default=0)
    buchholz: Mapped[float | None] = mapped_column(Numeric(6, 1))

    # Relationships
    tournament: Mapped["Tournament"] = relationship(back_populates="standings")
    student: Mapped["User"] = relationship(lazy="selectin")


from typing import TYPE_CHECKING  # noqa: E402

if TYPE_CHECKING:
    from app.models.user import User
