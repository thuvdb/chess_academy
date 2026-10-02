from typing import List
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.core.database import get_db
from app.api.deps import get_current_user, require_role
from app.schemas.invoice import InvoiceCreate, InvoiceUpdate, InvoiceResponse, GenerateClassInvoicesRequest
from app.services.invoice_service import InvoiceService
from app.services.payment.payment_service import PaymentService
from app.models.user import User

router = APIRouter()


@router.post("/", response_model=InvoiceResponse, status_code=status.HTTP_201_CREATED)
async def create_invoice(
    invoice_in: InvoiceCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(["admin", "center_admin"]))
):
    service = InvoiceService(db)
    return await service.create(current_user.center_id, invoice_in)


@router.post("/generate", response_model=List[InvoiceResponse], status_code=status.HTTP_201_CREATED)
async def generate_class_invoices(
    req: GenerateClassInvoicesRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(["admin", "center_admin"]))
):
    service = InvoiceService(db)
    try:
        return await service.generate_for_class(current_user.center_id, req)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/my", response_model=List[InvoiceResponse])
async def get_my_invoices(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    service = InvoiceService(db)
    return await service.get_all_by_student(current_user.id)


@router.get("/center", response_model=List[InvoiceResponse])
async def get_center_invoices(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(["admin", "center_admin"]))
):
    service = InvoiceService(db)
    return await service.get_all_by_center(current_user.center_id)


@router.get("/{invoice_id}", response_model=InvoiceResponse)
async def get_invoice(
    invoice_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    service = InvoiceService(db)
    invoice = await service.get_by_id(invoice_id)
    if not invoice:
        raise HTTPException(status_code=404, detail="Invoice not found")
        
    if current_user.role not in ["admin", "center_admin"] and invoice.student_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not enough permissions")
        
    return invoice


@router.get("/{invoice_id}/qr", response_model=dict)
async def get_invoice_qr(
    invoice_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    invoice_service = InvoiceService(db)
    payment_service = PaymentService(db)
    
    invoice = await invoice_service.get_by_id(invoice_id)
    if not invoice:
        raise HTTPException(status_code=404, detail="Invoice not found")
        
    if current_user.role not in ["admin", "center_admin"] and invoice.student_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not enough permissions")
        
    qr_url = await payment_service.get_payment_qr(invoice)
    return {"qr_url": qr_url}


@router.put("/{invoice_id}", response_model=InvoiceResponse)
async def update_invoice(
    invoice_id: UUID,
    invoice_in: InvoiceUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(["admin", "center_admin"]))
):
    service = InvoiceService(db)
    invoice = await service.get_by_id(invoice_id)
    if not invoice:
        raise HTTPException(status_code=404, detail="Invoice not found")
    if invoice.center_id != current_user.center_id and current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Not enough permissions")
        
    return await service.update(invoice_id, invoice_in)
