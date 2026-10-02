from typing import List, Optional
from uuid import UUID
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.models.payment import Invoice, FeePlan
from app.models.class_ import ClassEnrollment
from app.schemas.invoice import InvoiceCreate, InvoiceUpdate, GenerateClassInvoicesRequest
from app.models.base import InvoiceStatus


class InvoiceService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_all_by_center(self, center_id: UUID) -> List[Invoice]:
        result = await self.db.execute(select(Invoice).where(Invoice.center_id == center_id))
        return list(result.scalars().all())
        
    async def get_all_by_student(self, student_id: UUID) -> List[Invoice]:
        result = await self.db.execute(select(Invoice).where(Invoice.student_id == student_id))
        return list(result.scalars().all())

    async def get_by_id(self, invoice_id: UUID) -> Optional[Invoice]:
        result = await self.db.execute(select(Invoice).where(Invoice.id == invoice_id))
        return result.scalars().first()

    async def create(self, center_id: UUID, invoice_in: InvoiceCreate) -> Invoice:
        # Generate a simple invoice number INV-YYYY-UUID
        year = datetime.now().year
        import uuid
        short_id = str(uuid.uuid4())[:8].upper()
        invoice_number = f"INV-{year}-{short_id}"
        
        invoice = Invoice(
            center_id=center_id,
            invoice_number=invoice_number,
            status=InvoiceStatus.DRAFT.value,
            **invoice_in.model_dump()
        )
        self.db.add(invoice)
        await self.db.commit()
        await self.db.refresh(invoice)
        return invoice

    async def update(self, invoice_id: UUID, invoice_in: InvoiceUpdate) -> Optional[Invoice]:
        invoice = await self.get_by_id(invoice_id)
        if not invoice:
            return None

        update_data = invoice_in.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(invoice, field, value)

        await self.db.commit()
        await self.db.refresh(invoice)
        return invoice

    async def delete(self, invoice_id: UUID) -> bool:
        invoice = await self.get_by_id(invoice_id)
        if not invoice:
            return False
            
        await self.db.delete(invoice)
        await self.db.commit()
        return True

    async def generate_for_class(self, center_id: UUID, req: GenerateClassInvoicesRequest) -> List[Invoice]:
        """Generate invoices for all active students in a class."""
        # 1. Get Fee Plan
        fp_result = await self.db.execute(select(FeePlan).where(FeePlan.id == req.fee_plan_id))
        fee_plan = fp_result.scalars().first()
        if not fee_plan:
            raise ValueError("Fee plan not found")

        # 2. Get students in class
        enrollment_result = await self.db.execute(
            select(ClassEnrollment).where(
                ClassEnrollment.class_id == req.class_id,
                ClassEnrollment.status == "active"
            )
        )
        enrollments = enrollment_result.scalars().all()
        
        invoices = []
        year = datetime.now().year
        import uuid
        
        for enr in enrollments:
            short_id = str(uuid.uuid4())[:8].upper()
            invoice = Invoice(
                center_id=center_id,
                student_id=enr.student_id,
                class_id=req.class_id,
                fee_plan_id=fee_plan.id,
                invoice_number=f"INV-{year}-{short_id}",
                amount=fee_plan.amount,
                currency=fee_plan.currency,
                description=f"Hoc phi {fee_plan.name}",
                status=InvoiceStatus.SENT.value, # Publish directly for MVP
                due_date=req.due_date,
                period_start=req.period_start,
                period_end=req.period_end,
            )
            self.db.add(invoice)
            invoices.append(invoice)
            
        await self.db.commit()
        for inv in invoices:
            await self.db.refresh(inv)
            
        return invoices
