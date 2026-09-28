"""
Models: puzzles, puzzle_solutions — Depends on centers, users.
"""

import uuid

from sqlalchemy import ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import ARRAY, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import (
    Base,
    TimestampMixin,
    UUIDMixin,
    PuzzleDifficulty,
    PuzzleSource,
    PuzzleType,
    enum_check_constraint,
)


class Puzzle(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "puzzles"
    __table_args__ = (
        enum_check_constraint("difficulty", PuzzleDifficulty),
        enum_check_constraint("puzzle_type", PuzzleType),
        enum_check_constraint("source", PuzzleSource),
    )

    center_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("centers.id"),
    )
    created_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"),
    )
    title: Mapped[str] = mapped_column(String(300), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    fen: Mapped[str] = mapped_column(String(200), nullable=False)
    pgn: Mapped[str | None] = mapped_column(Text)
    difficulty: Mapped[str | None] = mapped_column(String(20))
    puzzle_type: Mapped[str | None] = mapped_column(String(20))
    source: Mapped[str] = mapped_column(
        String(20), default=PuzzleSource.MANUAL_FEN.value,
    )
    tags: Mapped[list[str] | None] = mapped_column(ARRAY(String))
    rating: Mapped[int] = mapped_column(Integer, default=1200)
    play_count: Mapped[int] = mapped_column(Integer, default=0)
    success_rate: Mapped[int | None] = mapped_column(Integer)  # 0-100%
    board_image_url: Mapped[str | None] = mapped_column(String(500))

    # Relationships
    solutions: Mapped[list["PuzzleSolution"]] = relationship(
        back_populates="puzzle", lazy="selectin",
    )


class PuzzleSolution(UUIDMixin, Base):
    __tablename__ = "puzzle_solutions"

    puzzle_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("puzzles.id"), nullable=False,
    )
    move_order: Mapped[int] = mapped_column(Integer, nullable=False)
    move_uci: Mapped[str] = mapped_column(String(10), nullable=False)
    move_san: Mapped[str] = mapped_column(String(10), nullable=False)
    is_best_move: Mapped[bool] = mapped_column(default=True)
    alternative_moves: Mapped[list[str] | None] = mapped_column(ARRAY(String))
    explanation: Mapped[str | None] = mapped_column(Text)

    # Relationships
    puzzle: Mapped["Puzzle"] = relationship(back_populates="solutions")
