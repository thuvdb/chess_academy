"""
Puzzles API — Sprint 4
Endpoints for Puzzle CRUD, search, filter, and conversion from scan results.
"""

import uuid
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.core.database import get_db
from app.models.user import User
from app.schemas.puzzle import (
    CreatePuzzleFromScanRequest,
    PuzzleCreate,
    PuzzleRead,
    PuzzleUpdate,
)
from app.services import puzzle_service
from app.api.access import ensure_puzzle_access, ensure_scan_job_access
from app.services import scan_service

router = APIRouter()


@router.get("", response_model=list[PuzzleRead])
async def list_puzzles(
    difficulty: Optional[str] = Query(None),
    puzzle_type: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List puzzles with optional filtering."""
    return await puzzle_service.list_puzzles(
        db=db,
        difficulty=difficulty,
        puzzle_type=puzzle_type,
        search=search,
        center_id=current_user.center_id,
        skip=skip,
        limit=limit,
    )


@router.get("/{puzzle_id}", response_model=PuzzleRead)
async def get_puzzle(
    puzzle_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    puzzle = await puzzle_service.get_puzzle(db, puzzle_id)
    if not puzzle:
        raise HTTPException(status_code=404, detail="Puzzle not found")
    ensure_puzzle_access(puzzle, current_user, write=False)
    return puzzle


@router.post("", response_model=PuzzleRead, status_code=status.HTTP_201_CREATED)
async def create_puzzle(
    data: PuzzleCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Create a new puzzle (Teachers and Admins)."""
    if current_user.role not in ("super_admin", "admin", "teacher"):
        raise HTTPException(status_code=403, detail="Only teachers can create puzzles")

    if current_user.role != "super_admin":
        data.center_id = current_user.center_id
    elif not data.center_id:
        data.center_id = current_user.center_id

    try:
        puzzle = await puzzle_service.create_puzzle(
            db=db,
            created_by=current_user.id,
            data=data,
        )
        await db.commit()
        return puzzle
    except ValueError as exc:
        await db.rollback()
        raise HTTPException(status_code=400, detail=str(exc))


@router.put("/{puzzle_id}", response_model=PuzzleRead)
async def update_puzzle(
    puzzle_id: uuid.UUID,
    data: PuzzleUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if current_user.role not in ("super_admin", "admin", "teacher"):
        raise HTTPException(status_code=403, detail="Only teachers can update puzzles")

    puzzle = await puzzle_service.get_puzzle(db, puzzle_id)
    if not puzzle:
        raise HTTPException(status_code=404, detail="Puzzle not found")
    ensure_puzzle_access(puzzle, current_user, write=True)

    try:
        updated = await puzzle_service.update_puzzle(db, puzzle, data)
        await db.commit()
        return updated
    except ValueError as exc:
        await db.rollback()
        raise HTTPException(status_code=400, detail=str(exc))


@router.delete("/{puzzle_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_puzzle(
    puzzle_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if current_user.role not in ("super_admin", "admin", "teacher"):
        raise HTTPException(status_code=403, detail="Only teachers can delete puzzles")

    puzzle = await puzzle_service.get_puzzle(db, puzzle_id)
    if not puzzle:
        raise HTTPException(status_code=404, detail="Puzzle not found")
    ensure_puzzle_access(puzzle, current_user, write=True)

    await puzzle_service.delete_puzzle(db, puzzle)
    await db.commit()


@router.post("/from-scan", response_model=PuzzleRead, status_code=status.HTTP_201_CREATED)
async def create_puzzle_from_scan(
    req: CreatePuzzleFromScanRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Converts an approved ScanResult to a Puzzle in the library."""
    if current_user.role not in ("super_admin", "admin", "teacher"):
        raise HTTPException(status_code=403, detail="Only teachers can create puzzles from scan")

    # Verify scan result access
    scan_res = await scan_service.get_scan_result(db, req.scan_result_id)
    if not scan_res:
        raise HTTPException(status_code=404, detail="Scan result not found")
    job = await scan_service.get_scan_job(db, scan_res.job_id)
    ensure_scan_job_access(job, current_user)

    try:
        puzzle = await puzzle_service.create_puzzle_from_scan(
            db=db,
            user_id=current_user.id,
            center_id=current_user.center_id if current_user.role != "super_admin" else None,
            req=req,
        )
        await db.commit()
        return puzzle
    except ValueError as exc:
        await db.rollback()
        raise HTTPException(status_code=400, detail=str(exc))
