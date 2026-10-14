import os
import shutil
import uuid
from typing import List

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile, status
from sqlalchemy import delete, insert, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.deps import get_current_user
from app.core.database import get_db
from app.core.permissions import (
    Role,
    assert_same_center,
    is_admin,
    is_center_admin,
    is_super_admin,
    require_roles,
    scope_query_to_center,
)
from app.core.security import hash_password
from app.models.user import User, parent_student
from app.models.center import Center
from app.schemas.user import (
    ParentStudentLinkResponse,
    UserAdminCreate,
    UserAdminUpdate,
    UserDetailRead,
    UserRead,
    UserUpdate,
)

router = APIRouter()


@router.put("/me", response_model=UserRead)
async def update_me(
    user_in: UserUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    update_data = user_in.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(current_user, field, value)

    try:
        await db.commit()
        await db.refresh(current_user)
    except IntegrityError:
        await db.rollback()
        raise HTTPException(
            status_code=400,
            detail="Username already taken or invalid data.",
        )

    return current_user


@router.get("/members", response_model=List[UserRead])
async def get_members(
    skip: int = 0,
    limit: int = 100,
    search: str | None = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List members within the current user's center."""
    if current_user.role not in [
        Role.SUPER_ADMIN.value,
        Role.CENTER_ADMIN.value,
        Role.ADMIN.value,
        Role.TEACHER.value,
    ]:
        raise HTTPException(status_code=403, detail="Not enough permissions")

    query = select(User)
    query = scope_query_to_center(query, current_user, User.center_id)

    if current_user.role == Role.TEACHER.value:
        query = query.where(User.role == Role.STUDENT.value)

    if search:
        query = query.where(
            or_(
                User.full_name.ilike(f"%{search}%"),
                User.email.ilike(f"%{search}%"),
                User.username.ilike(f"%{search}%"),
            )
        )

    query = query.offset(skip).limit(limit)
    result = await db.execute(query)
    return result.scalars().all()


@router.post("", response_model=UserRead, status_code=status.HTTP_201_CREATED)
async def create_user(
    user_in: UserAdminCreate,
    current_user: User = Depends(
        require_roles(Role.SUPER_ADMIN, Role.CENTER_ADMIN, Role.ADMIN)
    ),
    db: AsyncSession = Depends(get_db),
):
    """
    Provision a new user within a center.
    - center_admin: can only create teacher, student, parent for their own center.
    - super_admin: can create any role (must supply center_id for non-super_admin).
    """
    target_role = user_in.role
    if is_center_admin(current_user):
        allowed_roles = {Role.TEACHER.value, Role.STUDENT.value, Role.PARENT.value}
        if target_role not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Center admins can only create {', '.join(sorted(allowed_roles))}",
            )
        if not current_user.center_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Your administrator account is not assigned to any center.",
            )
        target_center_id = current_user.center_id
    else:
        # super_admin
        if target_role != Role.SUPER_ADMIN.value and not user_in.center_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="center_id is required when creating non-super_admin users.",
            )
        target_center_id = user_in.center_id

    # Check for duplicate email
    existing = await db.execute(select(User).where(User.email == user_in.email))
    if existing.scalars().first():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="A user with this email already exists.",
        )

    new_user = User(
        email=user_in.email,
        password_hash=hash_password(user_in.password),
        full_name=user_in.full_name,
        role=target_role,
        center_id=target_center_id,
        phone=user_in.phone,
        date_of_birth=user_in.date_of_birth,
        is_active=True,
        elo_rating=800,
    )
    db.add(new_user)
    await db.flush()  # Flush to get new_user.id

    # If creating a parent with student_ids, link them
    if target_role == Role.PARENT.value and user_in.student_ids:
        for sid in user_in.student_ids:
            student_res = await db.execute(select(User).where(User.id == sid))
            student = student_res.scalars().first()
            if not student:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Student {sid} not found.",
                )
            if student.role != Role.STUDENT.value:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"User {sid} is not a student.",
                )
            if str(student.center_id) != str(target_center_id):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Student {sid} belongs to a different center.",
                )
            await db.execute(
                insert(parent_student).values(
                    parent_id=new_user.id,
                    student_id=student.id,
                )
            )

    await db.commit()
    await db.refresh(new_user)
    return new_user


@router.get("", response_model=List[UserRead])
async def list_users(
    skip: int = 0,
    limit: int = 100,
    search: str | None = None,
    role: str | None = None,
    center_id: uuid.UUID | None = None,
    current_user: User = Depends(
        require_roles(Role.SUPER_ADMIN, Role.CENTER_ADMIN, Role.ADMIN)
    ),
    db: AsyncSession = Depends(get_db),
):
    """
    List users with center scoping:
    - center_admin: strictly filtered to their center_id.
    - super_admin: can view all or filter by center_id query param.
    """
    query = select(User)
    query = scope_query_to_center(
        query, current_user, User.center_id, filter_center_id=center_id
    )

    if role:
        query = query.where(User.role == role)

    if search:
        query = query.where(
            or_(
                User.full_name.ilike(f"%{search}%"),
                User.email.ilike(f"%{search}%"),
                User.username.ilike(f"%{search}%"),
            )
        )

    query = query.offset(skip).limit(limit)
    result = await db.execute(query)
    return result.scalars().all()


@router.get("/parent/my-children", response_model=List[UserRead])
async def get_my_children(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Endpoint for parent users to view their linked children."""
    if current_user.role != Role.PARENT.value and not is_admin(current_user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only parents or administrators can view linked children.",
        )

    # Fetch children through relationship
    query = (
        select(User)
        .join(parent_student, parent_student.c.student_id == User.id)
        .where(parent_student.c.parent_id == current_user.id)
    )
    result = await db.execute(query)
    return result.scalars().all()


@router.get("/centers")
async def get_centers_for_user(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List centers available to current user."""
    if is_super_admin(current_user):
        stmt = select(Center).order_by(Center.name)
    elif current_user.center_id:
        stmt = select(Center).where(Center.id == current_user.center_id)
    else:
        return []
    result = await db.execute(stmt)
    centers = result.scalars().all()
    return [
        {
            "id": str(c.id),
            "name": c.name,
            "address": c.address,
            "phone": c.phone,
        }
        for c in centers
    ]


@router.get("/{user_id}", response_model=UserDetailRead)
async def get_user_detail(
    user_id: uuid.UUID,
    current_user: User = Depends(
        require_roles(Role.SUPER_ADMIN, Role.CENTER_ADMIN, Role.ADMIN, Role.TEACHER)
    ),
    db: AsyncSession = Depends(get_db),
):
    """Get detailed information for a user including linked parents/children."""
    query = (
        select(User)
        .options(selectinload(User.children), selectinload(User.parents))
        .where(User.id == user_id)
    )
    result = await db.execute(query)
    target_user = result.scalars().first()

    if not target_user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="User not found"
        )

    # Cross-center check: returns 404 if outside caller's center
    assert_same_center(current_user, target_user.center_id, detail="User not found")

    return target_user


@router.patch("/{user_id}", response_model=UserRead)
async def update_user(
    user_id: uuid.UUID,
    user_in: UserAdminUpdate,
    current_user: User = Depends(
        require_roles(Role.SUPER_ADMIN, Role.CENTER_ADMIN, Role.ADMIN)
    ),
    db: AsyncSession = Depends(get_db),
):
    """Update user information (active status, password, profile, role)."""
    result = await db.execute(select(User).where(User.id == user_id))
    target_user = result.scalars().first()

    if not target_user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="User not found"
        )

    # Cross-center check: must return 404
    assert_same_center(current_user, target_user.center_id, detail="User not found")

    if is_center_admin(current_user):
        # Cannot modify super_admin or other center_admins
        if target_user.role in {Role.SUPER_ADMIN.value, Role.CENTER_ADMIN.value, Role.ADMIN.value}:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Center admins cannot modify administrator accounts.",
            )
        # Cannot promote to super_admin or center_admin
        if user_in.role in {Role.SUPER_ADMIN.value, Role.CENTER_ADMIN.value, Role.ADMIN.value}:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Center admins cannot promote users to administrator roles.",
            )

    update_dict = user_in.model_dump(exclude_unset=True)
    if "password" in update_dict and update_dict["password"]:
        target_user.password_hash = hash_password(update_dict.pop("password"))

    for field, value in update_dict.items():
        setattr(target_user, field, value)

    await db.commit()
    await db.refresh(target_user)
    return target_user


@router.post(
    "/{parent_id}/students/{student_id}",
    response_model=ParentStudentLinkResponse,
)
async def link_parent_student(
    parent_id: uuid.UUID,
    student_id: uuid.UUID,
    current_user: User = Depends(
        require_roles(Role.SUPER_ADMIN, Role.CENTER_ADMIN, Role.ADMIN)
    ),
    db: AsyncSession = Depends(get_db),
):
    """Link a parent to a student. Both must belong to the caller's center."""
    parent_res = await db.execute(select(User).where(User.id == parent_id))
    parent = parent_res.scalars().first()
    if not parent or parent.role != Role.PARENT.value:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Parent not found"
        )

    student_res = await db.execute(select(User).where(User.id == student_id))
    student = student_res.scalars().first()
    if not student or student.role != Role.STUDENT.value:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Student not found"
        )

    # Check center boundaries
    assert_same_center(current_user, parent.center_id, detail="Parent not found")
    assert_same_center(current_user, student.center_id, detail="Student not found")

    if str(parent.center_id) != str(student.center_id):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Parent and student must belong to the same center.",
        )

    # Check existing link
    link_res = await db.execute(
        select(parent_student).where(
            parent_student.c.parent_id == parent_id,
            parent_student.c.student_id == student_id,
        )
    )
    if not link_res.first():
        await db.execute(
            insert(parent_student).values(
                parent_id=parent_id,
                student_id=student_id,
            )
        )
        await db.commit()

    return {
        "parent_id": parent_id,
        "student_id": student_id,
        "message": f"Linked parent {parent.full_name} with student {student.full_name}",
    }


@router.delete(
    "/{parent_id}/students/{student_id}",
    response_model=ParentStudentLinkResponse,
)
async def unlink_parent_student(
    parent_id: uuid.UUID,
    student_id: uuid.UUID,
    current_user: User = Depends(
        require_roles(Role.SUPER_ADMIN, Role.CENTER_ADMIN, Role.ADMIN)
    ),
    db: AsyncSession = Depends(get_db),
):
    """Unlink a parent from a student."""
    parent_res = await db.execute(select(User).where(User.id == parent_id))
    parent = parent_res.scalars().first()
    if not parent:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Parent not found"
        )

    student_res = await db.execute(select(User).where(User.id == student_id))
    student = student_res.scalars().first()
    if not student:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Student not found"
        )

    assert_same_center(current_user, parent.center_id, detail="Parent not found")
    assert_same_center(current_user, student.center_id, detail="Student not found")

    await db.execute(
        delete(parent_student).where(
            parent_student.c.parent_id == parent_id,
            parent_student.c.student_id == student_id,
        )
    )
    await db.commit()

    return {
        "parent_id": parent_id,
        "student_id": student_id,
        "message": "Unlinked successfully",
    }


@router.post("/avatar")
async def upload_avatar(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
):
    if not file.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="Invalid file type")

    ext = file.filename.split(".")[-1]
    filename = f"{current_user.id}_{uuid.uuid4().hex[:8]}.{ext}"
    os.makedirs("uploads/avatars", exist_ok=True)
    file_path = os.path.join("uploads/avatars", filename)

    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    base_url = "http://localhost:8000"
    avatar_url = f"{base_url}/static/avatars/{filename}"
    return {"avatar_url": avatar_url}

