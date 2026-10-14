"""
Progress & Attempts Service — Sprint 4
Handles student puzzle attempts, automated AI grading, manual teacher grading, and leaderboard.
"""

from datetime import datetime, timezone
import logging
import uuid
from typing import Optional

import chess
from sqlalchemy import desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.assignment import Assignment
from app.models.base import GradingMethod, ProgressStatus
from app.models.progress import StudentAttempt, StudentProgress
from app.models.puzzle import Puzzle, PuzzleSolution
from app.models.user import User
from app.schemas.progress import (
    LeaderboardEntry,
    StudentAttemptCreate,
    TeacherGradingRequest,
)
from app.services import mate_solver
from app.services.puzzle_service import calculate_new_puzzle_rating

logger = logging.getLogger(__name__)


# ── Chấm lời giải ────────────────────────────────────────────

def split_sides(fen: str, moves_uci: list[str]) -> tuple[list[str], list[str]]:
    """
    Tách một dãy nước trộn lẫn thành (nước của bên đi trong FEN, nước đối phương).

    Dùng cho client cũ chỉ gửi một mảng chung. Lượt được suy từ bàn cờ thật chứ
    không từ chỉ số chẵn/lẻ, nên dãy có nước không hợp lệ cũng không làm lệch bên.
    """
    player: list[str] = []
    opponent: list[str] = []
    try:
        board = chess.Board(fen)
    except ValueError:
        return [m.lower() for m in moves_uci], []

    attacker = board.turn
    for raw in moves_uci:
        token = (raw or "").strip().lower()
        if not token:
            continue
        try:
            move = chess.Move.from_uci(token)
        except ValueError:
            break
        if move not in board.legal_moves:
            break
        (player if board.turn == attacker else opponent).append(token)
        board.push(move)
    return player, opponent


def _grade_attempt(puzzle: Puzzle, attempt_in: StudentAttemptCreate) -> bool:
    """
    Chấm một lượt thử.

    Bài đã chứng minh được mate: CÂY BIẾN THỂ là thẩm quyền duy nhất. Cây chứa
    mọi nước ép được mate ở mỗi nút nên học sinh đi biến thể khác main line vẫn
    được nhận, không cần engine đoán thêm.

    Bài chưa chứng minh (chiến thuật thắng quân, bài cũ): giữ fallback Stockfish.
    """
    player_ucis = attempt_in.player_moves_uci
    if player_ucis is None:
        player_ucis, _ = split_sides(puzzle.fen, attempt_in.moves_uci)
    player_ucis = [m.lower() for m in player_ucis if (m or "").strip()]

    if puzzle.solution_tree and puzzle.solution_verified:
        solved, matched = mate_solver.grade_against_tree(puzzle.solution_tree, player_ucis)
        logger.info(
            "Chấm theo cây cho puzzle %s: solved=%s matched=%d/%s",
            puzzle.id, solved, matched, puzzle.mate_in,
        )
        return solved

    # ── Bài chưa chứng minh ──
    user_ucis = [m.lower() for m in attempt_in.moves_uci if (m or "").strip()]
    if not user_ucis:
        return False

    sorted_solutions = sorted(puzzle.solutions, key=lambda s: s.move_order)
    expected_ucis = [s.move_uci.lower() for s in sorted_solutions if s.is_best_move]
    if expected_ucis and len(user_ucis) >= len(expected_ucis):
        if user_ucis[:len(expected_ucis)] == expected_ucis:
            return True

    # Chiếu hết thật thì luôn được nhận, không cần engine
    try:
        board = chess.Board(puzzle.fen)
        for token in user_ucis:
            move = chess.Move.from_uci(token)
            if move not in board.legal_moves:
                board = None
                break
            board.push(move)
        if board is not None and board.is_checkmate():
            return True
    except ValueError:
        pass

    # Bài mate thì chỉ mate mới tính — lợi thế quân không phải lời giải
    if puzzle.mate_in or (puzzle.puzzle_type or "").startswith("mate_in_"):
        return False

    from app.services.stockfish_service import evaluate_alternate_solution
    return evaluate_alternate_solution(puzzle.fen, user_ucis)


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
    else:
        stmt = stmt.where(StudentProgress.assignment_id.is_(None))

    res = await db.execute(stmt)
    progress = res.scalars().first()

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

    # 1.5. Check if assignment is submitted and locked, and link to active submission
    submission_id = None
    if attempt_in.assignment_id:
        from app.models.base import SubmissionStatus
        from app.services.assignment_service import (
            get_or_create_submission,
            is_assignment_locked_for_student,
        )
        if await is_assignment_locked_for_student(db, attempt_in.assignment_id, student_id):
            raise ValueError("Bài tập đã được nộp và khóa, không thể làm lại trừ khi được giáo viên mở lại.")

        sub = await get_or_create_submission(db, attempt_in.assignment_id, student_id)
        # Chuyển trạng thái reopened -> in_progress khi học sinh đi nước đầu tiên của lần làm lại
        if sub.status == SubmissionStatus.REOPENED.value:
            sub.status = SubmissionStatus.IN_PROGRESS.value
            await db.flush()
        submission_id = sub.id

    # 2. Get student progress
    progress = await get_or_create_progress(
        db, student_id, attempt_in.puzzle_id, attempt_in.assignment_id
    )

    # 3. Check solution
    is_correct = _grade_attempt(puzzle, attempt_in)

    # 4. Create attempt record
    attempt_no = progress.attempts + 1
    progress.attempts = attempt_no
    progress.time_spent_seconds += attempt_in.time_spent_seconds
    if attempt_in.hint_used:
        progress.hints_used += 1

    points = 0
    now = datetime.now(timezone.utc)

    # Check assignment due date & overdue status
    is_overdue = False
    if attempt_in.assignment_id:
        asm_stmt = select(Assignment).where(Assignment.id == attempt_in.assignment_id)
        asm_res = await db.execute(asm_stmt)
        assignment = asm_res.scalar_one_or_none()
        if assignment and assignment.due_date:
            due = assignment.due_date
            if due.tzinfo is None:
                due = due.replace(tzinfo=timezone.utc)
            if now > due:
                is_overdue = True

    was_already_solved = (progress.status == ProgressStatus.SOLVED.value)

    if is_correct:
        if not is_overdue:
            base_points = max(10, puzzle.rating // 100)
            penalty = 5 if attempt_in.hint_used else 0
            points = max(5, base_points - penalty)
        else:
            # Overdue practice: 0 points toward homework leaderboard
            points = 0

        # Nếu là Luyện tập tự do (không phải BTVN): tính điểm ngay và update ELO
        if not attempt_in.assignment_id:
            progress.status = ProgressStatus.SOLVED.value
            if not was_already_solved:
                progress.points_earned = points
            else:
                progress.points_earned = max(progress.points_earned, points)
            progress.grading_method = GradingMethod.AUTO_AI.value
            progress.solved_at = now

            # Update puzzle rating & student rating on first solve
            if not was_already_solved:
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
        else:
            # Nếu là BTVN: Trạng thái progress giữ in_progress trong lúc làm bài,
            # điểm tích lũy chính thức chỉ cập nhật khi nộp bài / trả bài để tránh lệch điểm và bảo mật
            progress.status = ProgressStatus.IN_PROGRESS.value

        # Update puzzle play count
        puzzle.play_count += 1
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
        submission_id=submission_id,
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
    progress.status = ProgressStatus.SOLVED.value

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
