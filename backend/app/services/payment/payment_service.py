from typing import Dict, Any, Optional
from uuid import UUID
from datetime import datetime, timezone
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.models.payment import Payment, Invoice
from app.models.base import PaymentStatus, PaymentLevel, PaymentMethod, PaymentProvider
from app.services.payment.providers.vietqr import VietQRProvider


class PaymentService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.providers = {
            "vietqr": VietQRProvider(),
        }

    async def get_payment_qr(self, invoice: Invoice) -> str:
        """Get the QR code URL for an invoice using VietQR MVP level."""
        provider = self.providers["vietqr"]
        return provider.generate_static_qr(
            amount=int(invoice.amount),
            description=invoice.invoice_number,
        )

    async def confirm_payment(
        self,
        invoice_id: UUID,
        admin_id: UUID,
        notes: Optional[str] = None
    ) -> Payment:
        """Level 1: Admin manual confirmation of payment."""
        # Find invoice
        result = await self.db.execute(select(Invoice).where(Invoice.id == invoice_id))
        invoice = result.scalars().first()
        if not invoice:
            raise ValueError("Invoice not found")

        if invoice.status == "paid":
            raise ValueError("Invoice is already paid")

        # Create payment record
        now = datetime.now(timezone.utc)
        
        payment = Payment(
            invoice_id=invoice.id,
            payer_id=invoice.student_id,
            amount=invoice.amount,
            currency=invoice.currency,
            payment_method=PaymentMethod.BANK_TRANSFER.value,
            payment_provider=PaymentProvider.VIETQR.value,
            payment_level=PaymentLevel.LEVEL1_MANUAL.value,
            status=PaymentStatus.SUCCESS.value,
            confirmed_by=admin_id,
            paid_at=now,
            payment_data={"notes": notes} if notes else {},
        )
        self.db.add(payment)
        
        # Update invoice status
        invoice.status = "paid"
        
        await self.db.commit()
        await self.db.refresh(payment)
        
        return payment

    async def get_invoice_payments(self, invoice_id: UUID) -> list[Payment]:
        result = await self.db.execute(select(Payment).where(Payment.invoice_id == invoice_id))
        return result.scalars().all()
