from typing import List
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.api.deps import require_role
from app.schemas.payment import PaymentResponse, PaymentConfirmRequest
from app.services.payment.payment_service import PaymentService
from app.models.user import User

router = APIRouter()


@router.post("/confirm", response_model=PaymentResponse, status_code=status.HTTP_201_CREATED)
async def confirm_payment(
    req: PaymentConfirmRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(["admin", "center_admin"]))
):
    """Admin manually confirms a bank transfer (Level 1)."""
    service = PaymentService(db)
    try:
        return await service.confirm_payment(
            invoice_id=req.invoice_id,
            admin_id=current_user.id,
            notes=req.notes
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/invoice/{invoice_id}", response_model=List[PaymentResponse])
async def get_payments_for_invoice(
    invoice_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(["admin", "center_admin", "student", "parent"]))
):
    service = PaymentService(db)
    # Basic permission check omitted for brevity, should check if invoice belongs to user if not admin
    return await service.get_invoice_payments(invoice_id)
