from typing import List, Optional
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.models.payment import FeePlan
from app.schemas.fee_plan import FeePlanCreate, FeePlanUpdate


class FeePlanService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_all_by_center(self, center_id: UUID) -> List[FeePlan]:
        result = await self.db.execute(select(FeePlan).where(FeePlan.center_id == center_id))
        return list(result.scalars().all())

    async def get_by_id(self, fee_plan_id: UUID) -> Optional[FeePlan]:
        result = await self.db.execute(select(FeePlan).where(FeePlan.id == fee_plan_id))
        return result.scalars().first()

    async def create(self, fee_plan_in: FeePlanCreate) -> FeePlan:
        fee_plan = FeePlan(**fee_plan_in.model_dump())
        self.db.add(fee_plan)
        await self.db.commit()
        await self.db.refresh(fee_plan)
        return fee_plan

    async def update(self, fee_plan_id: UUID, fee_plan_in: FeePlanUpdate) -> Optional[FeePlan]:
        fee_plan = await self.get_by_id(fee_plan_id)
        if not fee_plan:
            return None

        update_data = fee_plan_in.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(fee_plan, field, value)

        await self.db.commit()
        await self.db.refresh(fee_plan)
        return fee_plan

    async def delete(self, fee_plan_id: UUID) -> bool:
        fee_plan = await self.get_by_id(fee_plan_id)
        if not fee_plan:
            return False
            
        await self.db.delete(fee_plan)
        await self.db.commit()
        return True
