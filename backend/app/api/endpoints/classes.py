"""
API endpoints for Classes & Enrollment management.
"""
import uuid
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.api.deps import get_current_user, require_role
from app.models.user import User
from app.schemas.class_ import (
    ClassCreate, ClassUpdate, ClassRead,
    EnrollmentCreate, EnrollmentRead,
)
from app.services import class_service

router = APIRouter()


# ==================== Class Endpoints ====================

@router.get("/", response_model=list[ClassRead])
async def list_classes(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    level: str | None = None,
    search: str | None = None,
    teacher_id: uuid.UUID | None = None,
    is_active: bool | None = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List all classes with optional filters."""
    return await class_service.get_classes(
        db, skip=skip, limit=limit,
        level=level, search=search,
        teacher_id=teacher_id, is_active=is_active,
    )


@router.get("/{class_id}", response_model=ClassRead)
async def get_class(
    class_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get a single class by ID."""
    cls = await class_service.get_class_by_id(db, class_id)
    if not cls:
        raise HTTPException(status_code=404, detail="Class not found")
    return cls


@router.post("/", response_model=ClassRead, status_code=status.HTTP_201_CREATED)
async def create_class(
    data: ClassCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(["admin", "super_admin", "teacher"])),
):
    """Create a new class. Only admin or teacher can create."""
    if current_user.role == "teacher":
        data.teacher_id = current_user.id
    result = await class_service.create_class(db, data)
    await db.commit()
    return result


@router.put("/{class_id}", response_model=ClassRead)
async def update_class(
    class_id: uuid.UUID,
    data: ClassUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(["admin", "super_admin", "teacher"])),
):
    """Update a class. Teacher can only update their own classes."""
    if current_user.role == "teacher":
        existing = await class_service.get_class_by_id(db, class_id)
        if not existing or existing["teacher_id"] != current_user.id:
            raise HTTPException(status_code=403, detail="You can only edit your own classes")

    result = await class_service.update_class(db, class_id, data)
    if not result:
        raise HTTPException(status_code=404, detail="Class not found")
    await db.commit()
    return result


@router.delete("/{class_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_class(
    class_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(["admin", "super_admin"])),
):
    """Soft-delete a class. Admin only."""
    success = await class_service.delete_class(db, class_id)
    if not success:
        raise HTTPException(status_code=404, detail="Class not found")
    await db.commit()


# ==================== Enrollment Endpoints ====================

@router.get("/{class_id}/students", response_model=list[EnrollmentRead])
async def list_class_students(
    class_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List all students enrolled in a class."""
    return await class_service.get_class_enrollments(db, class_id)


@router.post(
    "/{class_id}/students",
    response_model=EnrollmentRead,
    status_code=status.HTTP_201_CREATED,
)
async def enroll_student(
    class_id: uuid.UUID,
    data: EnrollmentCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(["admin", "super_admin", "teacher"])),
):
    """Add a student to a class."""
    enrollment, error = await class_service.enroll_student(db, class_id, data.student_id)
    if error:
        raise HTTPException(status_code=400, detail=error)
    await db.commit()
    return enrollment


@router.delete(
    "/{class_id}/students/{student_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def unenroll_student(
    class_id: uuid.UUID,
    student_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(["admin", "super_admin", "teacher"])),
):
    """Remove a student from a class."""
    success = await class_service.unenroll_student(db, class_id, student_id)
    if not success:
        raise HTTPException(status_code=404, detail="Enrollment not found")
    await db.commit()
