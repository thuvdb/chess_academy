from datetime import datetime
from typing import Any, Dict, Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class PaymentBase(BaseModel):
    invoice_id: Optional[UUID] = None
    payer_id: Optional[UUID] = None
    amount: float
    currency: str = "VND"
    payment_method: Optional[str] = None
    payment_provider: Optional[str] = None
    transaction_id: Optional[str] = None
    reference: Optional[str] = None
    payment_data: Optional[Dict[str, Any]] = None


class PaymentCreate(PaymentBase):
    pass


class PaymentConfirmRequest(BaseModel):
    invoice_id: UUID
    notes: Optional[str] = None


class PaymentResponse(PaymentBase):
    id: UUID
    payment_level: str
    status: str
    confirmed_by: Optional[UUID] = None
    paid_at: Optional[datetime] = None
    created_at: datetime
    updated_at: Optional[datetime]

    model_config = ConfigDict(from_attributes=True)
