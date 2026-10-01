"""
Pydantic schemas for Student Progress & Attempts API — Sprint 4
"""

import uuid
from datetime import datetime
from pydantic import BaseModel, ConfigDict


class StudentAttemptCreate(BaseModel):
    puzzle_id: uuid.UUID
    assignment_id: uuid.UUID | None = None
    moves_uci: list[str]
    moves_san: list[str] = []
    time_spent_seconds: int = 0
    hint_used: bool = False


class StudentAttemptRead(BaseModel):
    id: uuid.UUID
    progress_id: uuid.UUID
    attempt_no: int
    moves_uci: list[str] | None = None
    moves_san: list[str] | None = None
    is_correct: bool | None = None
    hint_used: bool = False
    points_earned: int = 0
    result: str | None = None
    started_at: datetime | None = None
    completed_at: datetime | None = None

    model_config = ConfigDict(from_attributes=True)


class StudentProgressRead(BaseModel):
    id: uuid.UUID
    student_id: uuid.UUID
    puzzle_id: uuid.UUID
    assignment_id: uuid.UUID | None = None
    status: str
    attempts: int
    hints_used: int
    time_spent_seconds: int
    points_earned: int
    grading_method: str | None = None
    teacher_feedback: str | None = None
    graded_at: datetime | None = None
    solved_at: datetime | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None

    model_config = ConfigDict(from_attributes=True)


class TeacherGradingRequest(BaseModel):
    points_earned: int
    teacher_feedback: str | None = None


class LeaderboardEntry(BaseModel):
    student_id: uuid.UUID
    full_name: str
    avatar_url: str | None = None
    rating: int
    puzzles_solved: int
    points: int
