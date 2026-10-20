"""
Scan API — Sprint 3A
POST /api/scan/upload    → upload PDF, queue Celery job
GET  /api/scan/jobs      → list scan jobs
GET  /api/scan/jobs/{id} → job detail + results
GET  /api/scan/jobs/{id}/results → results only
PUT  /api/scan/results/{id}/review  → teacher corrects FEN
POST /api/scan/results/{id}/approve → approve → ready for puzzle creation
"""

import re
import uuid
from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.config import settings
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
MAX_UPLOAD_BYTES = settings.MAX_UPLOAD_SIZE_MB * 1024 * 1024
ALLOWED_TYPES = {"application/pdf", "application/x-pdf"}
UPLOAD_ROLES = ("super_admin", "center_admin", "admin", "teacher")
STAFF_ROLES = UPLOAD_ROLES
PDF_MAGIC = b"%PDF-"
READ_CHUNK_BYTES = 1024 * 1024


from app.api.access import ensure_scan_job_access


def _infer_puzzle_type_from_filename(filename: str | None) -> str:
    """
    Đoán puzzle_type từ tên file PDF để tự động phân loại đúng khi approve.

    Ví dụ:
      'mate4-odd-odd.pdf'  → 'mate-in-4'
      'chieumat3.pdf'      → 'mate-in-3'
      'mate_in_2.pdf'      → 'mate-in-2'
      'tactics-fork.pdf'   → 'tactic'  (mặc định)
    """
    if not filename:
        return "tactic"
    import unicodedata
    import re as _re
    # Bỏ dấu tiếng Việt và chữ hoa
    norm = unicodedata.normalize('NFKD', filename).encode('ASCII', 'ignore').decode('utf-8').lower()
    
    # Pattern 1: mate-in-N, mateN, mate N
    m = _re.search(r'mate[-_ ]?(?:in[-_ ]?)?(\d)', norm)
    if not m:
        # Pattern 2: chieu het N, chieu mat N, chieu N
        m = _re.search(r'chieu[-_ ]*(?:mat|het)?[-_ ]*(\d)', norm)
    if not m:
        # Pattern 3: N nuoc chieu, N nuoc mat, N nuoc het
        m = _re.search(r'(\d)[-_ ]*nuoc[-_ ]*(?:chieu|mat|het)?', norm)
    if not m:
        # Pattern 4: matN (ngắn gọn)
        m = _re.search(r'(?<![a-z])mat[-_ ]*(\d)', norm)
    if m:
        n = int(m.group(1))
        if 1 <= n <= 8:
            return f"mate-in-{n}"
    return "tactic"


# ── Upload ────────────────────────────────────────────────────

@router.post("/upload", response_model=ScanJobRead, status_code=status.HTTP_202_ACCEPTED)
async def upload_pdf(
    file: UploadFile = File(...),
    center_id: str | None = Form(None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Upload a chess book PDF.
    Returns a ScanJob in PENDING state immediately.
    Processing is queued as a Celery background task.
    """
    if current_user.role not in UPLOAD_ROLES:
        raise HTTPException(403, detail="Only admins and teachers can upload PDFs")

    # Validate file type
    if file.content_type not in ALLOWED_TYPES and not (file.filename or "").lower().endswith(".pdf"):
        raise HTTPException(400, detail="Only PDF files are accepted")

    # Read in chunks and abort as soon as the size limit is exceeded
    buf = bytearray()
    while True:
        chunk = await file.read(READ_CHUNK_BYTES)
        if not chunk:
            break
        buf.extend(chunk)
        if len(buf) > MAX_UPLOAD_BYTES:
            raise HTTPException(413, detail="File too large (max 50 MB)")
    file_bytes = bytes(buf)
    if len(file_bytes) == 0:
        raise HTTPException(400, detail="Empty file")
    if not file_bytes.startswith(PDF_MAGIC):
        raise HTTPException(400, detail="Invalid PDF file")

    # Sanitize original filename (kept for display only, never used as a path)
    safe_name = Path(file.filename or "upload.pdf").name
    safe_name = re.sub(r"[^\w.\- ]", "_", safe_name)[:200] or "upload.pdf"

    target_center_id: uuid.UUID | None = None
    if center_id and center_id.strip():
        try:
            target_center_id = uuid.UUID(center_id.strip())
        except ValueError:
            raise HTTPException(400, detail="Invalid center_id")

    # Strict center binding for non-super_admin callers
    if current_user.role != "super_admin":
        if not current_user.center_id:
            raise HTTPException(400, detail="User is not assigned to any center.")
        target_center_id = current_user.center_id
    elif not target_center_id and current_user.center_id:
        target_center_id = current_user.center_id

    # Verify center exists
    from sqlalchemy import select
    from app.models.center import Center

    resolved_center_id: uuid.UUID | None = None
    if target_center_id:
        res = await db.execute(select(Center.id).where(Center.id == target_center_id))
        resolved_center_id = res.scalar_one_or_none()

    if not resolved_center_id and current_user.role == "super_admin":
        res = await db.execute(select(Center.id).limit(1))
        resolved_center_id = res.scalar_one_or_none()

    if not resolved_center_id:
        raise HTTPException(400, detail="No active center found in database. Please configure a center first.")

    job_id = uuid.uuid4()

    # Save PDF to storage
    file_url, file_size = await pdf_service.save_pdf(
        file_bytes, safe_name, str(job_id)
    )

    # Create DB record
    job = await scan_service.create_scan_job(
        db=db,
        id=job_id,
        center_id=resolved_center_id,
        uploaded_by=current_user.id,
        file_name=safe_name,
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
    """List scan jobs. Scoped strictly to caller's center unless super_admin."""
    center_filter = None if current_user.role == "super_admin" else current_user.center_id
    uploaded_by = None
    if current_user.role not in ("super_admin", "center_admin", "admin", "teacher"):
        uploaded_by = current_user.id

    return await scan_service.list_scan_jobs(
        db, center_id=center_filter, uploaded_by=uploaded_by, status=status, skip=skip, limit=limit
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
    ensure_scan_job_access(job, current_user)
    return job


@router.delete("/jobs/{job_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_job(
    job_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Delete a scan job and all its physical files and results."""
    job = await scan_service.get_scan_job(db, job_id)
    if not job:
        raise HTTPException(404, detail="Scan job not found")
    
    # Only allow the user who uploaded it, or admins/teachers
    ensure_scan_job_access(job, current_user)
    
    await scan_service.delete_scan_job(db, job)
    await db.commit()



@router.get("/jobs/{job_id}/results", response_model=list[ScanResultRead])
async def get_job_results(
    job_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    job = await scan_service.get_scan_job(db, job_id)
    if not job:
        raise HTTPException(404, detail="Scan job not found")
    ensure_scan_job_access(job, current_user)
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

    job = await scan_service.get_scan_job(db, result.job_id)
    ensure_scan_job_access(job, current_user)

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

    job = await scan_service.get_scan_job(db, result.job_id)
    ensure_scan_job_access(job, current_user)



    target_fen = result.fen_final or result.fen_candidate
    await scan_service.update_result_review(
        db=db,
        result=result,
        reviewed_by=current_user.id,
        fen_final=target_fen,
        review_status=ReviewStatus.APPROVED.value,
    )

    # Auto-create puzzle in Puzzle Bank if not already created
    if target_fen and not result.puzzle_id:
        from app.schemas.puzzle import CreatePuzzleFromScanRequest
        from app.services import puzzle_service
        try:
            puzzle = await puzzle_service.create_puzzle_from_scan(
                db=db,
                user_id=current_user.id,
                req=CreatePuzzleFromScanRequest(
                    scan_result_id=result.id,
                    title=f"{job.file_name} - Trang {result.page_number} / Bàn {result.board_index}",
                    description=f"Quét tự động từ tài liệu {job.file_name} (Trang {result.page_number}, Bàn {result.board_index})",
                    difficulty="easy",
                    # Tự nhận diện từ tên file; solver sẽ xác nhận lại khi chứng minh
                    puzzle_type=_infer_puzzle_type_from_filename(job.file_name),
                ),
                center_id=job.center_id or current_user.center_id,
                strict=False,
            )
            result.puzzle_id = puzzle.id
        except Exception as exc:
            import logging
            logging.getLogger(__name__).warning("Auto create puzzle on approve failed: %s", exc)

    await db.commit()
    await db.refresh(result)
    return result


@router.post("/jobs/{job_id}/save-approved", response_model=dict)
async def save_approved_puzzles_for_job(
    job_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Converts all approved scan results in a job that don't have a puzzle yet into puzzles."""
    if current_user.role not in ("super_admin", "admin", "teacher"):
        raise HTTPException(403, detail="Only teachers can save puzzles from scan")

    job = await scan_service.get_scan_job(db, job_id)
    if not job:
        raise HTTPException(404, detail="Scan job not found")
    ensure_scan_job_access(job, current_user)

    results = await scan_service.get_job_results(db, job_id)
    saved_count = 0
    verified_count = 0
    unverified: list[str] = []
    from app.schemas.puzzle import CreatePuzzleFromScanRequest
    from app.services import puzzle_service

    for r in results:
        if r.review_status == ReviewStatus.APPROVED.value and not r.puzzle_id:
            target_fen = r.fen_final or r.fen_candidate
            if target_fen:
                try:
                    puzzle = await puzzle_service.create_puzzle_from_scan(
                        db=db,
                        user_id=current_user.id,
                        req=CreatePuzzleFromScanRequest(
                            scan_result_id=r.id,
                            title=f"{job.file_name} - Trang {r.page_number} / Bàn {r.board_index}",
                            description=f"Quét tự động từ tài liệu {job.file_name} (Trang {r.page_number}, Bàn {r.board_index})",
                            difficulty="easy",
                            # Tự nhận diện từ tên file; solver sẽ xác nhận lại khi chứng minh
                            puzzle_type=_infer_puzzle_type_from_filename(job.file_name),
                        ),
                        center_id=job.center_id or current_user.center_id,
                        # Một bàn quét hỏng không được làm fail cả batch
                        strict=False,
                    )
                    r.puzzle_id = puzzle.id
                    saved_count += 1
                    if puzzle.solution_verified:
                        verified_count += 1
                    else:
                        unverified.append(f"Trang {r.page_number} / Bàn {r.board_index}")
                except Exception as exc:
                    import logging
                    logging.getLogger(__name__).warning("Batch create puzzle failed for %s: %s", r.id, exc)

    await db.commit()
    msg = f"Đã tạo {saved_count} bài tập, {verified_count} bài có lời giải đã được chứng minh"
    if unverified:
        msg += f". {len(unverified)} bài cần giáo viên rà lại lời giải"
    return {
        "message": msg,
        "saved_count": saved_count,
        "verified_count": verified_count,
        "needs_review": unverified,
    }


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

    job = await scan_service.get_scan_job(db, result.job_id)
    ensure_scan_job_access(job, current_user)

    await scan_service.update_result_review(
        db=db,
        result=result,
        reviewed_by=current_user.id,
        review_status=ReviewStatus.REJECTED.value,
    )
    await db.commit()
    await db.refresh(result)
    return result
