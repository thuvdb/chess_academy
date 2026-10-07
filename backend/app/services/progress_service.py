"""
Progress & Attempts Service — Sprint 4
Handles student puzzle attempts, automated AI grading, manual teacher grading, and leaderboard.
"""

from datetime import datetime, timezone
import logging
import uuid
from typing import Optional

from sqlalchemy import desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.base import GradingMethod, ProgressStatus
from app.models.progress import StudentAttempt, StudentProgress
from app.models.puzzle import Puzzle, PuzzleSolution
from app.models.user import User
from app.schemas.progress import (
    LeaderboardEntry,
    StudentAttemptCreate,
    TeacherGradingRequest,
)
from app.services.puzzle_service import calculate_new_puzzle_rating

logger = logging.getLogger(__name__)


async def get_or_create_progress(
    db: AsyncSession,
    student_id: uuid.UUID,
    puzzle_id: uuid.UUID,
    assignment_id: Optional[uuid.UUID] = None,
) -> StudentProgress:
    stmt = (
        select(StudentProgress)
        .options(selectinload(StudentProgress.attempt_details))
        .where(
            StudentProgress.student_id == student_id,
            StudentProgress.puzzle_id == puzzle_id,
        )
    )
    if assignment_id:
        stmt = stmt.where(StudentProgress.assignment_id == assignment_id)

    res = await db.execute(stmt)
    progress = res.scalar_one_or_none()

    if not progress:
        progress = StudentProgress(
            student_id=student_id,
            puzzle_id=puzzle_id,
            assignment_id=assignment_id,
            status=ProgressStatus.IN_PROGRESS.value,
            attempts=0,
            hints_used=0,
            time_spent_seconds=0,
            points_earned=0,
        )
        db.add(progress)
        await db.flush()
        await db.refresh(progress)

    return progress


async def submit_attempt(
    db: AsyncSession,
    student_id: uuid.UUID,
    attempt_in: StudentAttemptCreate,
) -> tuple[StudentProgress, StudentAttempt]:
    # 1. Fetch puzzle & solutions
    puzzle_stmt = (
        select(Puzzle)
        .options(selectinload(Puzzle.solutions))
        .where(Puzzle.id == attempt_in.puzzle_id)
    )
    res = await db.execute(puzzle_stmt)
    puzzle = res.scalar_one_or_none()
    if not puzzle:
        raise ValueError("Puzzle not found")

    # 2. Get student progress
    progress = await get_or_create_progress(
        db, student_id, attempt_in.puzzle_id, attempt_in.assignment_id
    )

    # 3. Check solution
    # Best moves ordered by move_order
    sorted_solutions = sorted(puzzle.solutions, key=lambda s: s.move_order)
    expected_ucis = [s.move_uci.lower() for s in sorted_solutions if s.is_best_move]
    user_ucis = [m.lower() for m in attempt_in.moves_uci]

    is_correct = False
    if expected_ucis and user_ucis:
        # Check if the sequence matches the expected sequence exactly
        if user_ucis[:len(expected_ucis)] == expected_ucis:
            is_correct = True
        else:
            # If not exact match, let Stockfish evaluate if it's still a winning move/mate
            from app.services.stockfish_service import evaluate_alternate_solution
            if evaluate_alternate_solution(puzzle.fen, user_ucis):
                is_correct = True
                
    elif not expected_ucis and user_ucis:
        # If no solutions specified in DB, accept first legal move
        is_correct = True

    # 4. Create attempt record
    attempt_no = progress.attempts + 1
    progress.attempts = attempt_no
    progress.time_spent_seconds += attempt_in.time_spent_seconds
    if attempt_in.hint_used:
        progress.hints_used += 1

    points = 0
    now = datetime.now(timezone.utc)

    if is_correct:
        # Full points (100 base or scaled by rating)
        base_points = max(10, puzzle.rating // 100)
        penalty = 5 if attempt_in.hint_used else 0
        points = max(5, base_points - penalty)

        progress.status = ProgressStatus.COMPLETED.value
        progress.points_earned += points
        progress.grading_method = GradingMethod.AUTO_AI.value
        progress.solved_at = now

        # Update puzzle rating & student rating
        student_stmt = select(User).where(User.id == student_id)
        s_res = await db.execute(student_stmt)
        student = s_res.scalar_one_or_none()
        if student:
            new_s_rating, new_p_rating = calculate_new_puzzle_rating(
                user_rating=student.elo_rating,
                puzzle_rating=puzzle.rating,
                solved=True,
            )
            student.elo_rating = new_s_rating
            puzzle.rating = new_p_rating

        # Update puzzle play count
        puzzle.play_count += 1
        # Success rate calculation
        if puzzle.play_count > 0:
            current_successes = round((puzzle.success_rate or 100) * (puzzle.play_count - 1) / 100) + 1
            puzzle.success_rate = min(100, round((current_successes / puzzle.play_count) * 100))

    else:
        # Failed attempt
        progress.status = ProgressStatus.IN_PROGRESS.value
        puzzle.play_count += 1
        if puzzle.play_count > 0:
            current_successes = round((puzzle.success_rate or 100) * (puzzle.play_count - 1) / 100)
            puzzle.success_rate = min(100, round((current_successes / puzzle.play_count) * 100))

    attempt = StudentAttempt(
        progress_id=progress.id,
        attempt_no=attempt_no,
        moves_uci=attempt_in.moves_uci,
        moves_san=attempt_in.moves_san,
        is_correct=is_correct,
        hint_used=attempt_in.hint_used,
        points_earned=points,
        result="solved" if is_correct else "failed",
        started_at=now,
        completed_at=now,
    )
    db.add(attempt)
    await db.flush()
    await db.refresh(progress)
    await db.refresh(attempt)

    return progress, attempt


async def grade_manually(
    db: AsyncSession,
    progress_id: uuid.UUID,
    teacher_id: uuid.UUID,
    grade_data: TeacherGradingRequest,
) -> StudentProgress:
    stmt = select(StudentProgress).where(StudentProgress.id == progress_id)
    res = await db.execute(stmt)
    progress = res.scalar_one_or_none()
    if not progress:
        raise ValueError("Student progress not found")

    progress.points_earned = grade_data.points_earned
    progress.teacher_feedback = grade_data.teacher_feedback
    progress.graded_by = teacher_id
    progress.grading_method = GradingMethod.MANUAL_TEACHER.value
    progress.graded_at = datetime.now(timezone.utc)
    progress.status = ProgressStatus.COMPLETED.value

    await db.flush()
    await db.refresh(progress)
    return progress


async def get_leaderboard(
    db: AsyncSession,
    center_id: Optional[uuid.UUID] = None,
    limit: int = 50,
) -> list[LeaderboardEntry]:
    # Query students sorted by rating or points
    stmt = (
        select(
            User.id.label("student_id"),
            User.full_name,
            User.avatar_url,
            User.elo_rating.label("rating"),
            func.coalesce(func.sum(StudentProgress.points_earned), 0).label("points"),
            func.count(StudentProgress.id).filter(
                StudentProgress.status == ProgressStatus.SOLVED.value
            ).label("puzzles_solved"),
        )
        .outerjoin(StudentProgress, StudentProgress.student_id == User.id)
        .where(User.role == "student")
        .group_by(User.id)
        .order_by(desc("points"), desc("rating"))
        .limit(limit)
    )

    if center_id:
        stmt = stmt.where(User.center_id == center_id)

    res = await db.execute(stmt)
    rows = res.all()

    return [
        LeaderboardEntry(
            student_id=row.student_id,
            full_name=row.full_name,
            avatar_url=row.avatar_url,
            rating=row.rating,
            puzzles_solved=row.puzzles_solved,
            points=row.points,
        )
        for row in rows
    ]
