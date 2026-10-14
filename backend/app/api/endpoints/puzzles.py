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
    ValidateSolutionRequest,
    ValidateSolutionResponse,
)
from app.services import puzzle_service
from app.api.access import ensure_puzzle_access, ensure_scan_job_access
from app.services import scan_service

router = APIRouter()

TEACHER_ROLES = ("super_admin", "center_admin", "admin", "teacher")


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
    center_filter = None if current_user.role == "super_admin" else current_user.center_id
    return await puzzle_service.list_puzzles(
        db=db,
        difficulty=difficulty,
        puzzle_type=puzzle_type,
        search=search,
        center_id=center_filter,
        skip=skip,
        limit=limit,
        # Học sinh chỉ thấy bài đã chứng minh được lời giải
        verified_only=current_user.role == "student",
    )


@router.post("/validate-solution", response_model=ValidateSolutionResponse)
async def validate_solution(
    req: ValidateSolutionRequest,
    current_user: User = Depends(get_current_user),
):
    """
    Kiểm tra một dãy nước UCI trước khi lưu bài: từng nước có hợp lệ, có đúng
    lượt, nước của bên tấn công có ép được mate, và cả dãy có dẫn tới chiếu hết
    đúng số nước đã khai báo. Chỉ đọc, không ghi DB.
    """
    if current_user.role not in TEACHER_ROLES:
        raise HTTPException(status_code=403, detail="Only teachers can validate solutions")

    check = await puzzle_service.verify_line(
        fen=req.fen,
        moves_uci=req.moves_uci,
        puzzle_type=req.puzzle_type,
    )
    tree = None
    if check.ok and check.mate_in:
        try:
            import chess
            from app.services import mate_solver
            tree = mate_solver.build_solution_tree(
                chess.Board(req.fen),
                check.mate_in,
                budget=mate_solver._Budget(mate_solver.DEFAULT_NODE_BUDGET, deadline_s=4.0),
            )
        except Exception as exc:
            import logging
            logging.getLogger(__name__).warning("Build tree on validate failed: %s", exc)

    return ValidateSolutionResponse(
        ok=check.ok,
        fen=check.fen,
        player_color=check.player_color,
        plies=[vars(p) for p in check.plies],
        ends_in_mate=check.ends_in_mate,
        mate_in=check.mate_in,
        declared_mate_in=check.declared_mate_in,
        expected_plies=check.expected_plies,
        errors=check.errors,
        warnings=check.warnings,
        player_moves=[vars(p) for p in check.player_moves],
        opponent_moves=[vars(p) for p in check.opponent_moves],
        solution_tree=tree,
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
    if current_user.role not in TEACHER_ROLES:
        raise HTTPException(status_code=403, detail="Only teachers can create puzzles")

    if current_user.role != "super_admin":
        if not current_user.center_id:
            raise HTTPException(status_code=400, detail="User is not assigned to any center")
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
    if current_user.role not in TEACHER_ROLES:
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
    if current_user.role not in TEACHER_ROLES:
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
    if current_user.role not in TEACHER_ROLES:
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
            # Giáo viên chuyển một bàn cụ thể: lời giải gửi lên phải chứng minh được
            strict=True,
        )
        await db.commit()
        return puzzle
    except ValueError as exc:
        await db.rollback()
        raise HTTPException(status_code=400, detail=str(exc))
