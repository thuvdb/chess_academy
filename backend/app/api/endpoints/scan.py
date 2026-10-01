"""
Scan API — Sprint 3A
POST /api/scan/upload    → upload PDF, queue Celery job
GET  /api/scan/jobs      → list scan jobs
GET  /api/scan/jobs/{id} → job detail + results
GET  /api/scan/jobs/{id}/results → results only
PUT  /api/scan/results/{id}/review  → teacher corrects FEN
POST /api/scan/results/{id}/approve → approve → ready for puzzle creation
"""

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.api.deps import get_current_user
from app.models.user import User
from app.models.scan import ScanJob, ScanResult
from app.models.base import ReviewStatus
from app.services import pdf_service, scan_service
from app.schemas.scan import (
    ScanJobRead, ScanResultRead, ScanResultReviewRequest,
)

router = APIRouter()

# Max upload size: 50 MB
MAX_UPLOAD_BYTES = 50 * 1024 * 1024
ALLOWED_TYPES = {"application/pdf", "application/x-pdf"}


# ── Upload ────────────────────────────────────────────────────

@router.post("/upload", response_model=ScanJobRead, status_code=status.HTTP_202_ACCEPTED)
async def upload_pdf(
    file: UploadFile = File(...),
    center_id: str = Form(...),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Upload a chess book PDF.
    Returns a ScanJob in PENDING state immediately.
    Processing is queued as a Celery background task.
    """
    # Validate file type
    if file.content_type not in ALLOWED_TYPES and not (
        file.filename or "").lower().endswith(".pdf")
    :
        raise HTTPException(400, detail="Only PDF files are accepted")

    file_bytes = await file.read()
    if len(file_bytes) > MAX_UPLOAD_BYTES:
        raise HTTPException(413, detail="File too large (max 50 MB)")
    if len(file_bytes) == 0:
        raise HTTPException(400, detail="Empty file")

    try:
        center_uuid = uuid.UUID(center_id)
    except ValueError:
        raise HTTPException(400, detail="Invalid center_id")

    # Save PDF to storage
    file_url, file_size = await pdf_service.save_pdf(
        file_bytes, file.filename or "upload.pdf", str(uuid.uuid4())
    )

    # Create DB record
    job = await scan_service.create_scan_job(
        db=db,
        center_id=center_uuid,
        uploaded_by=current_user.id,
        file_name=file.filename or "upload.pdf",
        file_url=file_url,
        file_size=file_size,
    )
    await db.commit()

    # Queue background task
    try:
        from app.tasks_scan import process_scan_job
        process_scan_job.delay(str(job.id))
    except Exception as exc:
        # Non-fatal: job is in DB, can be retried manually
        import logging
        logging.getLogger(__name__).warning("Failed to queue scan task: %s", exc)

    return job


# ── Jobs ──────────────────────────────────────────────────────

@router.get("/jobs", response_model=list[ScanJobRead])
async def list_jobs(
    status: str | None = None,
    skip: int = 0,
    limit: int = 50,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List scan jobs. Admins/teachers see all; students see only theirs."""
    uploaded_by = None
    if current_user.role not in ("super_admin", "admin", "teacher"):
        uploaded_by = current_user.id

    return await scan_service.list_scan_jobs(
        db, uploaded_by=uploaded_by, status=status, skip=skip, limit=limit
    )


@router.get("/jobs/{job_id}", response_model=ScanJobRead)
async def get_job(
    job_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    job = await scan_service.get_scan_job(db, job_id)
    if not job:
        raise HTTPException(404, detail="Scan job not found")
    return job


@router.get("/jobs/{job_id}/results", response_model=list[ScanResultRead])
async def get_job_results(
    job_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    job = await scan_service.get_scan_job(db, job_id)
    if not job:
        raise HTTPException(404, detail="Scan job not found")
    return await scan_service.get_job_results(db, job_id)


# ── Review ────────────────────────────────────────────────────

@router.put("/results/{result_id}/review", response_model=ScanResultRead)
async def review_result(
    result_id: uuid.UUID,
    body: ScanResultReviewRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Teacher reviews / corrects a scan result FEN."""
    if current_user.role not in ("super_admin", "admin", "teacher"):
        raise HTTPException(403, detail="Only teachers can review scan results")

    result = await scan_service.get_scan_result(db, result_id)
    if not result:
        raise HTTPException(404, detail="Scan result not found")

    await scan_service.update_result_review(
        db=db,
        result=result,
        reviewed_by=current_user.id,
        fen_final=body.fen_final,
        side_to_move=body.side_to_move,
        castling_rights=body.castling_rights,
        en_passant=body.en_passant,
        review_status=ReviewStatus.CORRECTED.value,
    )
    await db.commit()
    await db.refresh(result)
    return result


@router.post("/results/{result_id}/approve", response_model=ScanResultRead)
async def approve_result(
    result_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Approve a scan result — marks it ready for puzzle creation."""
    if current_user.role not in ("super_admin", "admin", "teacher"):
        raise HTTPException(403, detail="Only teachers can approve scan results")

    result = await scan_service.get_scan_result(db, result_id)
    if not result:
        raise HTTPException(404, detail="Scan result not found")

    if result.review_status == ReviewStatus.REJECTED.value:
        raise HTTPException(400, detail="Cannot approve a rejected result")

    await scan_service.update_result_review(
        db=db,
        result=result,
        reviewed_by=current_user.id,
        fen_final=result.fen_final or result.fen_candidate,
        review_status=ReviewStatus.APPROVED.value,
    )
    await db.commit()
    await db.refresh(result)
    return result


@router.post("/results/{result_id}/reject", response_model=ScanResultRead)
async def reject_result(
    result_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Reject a scan result."""
    if current_user.role not in ("super_admin", "admin", "teacher"):
        raise HTTPException(403, detail="Only teachers can reject scan results")

    result = await scan_service.get_scan_result(db, result_id)
    if not result:
        raise HTTPException(404, detail="Scan result not found")

    await scan_service.update_result_review(
        db=db,
        result=result,
        reviewed_by=current_user.id,
        review_status=ReviewStatus.REJECTED.value,
    )
    await db.commit()
    await db.refresh(result)
    return result
