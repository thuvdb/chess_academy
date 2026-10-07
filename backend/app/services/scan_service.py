"""
Scan Service — Sprint 3A
Orchestrates the scan pipeline: PDF → pages → board detection → DB records.
"""

import uuid
import logging
import time
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models.scan import ScanJob, ScanResult
from app.models.base import ScanStatus, ReviewStatus

logger = logging.getLogger(__name__)


# ── Job CRUD ─────────────────────────────────────────────────

async def create_scan_job(
    db: AsyncSession,
    id: uuid.UUID,
    center_id: uuid.UUID,
    uploaded_by: uuid.UUID,
    file_name: str,
    file_url: str,
    file_size: int,
) -> ScanJob:
    """Create a new ScanJob record in PENDING state."""
    job = ScanJob(
        id=id,
        center_id=center_id,
        uploaded_by=uploaded_by,
        file_name=file_name,
        file_url=file_url,
        file_size=file_size,
        status=ScanStatus.PENDING.value,
    )
    db.add(job)
    await db.flush()
    await db.refresh(job)
    logger.info("ScanJob created: %s for file '%s'", job.id, file_name)
    return job


async def get_scan_job(db: AsyncSession, job_id: uuid.UUID) -> ScanJob | None:
    result = await db.execute(select(ScanJob).where(ScanJob.id == job_id))
    return result.scalar_one_or_none()


async def list_scan_jobs(
    db: AsyncSession,
    center_id: uuid.UUID | None = None,
    uploaded_by: uuid.UUID | None = None,
    status: str | None = None,
    skip: int = 0,
    limit: int = 50,
) -> list[ScanJob]:
    query = select(ScanJob).offset(skip).limit(limit).order_by(ScanJob.created_at.desc())
    if center_id:
        query = query.where(ScanJob.center_id == center_id)
    if uploaded_by:
        query = query.where(ScanJob.uploaded_by == uploaded_by)
    if status:
        query = query.where(ScanJob.status == status)
    result = await db.execute(query)
    return list(result.scalars().all())


async def get_job_results(db: AsyncSession, job_id: uuid.UUID) -> list[ScanResult]:
    result = await db.execute(
        select(ScanResult)
        .where(ScanResult.job_id == job_id)
        .order_by(ScanResult.page_number, ScanResult.board_index)
    )
    return list(result.scalars().all())


async def update_job_status(
    db: AsyncSession,
    job: ScanJob,
    status: str,
    total_pages: int | None = None,
    boards_found: int | None = None,
    error_message: str | None = None,
    processing_time_ms: int | None = None,
) -> None:
    """Update job status in-place (caller must commit)."""
    job.status = status
    if total_pages is not None:
        job.total_pages = total_pages
    if boards_found is not None:
        job.boards_found = boards_found
    if error_message is not None:
        job.error_message = error_message
    if processing_time_ms is not None:
        job.processing_time_ms = processing_time_ms
    await db.flush()


async def delete_scan_job(db: AsyncSession, job: ScanJob) -> None:
    import shutil
    from app.services.storage_service import SCAN_STORAGE_PATH

    # Delete physical files
    # Attempt to delete based on file_url (for old jobs where uuid differed)
    try:
        folder_uuid = job.file_url.split("/")[-3]
        job_dir_1 = SCAN_STORAGE_PATH / folder_uuid
        if job_dir_1.exists() and job_dir_1.is_dir():
            shutil.rmtree(job_dir_1)
            logger.info("Deleted physical scan directory (from URL): %s", job_dir_1)
    except Exception as e:
        logger.warning("Failed to delete physical scan directory for job %s: %s", job.id, e)

    # Attempt to delete based on job.id (for new jobs)
    try:
        job_dir_2 = SCAN_STORAGE_PATH / str(job.id)
        if job_dir_2.exists() and job_dir_2.is_dir():
            shutil.rmtree(job_dir_2)
            logger.info("Deleted physical scan directory (from job ID): %s", job_dir_2)
    except Exception as e:
        logger.warning("Failed to delete physical scan directory for job %s: %s", job.id, e)

    # DB cascading will delete associated scan_results
    await db.delete(job)
    await db.flush()


# ── Result CRUD ───────────────────────────────────────────────

async def create_scan_result(
    db: AsyncSession,
    job_id: uuid.UUID,
    page_number: int,
    board_index: int,
    bounding_box: dict,
    confidence_board: float,
    board_image_url: str | None = None,
    fen_candidate: str | None = None,
    cell_confidence: dict | None = None,
) -> ScanResult:
    result = ScanResult(
        job_id=job_id,
        page_number=page_number,
        board_index=board_index,
        board_image_url=board_image_url,
        bounding_box=bounding_box,
        confidence_board=confidence_board,
        fen_candidate=fen_candidate,
        cell_confidence=cell_confidence,
        review_status=ReviewStatus.PENDING.value,
    )
    db.add(result)
    await db.flush()
    await db.refresh(result)
    return result


async def get_scan_result(db: AsyncSession, result_id: uuid.UUID) -> ScanResult | None:
    r = await db.execute(select(ScanResult).where(ScanResult.id == result_id))
    return r.scalar_one_or_none()


async def update_result_review(
    db: AsyncSession,
    result: ScanResult,
    reviewed_by: uuid.UUID,
    fen_final: str | None = None,
    side_to_move: str = "w",
    castling_rights: str = "-",
    en_passant: str = "-",
    review_status: str = ReviewStatus.APPROVED.value,
) -> None:
    """Apply teacher review to a scan result."""
    import sqlalchemy
    result.reviewed_by = reviewed_by
    result.reviewed_at = sqlalchemy.func.now()
    result.review_status = review_status
    if fen_final is not None:
        result.fen_final = fen_final
    result.side_to_move = side_to_move
    result.castling_rights = castling_rights
    result.en_passant = en_passant
    await db.flush()
