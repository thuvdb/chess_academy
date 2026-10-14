"""
Assignment Service — Sprint 4
Handles Assignment CRUD and class assignment logic.
"""

import logging
import uuid
from datetime import datetime, timezone
from typing import Optional

from fastapi import HTTPException, status
from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.assignment import Assignment, AssignmentSubmission
from app.models.base import ProgressStatus, SubmissionStatus
from app.models.class_ import ClassEnrollment
from app.models.progress import StudentAttempt, StudentProgress
from app.models.puzzle import Puzzle
from app.schemas.assignment import AssignmentCreate, AssignmentUpdate

logger = logging.getLogger(__name__)


async def create_assignment(
    db: AsyncSession,
    teacher_id: uuid.UUID,
    data: AssignmentCreate,
) -> Assignment:
    assignment = Assignment(
        class_id=data.class_id,
        teacher_id=teacher_id,
        title=data.title,
        description=data.description,
        puzzle_ids=data.puzzle_ids,
        due_date=data.due_date,
        max_attempts=data.max_attempts,
    )
    db.add(assignment)
    await db.flush()
    await db.refresh(assignment)
    return assignment


async def get_assignment(
    db: AsyncSession,
    assignment_id: uuid.UUID,
) -> Assignment | None:
    stmt = (
        select(Assignment)
        .options(selectinload(Assignment.class_), selectinload(Assignment.teacher))
        .where(Assignment.id == assignment_id)
    )
    result = await db.execute(stmt)
    return result.scalar_one_or_none()


async def list_assignments(
    db: AsyncSession,
    center_id: Optional[uuid.UUID] = None,
    class_id: Optional[uuid.UUID] = None,
    teacher_id: Optional[uuid.UUID] = None,
    student_id: Optional[uuid.UUID] = None,
    skip: int = 0,
    limit: int = 50,
) -> list[Assignment]:
    stmt = select(Assignment).options(
        selectinload(Assignment.class_), selectinload(Assignment.teacher)
    )

    if center_id:
        from app.models.class_ import Class
        stmt = stmt.join(Class, Class.id == Assignment.class_id).where(Class.center_id == center_id)

    if class_id:
        stmt = stmt.where(Assignment.class_id == class_id)
    if teacher_id:
        stmt = stmt.where(Assignment.teacher_id == teacher_id)
    if student_id:
        stmt = stmt.join(ClassEnrollment, ClassEnrollment.class_id == Assignment.class_id).where(
            ClassEnrollment.student_id == student_id
        )

    stmt = stmt.order_by(desc(Assignment.created_at)).offset(skip).limit(limit)
    result = await db.execute(stmt)
    return list(result.scalars().all())


async def update_assignment(
    db: AsyncSession,
    assignment: Assignment,
    data: AssignmentUpdate,
) -> Assignment:
    if data.title is not None:
        assignment.title = data.title
    if data.description is not None:
        assignment.description = data.description
    if data.puzzle_ids is not None:
        assignment.puzzle_ids = data.puzzle_ids
    if data.due_date is not None:
        assignment.due_date = data.due_date
    if data.max_attempts is not None:
        assignment.max_attempts = data.max_attempts

    await db.flush()
    await db.refresh(assignment)
    return assignment


async def delete_assignment(
    db: AsyncSession,
    assignment: Assignment,
) -> None:
    await db.delete(assignment)
    await db.flush()


async def get_latest_submission(
    db: AsyncSession,
    assignment_id: uuid.UUID,
    student_id: uuid.UUID,
) -> AssignmentSubmission | None:
    stmt = (
        select(AssignmentSubmission)
        .where(
            AssignmentSubmission.assignment_id == assignment_id,
            AssignmentSubmission.student_id == student_id,
        )
        .order_by(desc(AssignmentSubmission.attempt_no))
    )
    res = await db.execute(stmt)
    return res.scalars().first()


async def get_submission_by_attempt(
    db: AsyncSession,
    assignment_id: uuid.UUID,
    student_id: uuid.UUID,
    attempt_no: int,
) -> AssignmentSubmission | None:
    stmt = (
        select(AssignmentSubmission)
        .where(
            AssignmentSubmission.assignment_id == assignment_id,
            AssignmentSubmission.student_id == student_id,
            AssignmentSubmission.attempt_no == attempt_no,
        )
    )
    res = await db.execute(stmt)
    return res.scalars().first()


async def get_student_submissions(
    db: AsyncSession,
    assignment_id: uuid.UUID,
    student_id: uuid.UUID,
) -> list[AssignmentSubmission]:
    stmt = (
        select(AssignmentSubmission)
        .where(
            AssignmentSubmission.assignment_id == assignment_id,
            AssignmentSubmission.student_id == student_id,
        )
        .order_by(desc(AssignmentSubmission.attempt_no))
    )
    res = await db.execute(stmt)
    return list(res.scalars().all())


async def get_or_create_submission(
    db: AsyncSession,
    assignment_id: uuid.UUID,
    student_id: uuid.UUID,
) -> AssignmentSubmission:
    sub = await get_latest_submission(db, assignment_id, student_id)
    if not sub:
        sub = AssignmentSubmission(
            assignment_id=assignment_id,
            student_id=student_id,
            attempt_no=1,
            version=1,
            status=SubmissionStatus.IN_PROGRESS.value,
        )
        db.add(sub)
        await db.flush()
        await db.refresh(sub)
    return sub


async def submit_assignment(
    db: AsyncSession,
    assignment_id: uuid.UUID,
    student_id: uuid.UUID,
) -> AssignmentSubmission:
    sub = await get_latest_submission(db, assignment_id, student_id)
    if not sub:
        sub = await get_or_create_submission(db, assignment_id, student_id)

    if sub.status in (
        SubmissionStatus.SUBMITTED.value,
        SubmissionStatus.GRADED.value,
        SubmissionStatus.RETURNED.value,
    ):
        return sub

    # Calculate completed puzzles & total points strictly from StudentAttempts belonging to this submission
    stmt = (
        select(StudentAttempt)
        .where(StudentAttempt.submission_id == sub.id)
        .order_by(StudentAttempt.attempt_no)
    )
    res = await db.execute(stmt)
    attempts = res.scalars().all()

    # Deduplicate by progress_id (each puzzle has its progress)
    best_by_progress: dict[uuid.UUID, StudentAttempt] = {}
    for att in attempts:
        pid = att.progress_id
        if pid not in best_by_progress or (att.is_correct and not best_by_progress[pid].is_correct):
            best_by_progress[pid] = att
        elif att.is_correct and (att.points_earned or 0) > (best_by_progress[pid].points_earned or 0):
            best_by_progress[pid] = att

    solved_count = sum(1 for att in best_by_progress.values() if att.is_correct)
    total_pts = sum(att.points_earned or 0 for att in best_by_progress.values() if att.is_correct)

    sub.status = SubmissionStatus.SUBMITTED.value
    sub.submitted_at = datetime.now(timezone.utc)
    sub.completed_puzzles = solved_count
    sub.total_points = total_pts
    sub.version = (sub.version or 1) + 1

    await db.flush()
    await db.refresh(sub)
    return sub


async def reopen_assignment(
    db: AsyncSession,
    assignment_id: uuid.UUID,
    student_id: uuid.UUID,
    teacher_id: uuid.UUID,
    reason: str,
) -> AssignmentSubmission:
    latest = await get_latest_submission(db, assignment_id, student_id)
    if latest and latest.status in (
        SubmissionStatus.REOPENED.value,
        SubmissionStatus.IN_PROGRESS.value,
    ):
        latest.reopened_at = datetime.now(timezone.utc)
        latest.reopened_by = teacher_id
        latest.reopen_reason = reason
        await db.flush()
        await db.refresh(latest)
        return latest

    next_attempt_no = (latest.attempt_no + 1) if latest else 1

    new_sub = AssignmentSubmission(
        assignment_id=assignment_id,
        student_id=student_id,
        attempt_no=next_attempt_no,
        version=1,
        status=SubmissionStatus.REOPENED.value,
        reopened_at=datetime.now(timezone.utc),
        reopened_by=teacher_id,
        reopen_reason=reason,
        completed_puzzles=0,
        total_points=0,
    )
    db.add(new_sub)
    await db.flush()
    await db.refresh(new_sub)
    return new_sub


async def is_assignment_locked_for_student(
    db: AsyncSession,
    assignment_id: uuid.UUID,
    student_id: uuid.UUID,
) -> bool:
    sub = await get_latest_submission(db, assignment_id, student_id)
    if not sub:
        return False
    return sub.status in (
        SubmissionStatus.SUBMITTED.value,
        SubmissionStatus.GRADED.value,
        SubmissionStatus.RETURNED.value,
    )


async def grade_and_return_assignment(
    db: AsyncSession,
    assignment_id: uuid.UUID,
    student_id: uuid.UUID,
    teacher_id: uuid.UUID,
    teacher_feedback: str | None = None,
    teacher_adjustment: int = 0,
    expected_version: int | None = None,
    attempt_no: int | None = None,
) -> AssignmentSubmission:
    stmt = (
        select(AssignmentSubmission)
        .where(
            AssignmentSubmission.assignment_id == assignment_id,
            AssignmentSubmission.student_id == student_id,
        )
        .with_for_update()
    )
    if attempt_no is not None:
        stmt = stmt.where(AssignmentSubmission.attempt_no == attempt_no)
    else:
        stmt = stmt.order_by(desc(AssignmentSubmission.attempt_no))

    res = await db.execute(stmt)
    sub = res.scalars().first()
    if not sub:
        raise HTTPException(status_code=404, detail="Không tìm thấy bài nộp")

    if sub.status not in (
        SubmissionStatus.SUBMITTED.value,
        SubmissionStatus.GRADED.value,
        SubmissionStatus.RETURNED.value,
    ):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Không thể chấm hoặc trả bài khi học sinh chưa nộp bài (trạng thái hiện tại: '{sub.status}').",
        )

    if expected_version is not None and sub.version != expected_version:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Dữ liệu bài tập đã được cập nhật bởi thao tác khác. Vui lòng tải lại trang.",
        )

    sub.teacher_feedback = teacher_feedback
    sub.teacher_adjustment = teacher_adjustment or 0
    sub.graded_by = teacher_id
    sub.graded_at = datetime.now(timezone.utc)
    sub.status = SubmissionStatus.RETURNED.value
    sub.version = (sub.version or 1) + 1
    if teacher_adjustment:
        sub.total_points = max(0, sub.total_points + teacher_adjustment)

    # Cập nhật điểm chính thức vào StudentProgress tương ứng để tính vào leaderboard
    att_stmt = select(StudentAttempt).where(StudentAttempt.submission_id == sub.id)
    att_res = await db.execute(att_stmt)
    sub_attempts = att_res.scalars().all()
    for att in sub_attempts:
        p_stmt = select(StudentProgress).where(StudentProgress.id == att.progress_id)
        p_res = await db.execute(p_stmt)
        prog = p_res.scalar_one_or_none()
        if prog:
            if att.is_correct:
                prog.status = ProgressStatus.SOLVED.value
                prog.points_earned = att.points_earned
            prog.graded_at = datetime.now(timezone.utc)
            prog.graded_by = teacher_id
            prog.teacher_feedback = teacher_feedback

    await db.flush()
    await db.refresh(sub)
    return sub


async def get_student_submission_detail(
    db: AsyncSession,
    assignment_id: uuid.UUID,
    student_id: uuid.UUID,
    attempt_no: Optional[int] = None,
    is_teacher_or_admin: bool = False,
) -> dict:
    if attempt_no is not None:
        sub = await get_submission_by_attempt(db, assignment_id, student_id, attempt_no)
    else:
        sub = await get_latest_submission(db, assignment_id, student_id)

    if not sub:
        sub = await get_or_create_submission(db, assignment_id, student_id)

    # Lấy toàn bộ lịch sử các submissions
    all_subs = await get_student_submissions(db, assignment_id, student_id)
    history = [
        {
            "attempt_no": s.attempt_no,
            "status": s.status,
            "total_points": s.total_points,
            "completed_puzzles": s.completed_puzzles,
            "submitted_at": s.submitted_at.isoformat() if s.submitted_at else None,
            "graded_at": s.graded_at.isoformat() if s.graded_at else None,
            "version": s.version,
            "teacher_feedback": s.teacher_feedback,
            "teacher_adjustment": s.teacher_adjustment,
            "reopened_at": s.reopened_at.isoformat() if s.reopened_at else None,
            "reopen_reason": s.reopen_reason,
        }
        for s in all_subs
    ]

    puzzles = await get_assignment_puzzles(db, assignment_id)

    # Lấy các StudentAttempt gắn chặt với submission này
    att_stmt = (
        select(StudentAttempt)
        .where(StudentAttempt.submission_id == sub.id)
        .order_by(StudentAttempt.attempt_no)
    )
    att_res = await db.execute(att_stmt)
    sub_attempts = att_res.scalars().all()

    # Map progress
    prog_stmt = select(StudentProgress).where(
        StudentProgress.assignment_id == assignment_id,
        StudentProgress.student_id == student_id,
    )
    p_res = await db.execute(prog_stmt)
    progs = {p.puzzle_id: p for p in p_res.scalars().all()}

    prog_id_to_puzzle_id = {p.id: p.puzzle_id for p in progs.values()}
    attempts_by_puzzle: dict[uuid.UUID, list[StudentAttempt]] = {}
    for att in sub_attempts:
        puz_id = prog_id_to_puzzle_id.get(att.progress_id)
        if puz_id:
            attempts_by_puzzle.setdefault(puz_id, []).append(att)

    is_unsubmitted = sub.status in (
        SubmissionStatus.REOPENED.value,
        SubmissionStatus.IN_PROGRESS.value,
    )
    can_grade = (not is_unsubmitted) and (
        sub.status in (SubmissionStatus.SUBMITTED.value, SubmissionStatus.GRADED.value)
    )

    items = []
    for puz in puzzles:
        puz_attempts = attempts_by_puzzle.get(puz.id, [])
        prog = progs.get(puz.id)

        attempts_list = []
        for att in puz_attempts:
            if is_unsubmitted and not is_teacher_or_admin:
                attempts_list.append({
                    "attempt_no": att.attempt_no,
                    "moves_san": att.moves_san or [],
                    "moves_uci": att.moves_uci or [],
                    "is_correct": None,
                    "hint_used": att.hint_used,
                    "points_earned": 0,
                })
            else:
                attempts_list.append({
                    "attempt_no": att.attempt_no,
                    "moves_san": att.moves_san or [],
                    "moves_uci": att.moves_uci or [],
                    "is_correct": att.is_correct,
                    "hint_used": att.hint_used,
                    "points_earned": att.points_earned if not is_unsubmitted else 0,
                })

        if is_unsubmitted and not is_teacher_or_admin:
            model_solutions = []
        else:
            sorted_sols = sorted(puz.solutions, key=lambda s: s.move_order) if puz.solutions else []
            model_solutions = [
                {
                    "move_order": s.move_order,
                    "move_san": s.move_san,
                    "move_uci": s.move_uci,
                    "is_best_move": s.is_best_move,
                }
                for s in sorted_sols
            ]

        is_solved = any(a.is_correct for a in puz_attempts) if not (is_unsubmitted and not is_teacher_or_admin) else False
        p_earned = sum(a.points_earned for a in puz_attempts if a.is_correct) if not is_unsubmitted else 0

        items.append({
            "puzzle_id": str(puz.id),
            "title": puz.title,
            "fen": puz.fen,
            "difficulty": puz.difficulty,
            "puzzle_type": puz.puzzle_type,
            "rating": puz.rating,
            "solution_tree": puz.solution_tree if (not is_unsubmitted or is_teacher_or_admin) else None,
            "model_solutions": model_solutions,
            "status": "completed" if is_solved else ("in_progress" if puz_attempts else "not_started"),
            "is_solved": is_solved,
            "attempts_count": len(puz_attempts),
            "points_earned": p_earned,
            "hints_used": sum(1 for a in puz_attempts if a.hint_used),
            "time_spent_seconds": prog.time_spent_seconds if prog else 0,
            "last_attempt": attempts_list[-1] if attempts_list else None,
            "all_attempts": attempts_list,
        })

    # Tìm previous_submission nếu có
    prev_sub = None
    for s in all_subs:
        if s.attempt_no < sub.attempt_no and s.status in (
            SubmissionStatus.SUBMITTED.value,
            SubmissionStatus.GRADED.value,
            SubmissionStatus.RETURNED.value,
        ):
            prev_sub = {
                "attempt_no": s.attempt_no,
                "status": s.status,
                "total_points": s.total_points,
                "completed_puzzles": s.completed_puzzles,
                "teacher_feedback": s.teacher_feedback,
                "graded_at": s.graded_at.isoformat() if s.graded_at else None,
                "submitted_at": s.submitted_at.isoformat() if s.submitted_at else None,
            }
            break

    sub_dict = {
        "id": str(sub.id),
        "assignment_id": str(sub.assignment_id),
        "student_id": str(sub.student_id),
        "attempt_no": sub.attempt_no,
        "version": sub.version,
        "status": sub.status,
        "submitted_at": sub.submitted_at.isoformat() if sub.submitted_at else None,
        "total_points": sub.total_points if not is_unsubmitted else 0,
        "completed_puzzles": sub.completed_puzzles if not is_unsubmitted else 0,
        "teacher_feedback": sub.teacher_feedback if not is_unsubmitted else None,
        "graded_at": sub.graded_at.isoformat() if sub.graded_at else None,
        "teacher_adjustment": sub.teacher_adjustment,
        "reopened_at": sub.reopened_at.isoformat() if sub.reopened_at else None,
        "reopen_reason": sub.reopen_reason,
        "can_grade": can_grade,
    }

    return {
        "submission": sub_dict,
        "history": history,
        "previous_submission": prev_sub,
        "items": items,
    }


async def get_assignment_puzzles(
    db: AsyncSession,
    assignment_id: uuid.UUID,
) -> list[Puzzle]:
    """
    Lấy danh sách các thế cờ thuộc bài tập theo đúng thứ tự teacher đã gán.
    Không lọc theo solution_verified vì các thế cờ này đã được giáo viên chọn lọc và giao bài.
    """
    assignment = await get_assignment(db, assignment_id)
    if not assignment or not assignment.puzzle_ids:
        return []

    stmt = (
        select(Puzzle)
        .options(selectinload(Puzzle.solutions))
        .where(Puzzle.id.in_(assignment.puzzle_ids))
    )
    res = await db.execute(stmt)
    puzzles_dict = {p.id: p for p in res.scalars().all()}

    # Bảo toàn đúng thứ tự giáo viên đã gán trong puzzle_ids
    return [
        puzzles_dict[pid]
        for pid in assignment.puzzle_ids
        if pid in puzzles_dict
    ]



