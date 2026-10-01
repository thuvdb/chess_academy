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


class AssignmentRead(AssignmentBase):
    id: uuid.UUID
    teacher_id: uuid.UUID
    created_at: datetime | None = None
    updated_at: datetime | None = None

    model_config = ConfigDict(from_attributes=True)
