"""
API endpoints for Classes & Enrollment management.
"""
import uuid
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.api.deps import get_current_user, require_role
from app.api.access import ensure_class_access, ensure_class_ownership
from app.models.user import User
from app.schemas.class_ import (
    ClassCreate, ClassUpdate, ClassRead,
    EnrollmentCreate, EnrollmentRead,
    ClassScheduleRead,
)
from app.services import class_service

router = APIRouter()

# Roles that can see student emails in the roster (F1 — CAMS-0014 decision 1)
_EMAIL_VISIBLE_ROLES = {"super_admin", "admin", "teacher"}


# ==================== Class Endpoints ====================

@router.get("/", response_model=list[ClassRead])
async def list_classes(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    level: str | None = None,
    search: str | None = None,
    teacher_id: uuid.UUID | None = None,
    student_id: uuid.UUID | None = None,
    is_active: bool | None = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List classes. Non-super_admin callers see only their own center's classes (F2)."""
    # CAMS-0014 F2: scope to caller's center unless super_admin
    center_filter = None if current_user.role == "super_admin" else current_user.center_id

    # If student requests a specific student_id, enforce it's themselves
    if student_id and current_user.role == "student" and student_id != current_user.id:
        raise HTTPException(status_code=403, detail="Students can only filter by their own student_id")

    return await class_service.get_classes(
        db, skip=skip, limit=limit,
        level=level, search=search,
        teacher_id=teacher_id, is_active=is_active,
        center_id=center_filter,
        current_user_id=current_user.id,
        student_id=student_id,
    )


@router.get("/{class_id}", response_model=ClassRead)
async def get_class(
    class_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get a single class by ID. Returns 404 if caller is from another center (F2)."""
    cls = await class_service.get_class_by_id(db, class_id)
    if not cls:
        raise HTTPException(status_code=404, detail="Class not found")
    # CAMS-0014 F2: center-scope check (raises 404 if wrong center)
    ensure_class_access(cls, current_user)
    return cls


@router.post("/", response_model=ClassRead, status_code=status.HTTP_201_CREATED)
async def create_class(
    data: ClassCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(["admin", "super_admin", "teacher"])),
):
    """Create a new class. Admin/teacher can only create within their own center."""
    # Bind center_id to caller's center when not super_admin
    if current_user.role != "super_admin":
        data.center_id = current_user.center_id
    # Teacher automatically becomes class owner
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
    """Update a class. Teacher can only update their own classes within their center."""
    existing = await class_service.get_class_by_id(db, class_id)
    if not existing:
        raise HTTPException(status_code=404, detail="Class not found")
    # CAMS-0014: ownership + center check (admin: same center; teacher: owner + same center)
    ensure_class_ownership(existing, current_user)

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
    """Hard-delete a class. Admin can only delete within own center (F2)."""
    existing = await class_service.get_class_by_id(db, class_id)
    if not existing:
        raise HTTPException(status_code=404, detail="Class not found")
    # CAMS-0014: admin scoped to own center
    ensure_class_ownership(existing, current_user)

    success, error = await class_service.delete_class(db, class_id)
    if not success:
        if error == "Class not found":
            raise HTTPException(status_code=404, detail=error)
        raise HTTPException(status_code=400, detail=error)
    await db.commit()


# ==================== Enrollment Endpoints ====================

@router.get("/{class_id}/students", response_model=list[EnrollmentRead])
async def list_class_students(
    class_id: uuid.UUID,
    status: str | None = Query(None, description="Filter by enrollment status (e.g. 'active', 'inactive')"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List students enrolled in a class.

    - Any authenticated user in the same center may see the roster (names only).
    - Email is visible only to admin/super_admin or the teacher assigned to the class (F1).
    - Users from other centers receive 404 (F2).
    - Students and parents can only see active classmates.
    """
    cls = await class_service.get_class_by_id(db, class_id)
    if not cls:
        raise HTTPException(status_code=404, detail="Class not found")
    # CAMS-0014 F2: center-scope check
    ensure_class_access(cls, current_user)

    # CAMS-0014 F1: only admin/super_admin and class teacher may see student emails
    is_class_teacher = (
        current_user.role == "teacher"
        and cls.get("teacher_id") == current_user.id
    )
    include_email = (
        current_user.role in {"super_admin", "admin"} or is_class_teacher
    )

    # Students and parents can only view active classmates
    effective_status = status
    if current_user.role in {"student", "parent"}:
        effective_status = "active"

    return await class_service.get_class_enrollments(
        db, class_id, include_email=include_email, status=effective_status
    )


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
    """Add a student to a class. Teacher can only enroll in their own class (F3)."""
    cls = await class_service.get_class_by_id(db, class_id)
    if not cls:
        raise HTTPException(status_code=404, detail="Class not found")
    # CAMS-0014 F3: ownership check — teacher must own this class
    ensure_class_ownership(cls, current_user)

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
    """Remove a student from a class. Teacher can only unenroll from their own class (F3)."""
    cls = await class_service.get_class_by_id(db, class_id)
    if not cls:
        raise HTTPException(status_code=404, detail="Class not found")
    # CAMS-0014 F3: ownership check
    ensure_class_ownership(cls, current_user)

    success = await class_service.unenroll_student(db, class_id, student_id)
    if not success:
        raise HTTPException(status_code=404, detail="Enrollment not found")
    await db.commit()


# ==================== Schedule Endpoints ====================

@router.get("/{class_id}/schedule", response_model=ClassScheduleRead)
async def get_class_schedule(
    class_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get the weekly schedule for a class. Returns 404 for other-center classes (F2)."""
    cls = await class_service.get_class_by_id(db, class_id)
    if not cls:
        raise HTTPException(status_code=404, detail="Class not found")
    # CAMS-0014 F2: center-scope check before returning schedule
    ensure_class_access(cls, current_user)

    schedule = await class_service.get_class_schedule(db, class_id)
    if not schedule:
        raise HTTPException(status_code=404, detail="Class not found")
    return schedule
