"""
Centers API Endpoints — CAMS-0058
Enables super_admin to manage centers (CRUD), and center_admin to update their own center details.
"""

import uuid
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import delete, func, or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.core.database import get_db
from app.core.permissions import Role, assert_same_center, is_super_admin, require_roles
from app.models.center import Branch, Center
from app.models.class_ import Class
from app.models.payment import FeePlan, Invoice, Payment
from app.models.puzzle import Puzzle
from app.models.scan import ScanJob, ScanResult
from app.models.tournament import Tournament
from app.models.user import User
from app.schemas.center import (
    CenterCreate,
    CenterRead,
    CenterUpdate,
)

router = APIRouter()


async def _enrich_center(db: AsyncSession, center: Center) -> CenterRead:
    branches_count = (
        await db.scalar(
            select(func.count(Branch.id)).where(Branch.center_id == center.id)
        )
        or 0
    )
    members_count = (
        await db.scalar(
            select(func.count(User.id)).where(User.center_id == center.id)
        )
        or 0
    )
    classes_count = (
        await db.scalar(
            select(func.count(Class.id)).where(Class.center_id == center.id)
        )
        or 0
    )

    return CenterRead(
        id=center.id,
        name=center.name,
        address=center.address,
        logo_url=center.logo_url,
        phone=center.phone,
        email=center.email,
        facebook_page_url=center.facebook_page_url,
        subscription_plan=center.subscription_plan,
        created_at=center.created_at,
        updated_at=center.updated_at,
        branches_count=branches_count,
        members_count=members_count,
        classes_count=classes_count,
    )


@router.get("", response_model=List[CenterRead])
async def list_centers(
    search: Optional[str] = Query(None),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List centers available to caller with member and class counts."""
    query = select(Center)

    if is_super_admin(current_user):
        if search:
            search_pattern = f"%{search.strip()}%"
            query = query.where(
                or_(
                    Center.name.ilike(search_pattern),
                    Center.address.ilike(search_pattern),
                    Center.phone.ilike(search_pattern),
                    Center.email.ilike(search_pattern),
                )
            )
        query = query.order_by(Center.created_at.desc(), Center.name.asc())
    elif current_user.center_id:
        query = query.where(Center.id == current_user.center_id)
    else:
        return []

    result = await db.execute(query)
    centers = result.scalars().all()

    enriched_list = []
    for c in centers:
        enriched = await _enrich_center(db, c)
        enriched_list.append(enriched)

    return enriched_list


@router.get("/{center_id}", response_model=CenterRead)
async def get_center(
    center_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get single center detail by ID."""
    result = await db.execute(select(Center).where(Center.id == center_id))
    center = result.scalars().first()

    if not center:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Trung tâm không tồn tại"
        )

    if not is_super_admin(current_user) and current_user.center_id != center_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Trung tâm không tồn tại"
        )

    return await _enrich_center(db, center)


@router.post("", response_model=CenterRead, status_code=status.HTTP_201_CREATED)
async def create_center(
    data: CenterCreate,
    current_user: User = Depends(require_roles(Role.SUPER_ADMIN)),
    db: AsyncSession = Depends(get_db),
):
    """Create a new center (Super Admin only)."""
    center_id = uuid.uuid4()
    center = Center(
        id=center_id,
        name=data.name.strip(),
        address=data.address.strip() if data.address else None,
        logo_url=data.logo_url.strip() if data.logo_url else None,
        phone=data.phone.strip() if data.phone else None,
        email=data.email.strip().lower() if data.email else None,
        facebook_page_url=data.facebook_page_url.strip() if data.facebook_page_url else None,
        subscription_plan=data.subscription_plan or "free",
    )
    db.add(center)
    await db.flush()

    # Automatically provision default primary branch
    default_branch = Branch(
        id=uuid.uuid4(),
        center_id=center.id,
        name="Cơ sở chính",
        address=center.address,
        phone=center.phone,
        is_active=True,
    )
    db.add(default_branch)
    await db.commit()
    await db.refresh(center)

    return await _enrich_center(db, center)


@router.put("/{center_id}", response_model=CenterRead)
async def update_center(
    center_id: uuid.UUID,
    data: CenterUpdate,
    current_user: User = Depends(require_roles(Role.SUPER_ADMIN, Role.CENTER_ADMIN)),
    db: AsyncSession = Depends(get_db),
):
    """Update center details."""
    result = await db.execute(select(Center).where(Center.id == center_id))
    center = result.scalars().first()

    if not center:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Trung tâm không tồn tại"
        )

    if not is_super_admin(current_user):
        assert_same_center(current_user, center_id, detail="Trung tâm không tồn tại")

    update_dict = data.model_dump(exclude_unset=True)

    # Center Admin cannot change subscription plan
    if not is_super_admin(current_user) and "subscription_plan" in update_dict:
        update_dict.pop("subscription_plan")

    if "name" in update_dict and update_dict["name"]:
        update_dict["name"] = update_dict["name"].strip()
    if "email" in update_dict and update_dict["email"]:
        update_dict["email"] = update_dict["email"].strip().lower()

    for field, value in update_dict.items():
        setattr(center, field, value)

    await db.commit()
    await db.refresh(center)
    return await _enrich_center(db, center)


@router.delete("/{center_id}", status_code=status.HTTP_200_OK)
async def delete_center(
    center_id: uuid.UUID,
    current_user: User = Depends(require_roles(Role.SUPER_ADMIN)),
    db: AsyncSession = Depends(get_db),
):
    """Delete a center if it has no active members or classes."""
    result = await db.execute(select(Center).where(Center.id == center_id))
    center = result.scalars().first()

    if not center:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Trung tâm không tồn tại"
        )

    members_count = await db.scalar(
        select(func.count(User.id)).where(User.center_id == center_id)
    )
    classes_count = await db.scalar(
        select(func.count(Class.id)).where(Class.center_id == center_id)
    )

    if (members_count or 0) > 0 or (classes_count or 0) > 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Không thể xóa trung tâm đang có {members_count} thành viên và {classes_count} lớp học.",
        )

    # Detach optional references and delete center-specific records
    await db.execute(update(Puzzle).where(Puzzle.center_id == center_id).values(center_id=None))
    await db.execute(update(Tournament).where(Tournament.center_id == center_id).values(center_id=None))
    job_ids = (await db.scalars(select(ScanJob.id).where(ScanJob.center_id == center_id))).all()
    if job_ids:
        await db.execute(delete(ScanResult).where(ScanResult.job_id.in_(job_ids)))
    await db.execute(delete(ScanJob).where(ScanJob.center_id == center_id))
    inv_ids = (await db.scalars(select(Invoice.id).where(Invoice.center_id == center_id))).all()
    if inv_ids:
        await db.execute(delete(Payment).where(Payment.invoice_id.in_(inv_ids)))
    await db.execute(delete(Invoice).where(Invoice.center_id == center_id))
    await db.execute(delete(FeePlan).where(FeePlan.center_id == center_id))
    await db.execute(delete(Branch).where(Branch.center_id == center_id))
    await db.delete(center)
    await db.commit()

    return {"message": "Đã xóa trung tâm thành công", "id": str(center_id)}

