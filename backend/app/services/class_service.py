"""
Service layer for Classes & Enrollment.
"""
import uuid
from sqlalchemy import select, func, delete
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.class_ import Class, ClassEnrollment
from app.models.user import User
from app.models.base import EnrollmentStatus
from app.schemas.class_ import ClassCreate, ClassUpdate


# ==================== Class CRUD ====================

async def get_classes(
    db: AsyncSession,
    skip: int = 0,
    limit: int = 50,
    level: str | None = None,
    search: str | None = None,
    teacher_id: uuid.UUID | None = None,
    is_active: bool | None = None,
):
    """List classes with optional filters."""
    query = select(Class).offset(skip).limit(limit)

    if level:
        query = query.where(Class.level == level)
    if search:
        query = query.where(Class.name.ilike(f"%{search}%"))
    if teacher_id:
        query = query.where(Class.teacher_id == teacher_id)
    if is_active is not None:
        query = query.where(Class.is_active == is_active)

    query = query.order_by(Class.created_at.desc())
    result = await db.execute(query)
    classes = result.scalars().all()

    # Enrich with current_students count and teacher_name
    enriched = []
    for c in classes:
        count_q = select(func.count()).select_from(ClassEnrollment).where(
            ClassEnrollment.class_id == c.id,
            ClassEnrollment.status == EnrollmentStatus.ACTIVE.value,
        )
        count_result = await db.execute(count_q)
        current_students = count_result.scalar() or 0

        teacher_name = c.teacher.full_name if c.teacher else None

        enriched.append({
            **{col.name: getattr(c, col.name) for col in c.__table__.columns},
            "current_students": current_students,
            "teacher_name": teacher_name,
        })

    return enriched


async def get_class_by_id(db: AsyncSession, class_id: uuid.UUID):
    """Get a single class by ID."""
    result = await db.execute(
        select(Class).where(Class.id == class_id)
    )
    cls = result.scalar_one_or_none()
    if not cls:
        return None

    count_q = select(func.count()).select_from(ClassEnrollment).where(
        ClassEnrollment.class_id == cls.id,
        ClassEnrollment.status == EnrollmentStatus.ACTIVE.value,
    )
    count_result = await db.execute(count_q)
    current_students = count_result.scalar() or 0
    teacher_name = cls.teacher.full_name if cls.teacher else None

    return {
        **{col.name: getattr(cls, col.name) for col in cls.__table__.columns},
        "current_students": current_students,
        "teacher_name": teacher_name,
    }


async def create_class(db: AsyncSession, data: ClassCreate):
    """Create a new class."""
    new_class = Class(**data.model_dump())
    db.add(new_class)
    await db.flush()
    await db.refresh(new_class)
    return await get_class_by_id(db, new_class.id)


async def update_class(db: AsyncSession, class_id: uuid.UUID, data: ClassUpdate):
    """Update an existing class."""
    result = await db.execute(select(Class).where(Class.id == class_id))
    cls = result.scalar_one_or_none()
    if not cls:
        return None

    update_data = data.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(cls, key, value)

    await db.flush()
    await db.refresh(cls)
    return await get_class_by_id(db, cls.id)


async def delete_class(db: AsyncSession, class_id: uuid.UUID) -> tuple[bool, str]:
    """Hard-delete a class. Fails if there are active enrollments."""
    result = await db.execute(select(Class).where(Class.id == class_id))
    cls = result.scalar_one_or_none()
    if not cls:
        return False, "Class not found"

    # check active students
    count_q = select(func.count()).select_from(ClassEnrollment).where(
        ClassEnrollment.class_id == class_id,
        ClassEnrollment.status == EnrollmentStatus.ACTIVE.value,
    )
    count_result = await db.execute(count_q)
    current_students = count_result.scalar() or 0
    if current_students > 0:
        return False, "Cannot delete class with active students. Please unenroll them first."

    # Delete all enrollments (inactive ones)
    await db.execute(delete(ClassEnrollment).where(ClassEnrollment.class_id == class_id))
    
    # Delete the class
    await db.execute(delete(Class).where(Class.id == class_id))
    await db.flush()
    return True, ""


# ==================== Enrollment CRUD ====================

async def get_class_enrollments(
    db: AsyncSession, class_id: uuid.UUID
):
    """List all enrollments for a class."""
    query = (
        select(ClassEnrollment)
        .where(ClassEnrollment.class_id == class_id)
        .order_by(ClassEnrollment.enrolled_at.desc())
    )
    result = await db.execute(query)
    enrollments = result.scalars().all()

    enriched = []
    for e in enrollments:
        enriched.append({
            "id": e.id,
            "class_id": e.class_id,
            "student_id": e.student_id,
            "enrolled_at": e.enrolled_at,
            "status": e.status,
            "student_name": e.student.full_name if e.student else None,
            "student_email": e.student.email if e.student else None,
        })
    return enriched


async def enroll_student(
    db: AsyncSession, class_id: uuid.UUID, student_id: uuid.UUID
):
    """Enroll a student into a class."""
    # Check class exists
    cls_result = await db.execute(select(Class).where(Class.id == class_id))
    cls = cls_result.scalar_one_or_none()
    if not cls:
        return None, "Class not found"

    # Check student exists and is a student
    stu_result = await db.execute(select(User).where(User.id == student_id))
    student = stu_result.scalar_one_or_none()
    if not student:
        return None, "Student not found"

    # Check if already enrolled (active)
    existing = await db.execute(
        select(ClassEnrollment).where(
            ClassEnrollment.class_id == class_id,
            ClassEnrollment.student_id == student_id,
            ClassEnrollment.status == EnrollmentStatus.ACTIVE.value,
        )
    )
    if existing.scalar_one_or_none():
        return None, "Student already enrolled in this class"

    # Check max_students
    count_q = select(func.count()).select_from(ClassEnrollment).where(
        ClassEnrollment.class_id == class_id,
        ClassEnrollment.status == EnrollmentStatus.ACTIVE.value,
    )
    count_result = await db.execute(count_q)
    current = count_result.scalar() or 0
    if current >= cls.max_students:
        return None, "Class is full"

    enrollment = ClassEnrollment(
        class_id=class_id,
        student_id=student_id,
        status=EnrollmentStatus.ACTIVE.value,
    )
    db.add(enrollment)
    await db.flush()
    await db.refresh(enrollment)

    return {
        "id": enrollment.id,
        "class_id": enrollment.class_id,
        "student_id": enrollment.student_id,
        "enrolled_at": enrollment.enrolled_at,
        "status": enrollment.status,
        "student_name": student.full_name,
        "student_email": student.email,
    }, None


async def unenroll_student(
    db: AsyncSession, class_id: uuid.UUID, student_id: uuid.UUID
) -> bool:
    """Remove a student from a class (set status to inactive)."""
    result = await db.execute(
        select(ClassEnrollment).where(
            ClassEnrollment.class_id == class_id,
            ClassEnrollment.student_id == student_id,
            ClassEnrollment.status == EnrollmentStatus.ACTIVE.value,
        )
    )
    enrollment = result.scalar_one_or_none()
    if not enrollment:
        return False
    enrollment.status = EnrollmentStatus.INACTIVE.value
    await db.flush()
    return True
