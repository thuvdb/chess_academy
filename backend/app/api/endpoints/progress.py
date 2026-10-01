"""
Progress & Practice API — Sprint 4
Endpoints for submitting attempts, auto-grading, and manual grading.
"""

import uuid
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.deps import get_current_user
from app.core.database import get_db
from app.models.progress import StudentAttempt, StudentProgress
from app.models.user import User
from app.schemas.progress import (
    StudentAttemptCreate,
    StudentAttemptRead,
    StudentProgressRead,
    TeacherGradingRequest,
)
from app.services import progress_service

router = APIRouter()


@router.post("/attempt", response_model=StudentAttemptRead, status_code=status.HTTP_201_CREATED)
async def submit_attempt(
    attempt_in: StudentAttemptCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Submit a puzzle solution attempt.
    Automatically evaluates the move sequence and performs Auto-AI grading.
    """
    try:
        progress, attempt = await progress_service.submit_attempt(
            db=db,
            student_id=current_user.id,
            attempt_in=attempt_in,
        )
        await db.commit()
        return attempt
    except ValueError as exc:
        await db.rollback()
        raise HTTPException(status_code=400, detail=str(exc))


@router.get("/{progress_id}", response_model=StudentProgressRead)
async def get_progress(
    progress_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    stmt = (
        select(StudentProgress)
        .options(selectinload(StudentProgress.attempt_details))
        .where(StudentProgress.id == progress_id)
    )
    res = await db.execute(stmt)
    progress = res.scalar_one_or_none()
    if not progress:
        raise HTTPException(status_code=404, detail="Progress record not found")
    return progress


@router.put("/{progress_id}/grade", response_model=StudentProgressRead)
async def grade_attempt(
    progress_id: uuid.UUID,
    data: TeacherGradingRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Teacher manual grading of a student progress record."""
    if current_user.role not in ("super_admin", "admin", "teacher"):
        raise HTTPException(status_code=403, detail="Only teachers can grade attempts")

    try:
        updated = await progress_service.grade_manually(
            db=db,
            progress_id=progress_id,
            teacher_id=current_user.id,
            grade_data=data,
        )
        await db.commit()
        return updated
    except ValueError as exc:
        await db.rollback()
        raise HTTPException(status_code=400, detail=str(exc))


@router.get("/student/my-progress", response_model=list[StudentProgressRead])
async def get_my_progress(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    stmt = (
        select(StudentProgress)
        .where(StudentProgress.student_id == current_user.id)
        .order_by(desc(StudentProgress.updated_at))
    )
    res = await db.execute(stmt)
    return list(res.scalars().all())
