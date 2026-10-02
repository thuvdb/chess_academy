from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from app.models.base import InvoiceStatus


class InvoiceBase(BaseModel):
    student_id: UUID
    class_id: Optional[UUID] = None
    fee_plan_id: Optional[UUID] = None
    amount: float
    currency: str = "VND"
    description: Optional[str] = None
    due_date: Optional[datetime] = None
    period_start: Optional[datetime] = None
    period_end: Optional[datetime] = None


class InvoiceCreate(InvoiceBase):
    pass


class InvoiceUpdate(BaseModel):
    status: Optional[str] = None
    due_date: Optional[datetime] = None
    description: Optional[str] = None


class InvoiceResponse(InvoiceBase):
    id: UUID
    center_id: UUID
    invoice_number: str
    status: str
    created_at: datetime
    updated_at: Optional[datetime]
    
    # Minimal nested info can be helpful
    student_name: Optional[str] = None
    class_name: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class GenerateClassInvoicesRequest(BaseModel):
    class_id: UUID
    fee_plan_id: UUID
    period_start: datetime
    period_end: datetime
    due_date: datetime
