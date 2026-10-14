"""
Models: puzzles, puzzle_solutions — Depends on centers, users.
"""

import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import ARRAY, JSONB, UUID
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

    # Lời giải dạng CÂY BIẾN THỂ: mỗi nút của bên tấn công giữ mọi nước ép được
    # mate, mỗi nước đó giữ mọi nước chống đỡ của bên phòng ngự. Xem
    # app/services/mate_solver.py. puzzle_solutions giữ main line rút từ cây này.
    solution_tree: Mapped[dict | None] = mapped_column(JSONB)
    mate_in: Mapped[int | None] = mapped_column(Integer)
    solution_verified: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default="false", default=False,
    )
    solution_verified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    verification_error: Mapped[str | None] = mapped_column(Text)

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
    # 'w' | 'b' — bên thực hiện nước này. Trước đây không có cột này nên nước
    # của hai bên nằm lẫn trong cùng một danh sách phẳng và UI gắn nhãn sai bên.
    side: Mapped[str | None] = mapped_column(String(1))
    is_best_move: Mapped[bool] = mapped_column(default=True)
    alternative_moves: Mapped[list[str] | None] = mapped_column(ARRAY(String))
    explanation: Mapped[str | None] = mapped_column(Text)

    # Relationships
    puzzle: Mapped["Puzzle"] = relationship(back_populates="solutions")
