"""
Assignments API — Sprint 4
Endpoints for managing homework and class assignments.
"""

import uuid
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.deps import get_current_user
from app.core.database import get_db
from app.core.permissions import Role, assert_same_center, is_super_admin, require_roles
from app.models.assignment import Assignment, AssignmentSubmission, SubmissionStatus
from app.models.class_ import Class
from app.models.progress import StudentProgress
from app.models.user import User
from app.schemas.assignment import (
    AssignmentCreate,
    AssignmentGradeRequest,
    AssignmentRead,
    AssignmentReopenRequest,
    AssignmentSubmissionRead,
    AssignmentUpdate,
)
from app.schemas.puzzle import PuzzleRead
from app.services import assignment_service

router = APIRouter()


@router.get("", response_model=list[AssignmentRead])
async def list_assignments(
    class_id: Optional[uuid.UUID] = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    teacher_id = None
    if current_user.role == "teacher":
        teacher_id = current_user.id

    student_id = None
    if current_user.role == "student":
        student_id = current_user.id

    center_filter = None if is_super_admin(current_user) else current_user.center_id

    return await assignment_service.list_assignments(
        db=db,
        center_id=center_filter,
        class_id=class_id,
        teacher_id=teacher_id,
        student_id=student_id,
        skip=skip,
        limit=limit,
    )


@router.get("/{assignment_id}", response_model=AssignmentRead)
async def get_assignment(
    assignment_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    assignment = await assignment_service.get_assignment(db, assignment_id)
    if not assignment:
        raise HTTPException(status_code=404, detail="Assignment not found")
    if assignment.class_:
        assert_same_center(current_user, assignment.class_.center_id, detail="Assignment not found")
    return assignment


@router.get("/{assignment_id}/puzzles", response_model=list[PuzzleRead])
async def get_assignment_puzzles(
    assignment_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Lấy danh sách chi tiết các thế cờ của bài tập này theo đúng thứ tự.
    Áp dụng cho cả học sinh và giáo viên trong lớp (không lọc theo solution_verified).
    """
    assignment = await assignment_service.get_assignment(db, assignment_id)
    if not assignment:
        raise HTTPException(status_code=404, detail="Assignment not found")
    if assignment.class_:
        assert_same_center(current_user, assignment.class_.center_id, detail="Assignment not found")
    return await assignment_service.get_assignment_puzzles(db, assignment_id)


@router.post("", response_model=AssignmentRead, status_code=status.HTTP_201_CREATED)
async def create_assignment(
    data: AssignmentCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles(Role.SUPER_ADMIN, Role.CENTER_ADMIN, Role.TEACHER)),
):
    target_class = await db.get(Class, data.class_id)
    if not target_class:
        raise HTTPException(status_code=404, detail="Class not found")
    assert_same_center(current_user, target_class.center_id, detail="Class not found")

    assignment = await assignment_service.create_assignment(
        db=db,
        teacher_id=current_user.id,
        data=data,
    )
    await db.commit()
    return assignment


@router.put("/{assignment_id}", response_model=AssignmentRead)
async def update_assignment(
    assignment_id: uuid.UUID,
    data: AssignmentUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles(Role.SUPER_ADMIN, Role.CENTER_ADMIN, Role.TEACHER)),
):
    assignment = await assignment_service.get_assignment(db, assignment_id)
    if not assignment:
        raise HTTPException(status_code=404, detail="Assignment not found")

    if assignment.class_:
        assert_same_center(current_user, assignment.class_.center_id, detail="Assignment not found")

    # If teacher, must be the owner of the assignment
    if current_user.role == Role.TEACHER.value and assignment.teacher_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="You do not have permission to modify this assignment")

    updated = await assignment_service.update_assignment(db, assignment, data)
    await db.commit()
    return updated


@router.delete("/{assignment_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_assignment(
    assignment_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles(Role.SUPER_ADMIN, Role.CENTER_ADMIN, Role.TEACHER)),
):
    assignment = await assignment_service.get_assignment(db, assignment_id)
    if not assignment:
        raise HTTPException(status_code=404, detail="Assignment not found")

    if assignment.class_:
        assert_same_center(current_user, assignment.class_.center_id, detail="Assignment not found")

    if current_user.role == Role.TEACHER.value and assignment.teacher_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="You do not have permission to delete this assignment")

    await assignment_service.delete_assignment(db, assignment)
    await db.commit()


@router.get("/{assignment_id}/progress", response_model=list[dict])
async def get_assignment_progress(
    assignment_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    assignment = await assignment_service.get_assignment(db, assignment_id)
    if not assignment:
        raise HTTPException(status_code=404, detail="Assignment not found")
    if assignment.class_:
        assert_same_center(current_user, assignment.class_.center_id, detail="Assignment not found")

    stmt = (
        select(StudentProgress)
        .options(selectinload(StudentProgress.student))
        .where(StudentProgress.assignment_id == assignment_id)
    )

    if current_user.role == "student":
        stmt = stmt.where(StudentProgress.student_id == current_user.id)

    res = await db.execute(stmt)
    progress_records = res.scalars().all()

    # Load submissions to get official submission status for each student
    sub_stmt = (
        select(AssignmentSubmission)
        .where(AssignmentSubmission.assignment_id == assignment_id)
        .order_by(AssignmentSubmission.student_id, desc(AssignmentSubmission.attempt_no))
    )
    sub_res = await db.execute(sub_stmt)
    all_subs_list = sub_res.scalars().all()

    # Nhóm theo student_id: latest submission và all submissions
    latest_submissions: dict[uuid.UUID, AssignmentSubmission] = {}
    subs_by_student: dict[uuid.UUID, list[AssignmentSubmission]] = {}
    for s in all_subs_list:
        subs_by_student.setdefault(s.student_id, []).append(s)
        if s.student_id not in latest_submissions:
            latest_submissions[s.student_id] = s

    # Deduplicate in case of historical concurrent records per (student_id, puzzle_id)
    deduped: dict[tuple, dict] = {}
    for p in progress_records:
        key = (p.student_id, p.puzzle_id)
        sub = latest_submissions.get(p.student_id)
        is_unsubmitted = sub and sub.status in (
            SubmissionStatus.REOPENED.value,
            SubmissionStatus.IN_PROGRESS.value,
        )

        # Tìm previous_submission nếu học sinh đang ở attempt > 1
        prev_sub_info = None
        student_subs = subs_by_student.get(p.student_id, [])
        for ps in student_subs:
            if sub and ps.attempt_no < sub.attempt_no and ps.status in (
                SubmissionStatus.SUBMITTED.value,
                SubmissionStatus.GRADED.value,
                SubmissionStatus.RETURNED.value,
            ):
                prev_sub_info = {
                    "attempt_no": ps.attempt_no,
                    "status": ps.status,
                    "total_points": ps.total_points,
                    "completed_puzzles": ps.completed_puzzles,
                    "teacher_feedback": ps.teacher_feedback,
                    "submitted_at": ps.submitted_at.isoformat() if ps.submitted_at else None,
                    "graded_at": ps.graded_at.isoformat() if ps.graded_at else None,
                }
                break

        item = {
            "id": p.id,
            "student_id": p.student_id,
            "student_name": p.student.full_name if p.student else "Unknown",
            "puzzle_id": p.puzzle_id,
            "status": "in_progress" if is_unsubmitted else p.status,
            "attempts": p.attempts,
            "points_earned": 0 if is_unsubmitted else p.points_earned,
            "submission_id": str(sub.id) if sub else None,
            "attempt_no": sub.attempt_no if sub else 1,
            "submission_version": sub.version if sub else 1,
            "submission_status": sub.status if sub else "in_progress",
            "submission_total_points": sub.total_points if sub and not is_unsubmitted else 0,
            "can_grade": sub.status in (SubmissionStatus.SUBMITTED.value, SubmissionStatus.GRADED.value) if sub else False,
            "submitted_at": sub.submitted_at if sub else None,
            "reopened_at": sub.reopened_at if sub else None,
            "reopen_reason": sub.reopen_reason if sub else None,
            "previous_submission": prev_sub_info,
            "updated_at": p.updated_at,
        }
        if key not in deduped or item["points_earned"] > deduped[key]["points_earned"]:
            deduped[key] = item

    return list(deduped.values())


@router.get("/{assignment_id}/my-submission", response_model=AssignmentSubmissionRead)
async def get_my_submission(
    assignment_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Lấy trạng thái nộp bài của học sinh hiện tại (bao gồm lịch sử attempt và kết quả lần trước)."""
    assignment = await assignment_service.get_assignment(db, assignment_id)
    if not assignment:
        raise HTTPException(status_code=404, detail="Assignment not found")
    if assignment.class_:
        assert_same_center(current_user, assignment.class_.center_id, detail="Assignment not found")

    sub = await assignment_service.get_latest_submission(db, assignment_id, current_user.id)
    if not sub:
        sub = await assignment_service.get_or_create_submission(db, assignment_id, current_user.id)
        await db.commit()
        await db.refresh(sub)

    is_unsubmitted = sub.status in (
        SubmissionStatus.REOPENED.value,
        SubmissionStatus.IN_PROGRESS.value,
    )

    all_subs = await assignment_service.get_student_submissions(db, assignment_id, current_user.id)
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

    sub_read = AssignmentSubmissionRead.model_validate(sub)
    if is_unsubmitted:
        # Giấu điểm và nhận xét của lần đang làm lại
        sub_read.total_points = 0
        sub_read.teacher_feedback = None
    sub_read.previous_submission = prev_sub
    sub_read.can_grade = False
    return sub_read


@router.post("/{assignment_id}/submit", response_model=AssignmentSubmissionRead)
async def submit_assignment(
    assignment_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Học sinh nộp bài chính thức và khóa cứng việc chỉnh sửa."""
    assignment = await assignment_service.get_assignment(db, assignment_id)
    if not assignment:
        raise HTTPException(status_code=404, detail="Bài tập không tồn tại")
    if assignment.class_:
        assert_same_center(current_user, assignment.class_.center_id, detail="Bài tập không tồn tại")

    sub = await assignment_service.submit_assignment(db, assignment_id, current_user.id)
    await db.commit()
    await db.refresh(sub)
    return sub


@router.post("/{assignment_id}/reopen", response_model=AssignmentSubmissionRead)
async def reopen_assignment(
    assignment_id: uuid.UUID,
    body: AssignmentReopenRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles(Role.SUPER_ADMIN, Role.CENTER_ADMIN, Role.TEACHER)),
):
    """Giáo viên hoặc Admin mở lại bài cho học sinh kèm lý do (tạo attempt_no mới)."""
    assignment = await assignment_service.get_assignment(db, assignment_id)
    if not assignment:
        raise HTTPException(status_code=404, detail="Bài tập không tồn tại")
    if assignment.class_:
        assert_same_center(current_user, assignment.class_.center_id, detail="Bài tập không tồn tại")

    sub = await assignment_service.reopen_assignment(
        db=db,
        assignment_id=assignment_id,
        student_id=body.student_id,
        teacher_id=current_user.id,
        reason=body.reason,
    )
    await db.commit()
    await db.refresh(sub)
    return sub


@router.get("/{assignment_id}/submissions/{student_id}")
async def get_student_submission_detail(
    assignment_id: uuid.UUID,
    student_id: uuid.UUID,
    attempt_no: Optional[int] = Query(None, description="Lần nộp bài cần xem (mặc định lấy lần mới nhất)"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Xem chi tiết bài làm của học sinh (từng thế cờ, nước đi, đáp án mẫu).
    Giáo viên, Admin hoặc chính học sinh đó mới có quyền xem.
    """
    is_teacher = current_user.role in ("teacher", "admin", "center_admin", "super_admin")
    if not is_teacher and current_user.id != student_id:
        raise HTTPException(status_code=403, detail="Bạn không có quyền xem chi tiết bài làm này")

    assignment = await assignment_service.get_assignment(db, assignment_id)
    if not assignment:
        raise HTTPException(status_code=404, detail="Bài tập không tồn tại")
    if assignment.class_:
        assert_same_center(current_user, assignment.class_.center_id, detail="Bài tập không tồn tại")

    detail = await assignment_service.get_student_submission_detail(
        db=db,
        assignment_id=assignment_id,
        student_id=student_id,
        attempt_no=attempt_no,
        is_teacher_or_admin=is_teacher,
    )
    return detail


@router.post("/{assignment_id}/submissions/{student_id}/return", response_model=AssignmentSubmissionRead)
async def grade_and_return_submission(
    assignment_id: uuid.UUID,
    student_id: uuid.UUID,
    body: AssignmentGradeRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles(Role.SUPER_ADMIN, Role.CENTER_ADMIN, Role.TEACHER)),
):
    """
    Giáo viên/Admin chấm bài, ghi nhận xét, cộng/trừ điểm và trả bài cho học sinh.
    Kiểm tra trạng thái (409 Conflict nếu chưa nộp) và version (chống race condition).
    """
    assignment = await assignment_service.get_assignment(db, assignment_id)
    if not assignment:
        raise HTTPException(status_code=404, detail="Bài tập không tồn tại")
    if assignment.class_:
        assert_same_center(current_user, assignment.class_.center_id, detail="Bài tập không tồn tại")

    sub = await assignment_service.grade_and_return_assignment(
        db=db,
        assignment_id=assignment_id,
        student_id=student_id,
        teacher_id=current_user.id,
        teacher_feedback=body.teacher_feedback,
        teacher_adjustment=body.teacher_adjustment,
        expected_version=body.expected_version,
        attempt_no=body.attempt_no,
    )
    await db.commit()
    await db.refresh(sub)
    return sub



