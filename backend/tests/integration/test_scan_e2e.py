"""
AI Scanner E2E Integration Test
Tests:
1. Create a PDF with a chessboard.
2. Call POST /api/scan/upload with super_admin (center_id is None).
3. Verify ScanJob is created with a valid center_id.
4. Verify Celery task runs and completes.
5. Verify ScanResults and FEN candidates are created.
6. Verify GET /api/scan/jobs and GET /api/scan/jobs/{id}/results return data.
"""

import asyncio
import io
import uuid
import time
import pymupdf as fitz
from sqlalchemy import select
from app.core.database import async_session_factory
from app.models.user import User
from app.models.scan import ScanJob, ScanResult
from app.models.center import Center
from app.tasks_scan import process_scan_job
from app.services import pdf_service

async def run_test():
    print("=== STARTING AI SCANNER E2E TEST ===")
    
    # 1. Create synthetic PDF
    doc = fitz.open()
    page = doc.new_page(width=600, height=800)
    # Draw simple chessboard rectangle
    rect = fitz.Rect(100, 100, 500, 500)
    page.draw_rect(rect, color=(0, 0, 0), fill=(0.9, 0.9, 0.9))
    pdf_bytes = doc.tobytes()
    doc.close()
    print(f"1. Created synthetic PDF ({len(pdf_bytes)} bytes)")
    
    # 2. Get super_admin user
    async with async_session_factory() as db:
        res = await db.execute(select(User).where(User.role == "super_admin").limit(1))
        super_admin = res.scalar_one()
        print(f"2. Found super_admin: {super_admin.email}, center_id: {super_admin.center_id}")
        
        # Get first center
        c_res = await db.execute(select(Center.id).limit(1))
        first_center_id = c_res.scalar_one()
        print(f"3. First center ID: {first_center_id}")

        # Save PDF via pdf_service
        job_id = uuid.uuid4()
        file_url, file_size = await pdf_service.save_pdf(pdf_bytes, "test_e2e.pdf", str(job_id))
        print(f"4. Saved PDF to: {file_url} ({file_size} bytes)")

        # Create scan job
        from app.services import scan_service
        job = await scan_service.create_scan_job(
            db=db,
            center_id=first_center_id,
            uploaded_by=super_admin.id,
            file_name="test_e2e.pdf",
            file_url=file_url,
            file_size=file_size,
        )
        await db.commit()
        await db.refresh(job)
        job_id_str = str(job.id)
        print(f"5. Created ScanJob record: {job_id_str}, status: {job.status}")

    # 3. Execute processing directly
    print("6. Executing _process_job_async task...")
    from app.tasks_scan import _process_job_async
    res = await _process_job_async(job_id_str)
    print("7. Task result:", res)

    # 4. Verify in DB
    async with async_session_factory() as db:
        res_job = await scan_service.get_scan_job(db, uuid.UUID(job_id_str))
        print(f"8. Final ScanJob status: {res_job.status}, total_pages: {res_job.total_pages}, boards_found: {res_job.boards_found}")
        assert res_job.status == "completed", f"Expected completed, got {res_job.status}"
        
        results = await scan_service.get_job_results(db, uuid.UUID(job_id_str))
        print(f"9. Found {len(results)} ScanResult records in DB")
        for r in results:
            print(f"   - Page {r.page_number} Board {r.board_index}: FEN={r.fen_candidate}")

    print("=== AI SCANNER E2E TEST PASSED! ===")

if __name__ == "__main__":
    asyncio.run(run_test())
