"""
Assignments API — Sprint 4
Endpoints for managing homework and class assignments.
"""

import uuid
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.core.database import get_db
from app.models.user import User
from app.schemas.assignment import (
    AssignmentCreate,
    AssignmentRead,
    AssignmentUpdate,
)
from app.services import assignment_service

router = APIRouter()


@router.get("", response_model=list[AssignmentRead])
async def list_assignments(
    class_id: Optional[uuid.UUID] = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    teacher_id = None
    if current_user.role == "teacher":
        teacher_id = current_user.id

    return await assignment_service.list_assignments(
        db=db,
        class_id=class_id,
        teacher_id=teacher_id,
        skip=skip,
        limit=limit,
    )


@router.get("/{assignment_id}", response_model=AssignmentRead)
async def get_assignment(
    assignment_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    assignment = await assignment_service.get_assignment(db, assignment_id)
    if not assignment:
        raise HTTPException(status_code=404, detail="Assignment not found")
    return assignment


@router.post("", response_model=AssignmentRead, status_code=status.HTTP_201_CREATED)
async def create_assignment(
    data: AssignmentCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if current_user.role not in ("super_admin", "admin", "teacher"):
        raise HTTPException(status_code=403, detail="Only teachers can create assignments")

    assignment = await assignment_service.create_assignment(
        db=db,
        teacher_id=current_user.id,
        data=data,
    )
    await db.commit()
    return assignment


@router.put("/{assignment_id}", response_model=AssignmentRead)
async def update_assignment(
    assignment_id: uuid.UUID,
    data: AssignmentUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if current_user.role not in ("super_admin", "admin", "teacher"):
        raise HTTPException(status_code=403, detail="Only teachers can update assignments")

    assignment = await assignment_service.get_assignment(db, assignment_id)
    if not assignment:
        raise HTTPException(status_code=404, detail="Assignment not found")

    updated = await assignment_service.update_assignment(db, assignment, data)
    await db.commit()
    return updated


@router.delete("/{assignment_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_assignment(
    assignment_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if current_user.role not in ("super_admin", "admin", "teacher"):
        raise HTTPException(status_code=403, detail="Only teachers can delete assignments")

    assignment = await assignment_service.get_assignment(db, assignment_id)
    if not assignment:
        raise HTTPException(status_code=404, detail="Assignment not found")

    await assignment_service.delete_assignment(db, assignment)
    await db.commit()
