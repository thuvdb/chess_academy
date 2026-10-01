"""
Scan pipeline Celery task — Sprint 3A
Runs as a background job: PDF → pages → board detection → DB scan_results.
"""

import logging
import time
import uuid

from app.core.celery_app import celery_app

logger = logging.getLogger(__name__)


@celery_app.task(
    name="app.tasks.scan.process_scan_job",
    bind=True,
    max_retries=2,
    default_retry_delay=10,
    acks_late=True,
)
def process_scan_job(self, job_id: str) -> dict:
    """
    Background task: process one ScanJob end-to-end (Sprint 3A scope).

    Steps:
      1. Load PDF bytes from storage
      2. Render pages → PNG images
      3. Run board_detector on each page
      4. Save scan_results to DB
      5. Update ScanJob status → completed / failed
    """
    import asyncio
    from sqlalchemy import select

    # We need a sync entry point for Celery; run async code via asyncio.
    return asyncio.run(_process_job_async(job_id))


async def _process_job_async(job_id: str) -> dict:
    """Async implementation called from the Celery task."""
    from app.core.database import async_session_factory
    from app.services import pdf_service, scan_service
    from app.services.board_detector import detect_boards
    from app.models.base import ScanStatus

    start = time.monotonic()
    logger.info("Processing ScanJob: %s", job_id)

    async with async_session_factory() as db:
        job = await scan_service.get_scan_job(db, uuid.UUID(job_id))
        if not job:
            logger.error("ScanJob not found: %s", job_id)
            return {"error": "Job not found"}

        # Mark as processing
        await scan_service.update_job_status(db, job, ScanStatus.PROCESSING.value)
        await db.commit()

        try:
            # 1. Load PDF bytes
            file_bytes = pdf_service.get_local_file_bytes(job.file_url)

            # 2. Render pages to PNG
            pages = await pdf_service.render_pdf_pages(file_bytes, str(job.id))

            total_pages = len(pages)
            total_boards = 0

            # 3. Detect boards on each page
            for page in pages:
                page_num = page["page_number"]
                try:
                    # Load rendered page image
                    page_img_bytes = pdf_service.get_local_file_bytes(page["image_url"])
                    boards = detect_boards(page_img_bytes)
                except Exception as exc:
                    logger.warning("Board detection failed on page %d: %s", page_num, exc)
                    boards = []

                # 4. Save each detected board to DB
                for board in boards:
                    await scan_service.create_scan_result(
                        db=db,
                        job_id=job.id,
                        page_number=page_num,
                        board_index=board["board_index"],
                        bounding_box={
                            "x": board["x"],
                            "y": board["y"],
                            "width": board["width"],
                            "height": board["height"],
                        },
                        confidence_board=board["confidence"],
                    )
                    total_boards += 1

            elapsed_ms = int((time.monotonic() - start) * 1000)

            # 5. Mark job complete
            await scan_service.update_job_status(
                db, job,
                status=ScanStatus.COMPLETED.value,
                total_pages=total_pages,
                boards_found=total_boards,
                processing_time_ms=elapsed_ms,
            )
            await db.commit()

            logger.info(
                "ScanJob %s done: %d pages, %d boards in %d ms",
                job_id, total_pages, total_boards, elapsed_ms,
            )
            return {
                "job_id": job_id,
                "total_pages": total_pages,
                "boards_found": total_boards,
                "processing_time_ms": elapsed_ms,
            }

        except Exception as exc:
            elapsed_ms = int((time.monotonic() - start) * 1000)
            logger.exception("ScanJob %s failed: %s", job_id, exc)
            await scan_service.update_job_status(
                db, job,
                status=ScanStatus.FAILED.value,
                error_message=str(exc)[:500],
                processing_time_ms=elapsed_ms,
            )
            await db.commit()
            raise
