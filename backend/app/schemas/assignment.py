"""
Pydantic schemas for Assignment API — Sprint 4
"""

import uuid
from datetime import datetime
from pydantic import BaseModel, ConfigDict, Field


class AssignmentBase(BaseModel):
    class_id: uuid.UUID
    title: str = Field(..., max_length=300)
    description: str | None = None
    puzzle_ids: list[uuid.UUID] = []
    due_date: datetime | None = None
    max_attempts: int | None = 3


class AssignmentCreate(AssignmentBase):
    pass


class AssignmentUpdate(BaseModel):
    title: str | None = None
    description: str | None = None
    puzzle_ids: list[uuid.UUID] | None = None
    due_date: datetime | None = None
    max_attempts: int | None = None


class ClassInfo(BaseModel):
    id: uuid.UUID
    name: str

    model_config = ConfigDict(from_attributes=True)

class AssignmentRead(AssignmentBase):
    id: uuid.UUID
    teacher_id: uuid.UUID
    created_at: datetime | None = None
    updated_at: datetime | None = None
    class_: ClassInfo | None = None

    model_config = ConfigDict(from_attributes=True)


class AssignmentSubmissionRead(BaseModel):
    id: uuid.UUID
    assignment_id: uuid.UUID
    student_id: uuid.UUID
    attempt_no: int = 1
    version: int = 1
    status: str
    submitted_at: datetime | None = None
    total_points: int = 0
    completed_puzzles: int = 0
    reopened_at: datetime | None = None
    reopened_by: uuid.UUID | None = None
    reopen_reason: str | None = None
    teacher_feedback: str | None = None
    graded_at: datetime | None = None
    graded_by: uuid.UUID | None = None
    teacher_adjustment: int = 0
    created_at: datetime | None = None
    updated_at: datetime | None = None
    can_grade: bool | None = None
    previous_submission: dict | None = None

    model_config = ConfigDict(from_attributes=True)


class AssignmentReopenRequest(BaseModel):
    student_id: uuid.UUID
    reason: str = Field(..., min_length=1, max_length=1000)


class AssignmentGradeRequest(BaseModel):
    student_id: uuid.UUID | None = None
    teacher_feedback: str | None = None
    teacher_adjustment: int = 0
    expected_version: int | None = None
    attempt_no: int | None = None


