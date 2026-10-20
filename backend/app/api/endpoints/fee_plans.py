from typing import List
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.api.deps import get_current_user, require_role
from app.schemas.fee_plan import FeePlanCreate, FeePlanUpdate, FeePlanResponse
from app.services.fee_plan_service import FeePlanService
from app.models.user import User

router = APIRouter()


@router.post("", response_model=FeePlanResponse, status_code=status.HTTP_201_CREATED)
@router.post("/", response_model=FeePlanResponse, status_code=status.HTTP_201_CREATED, include_in_schema=False)
async def create_fee_plan(
    fee_plan_in: FeePlanCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(["admin", "center_admin"]))
):
    service = FeePlanService(db)
    # Basic permission check: user's center must match fee_plan center
    if current_user.center_id != fee_plan_in.center_id:
        raise HTTPException(status_code=403, detail="Not enough permissions")
    return await service.create(fee_plan_in)


@router.get("/center/{center_id}", response_model=List[FeePlanResponse])
async def get_fee_plans(
    center_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    service = FeePlanService(db)
    if current_user.center_id != center_id and current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Not enough permissions")
    return await service.get_all_by_center(center_id)


@router.get("/{fee_plan_id}", response_model=FeePlanResponse)
async def get_fee_plan(
    fee_plan_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    service = FeePlanService(db)
    fee_plan = await service.get_by_id(fee_plan_id)
    if not fee_plan:
        raise HTTPException(status_code=404, detail="Fee plan not found")
    if fee_plan.center_id != current_user.center_id and current_user.role != "admin":
         raise HTTPException(status_code=403, detail="Not enough permissions")
    return fee_plan


@router.put("/{fee_plan_id}", response_model=FeePlanResponse)
async def update_fee_plan(
    fee_plan_id: UUID,
    fee_plan_in: FeePlanUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(["admin", "center_admin"]))
):
    service = FeePlanService(db)
    fee_plan = await service.get_by_id(fee_plan_id)
    if not fee_plan:
        raise HTTPException(status_code=404, detail="Fee plan not found")
    if fee_plan.center_id != current_user.center_id:
        raise HTTPException(status_code=403, detail="Not enough permissions")
    return await service.update(fee_plan_id, fee_plan_in)


@router.delete("/{fee_plan_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_fee_plan(
    fee_plan_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(["admin", "center_admin"]))
):
    service = FeePlanService(db)
    fee_plan = await service.get_by_id(fee_plan_id)
    if not fee_plan:
        raise HTTPException(status_code=404, detail="Fee plan not found")
    if fee_plan.center_id != current_user.center_id:
        raise HTTPException(status_code=403, detail="Not enough permissions")
    await service.delete(fee_plan_id)
