from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class FeePlanBase(BaseModel):
    name: str
    amount: float
    currency: str = "VND"
    billing_cycle: str = "monthly"
    description: Optional[str] = None
    is_active: bool = True


class FeePlanCreate(FeePlanBase):
    center_id: UUID


class FeePlanUpdate(BaseModel):
    name: Optional[str] = None
    amount: Optional[float] = None
    currency: Optional[str] = None
    billing_cycle: Optional[str] = None
    description: Optional[str] = None
    is_active: Optional[bool] = None


class FeePlanResponse(FeePlanBase):
    id: UUID
    center_id: UUID
    created_at: datetime
    updated_at: Optional[datetime]

    model_config = ConfigDict(from_attributes=True)
