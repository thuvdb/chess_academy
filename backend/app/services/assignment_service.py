"""
Assignment Service — Sprint 4
Handles Assignment CRUD and class assignment logic.
"""

import logging
import uuid
from typing import Optional

from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.assignment import Assignment
from app.models.class_ import ClassEnrollment
from app.schemas.assignment import AssignmentCreate, AssignmentUpdate

logger = logging.getLogger(__name__)


async def create_assignment(
    db: AsyncSession,
    teacher_id: uuid.UUID,
    data: AssignmentCreate,
) -> Assignment:
    assignment = Assignment(
        class_id=data.class_id,
        teacher_id=teacher_id,
        title=data.title,
        description=data.description,
        puzzle_ids=data.puzzle_ids,
        due_date=data.due_date,
        max_attempts=data.max_attempts,
    )
    db.add(assignment)
    await db.flush()
    await db.refresh(assignment)
    return assignment


async def get_assignment(
    db: AsyncSession,
    assignment_id: uuid.UUID,
) -> Assignment | None:
    stmt = (
        select(Assignment)
        .options(selectinload(Assignment.class_), selectinload(Assignment.teacher))
        .where(Assignment.id == assignment_id)
    )
    result = await db.execute(stmt)
    return result.scalar_one_or_none()


async def list_assignments(
    db: AsyncSession,
    class_id: Optional[uuid.UUID] = None,
    teacher_id: Optional[uuid.UUID] = None,
    student_id: Optional[uuid.UUID] = None,
    skip: int = 0,
    limit: int = 50,
) -> list[Assignment]:
    stmt = select(Assignment).options(
        selectinload(Assignment.class_), selectinload(Assignment.teacher)
    )

    if class_id:
        stmt = stmt.where(Assignment.class_id == class_id)
    if teacher_id:
        stmt = stmt.where(Assignment.teacher_id == teacher_id)
    if student_id:
        stmt = stmt.join(ClassEnrollment, ClassEnrollment.class_id == Assignment.class_id).where(
            ClassEnrollment.student_id == student_id
        )

    stmt = stmt.order_by(desc(Assignment.created_at)).offset(skip).limit(limit)
    result = await db.execute(stmt)
    return list(result.scalars().all())


async def update_assignment(
    db: AsyncSession,
    assignment: Assignment,
    data: AssignmentUpdate,
) -> Assignment:
    if data.title is not None:
        assignment.title = data.title
    if data.description is not None:
        assignment.description = data.description
    if data.puzzle_ids is not None:
        assignment.puzzle_ids = data.puzzle_ids
    if data.due_date is not None:
        assignment.due_date = data.due_date
    if data.max_attempts is not None:
        assignment.max_attempts = data.max_attempts

    await db.flush()
    await db.refresh(assignment)
    return assignment


async def delete_assignment(
    db: AsyncSession,
    assignment: Assignment,
) -> None:
    await db.delete(assignment)
    await db.flush()
