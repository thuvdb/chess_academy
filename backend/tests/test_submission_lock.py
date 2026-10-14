"""
Unit test for Assignment Submission Lock & Reopen flow.
"""
import asyncio
import os
import sys
import uuid
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import select

from app.core.database import async_session_factory
from app.models.assignment import Assignment, AssignmentSubmission
from app.models.base import SubmissionStatus
from app.models.class_ import Class
from app.models.progress import StudentAttempt, StudentProgress
from app.models.puzzle import Puzzle
from app.models.user import User
from app.schemas.progress import StudentAttemptCreate
from app.services import assignment_service, progress_service


async def run_test():
    print("============================================================")
    print("TEST: Assignment Submission Lock & Reopen")
    print("============================================================")

    async with async_session_factory() as db:
        # 1. Fetch teacher & student
        teacher = (await db.execute(select(User).where(User.role == "teacher"))).scalars().first()
        student = (await db.execute(select(User).where(User.role == "student"))).scalars().first()
        puzzle = (await db.execute(select(Puzzle))).scalars().first()
        class_obj = (await db.execute(select(Class))).scalars().first()

        assert teacher and student and puzzle and class_obj, "Missing seed data"

        # 2. Create test assignment
        assignment = Assignment(
            class_id=class_obj.id,
            teacher_id=teacher.id,
            title="Test Lock Assignment " + str(uuid.uuid4())[:8],
            puzzle_ids=[puzzle.id],
        )
        db.add(assignment)
        await db.commit()
        await db.refresh(assignment)

        # 3. Student makes an attempt when in_progress -> should succeed
        attempt_in = StudentAttemptCreate(
            puzzle_id=puzzle.id,
            assignment_id=assignment.id,
            moves_uci=["e2e4"],
            time_spent_seconds=10,
        )
        prog, att = await progress_service.submit_attempt(db, student.id, attempt_in)
        await db.commit()
        print("  [PASS] Student can submit attempt when assignment is open")

        # 4. Student submits assignment -> lock
        sub = await assignment_service.submit_assignment(db, assignment.id, student.id)
        await db.commit()
        assert sub.status == SubmissionStatus.SUBMITTED.value
        assert sub.submitted_at is not None
        print(f"  [PASS] Assignment submitted successfully (status={sub.status})")

        # 5. Student tries to make another attempt -> MUST BE BLOCKED
        blocked = False
        try:
            await progress_service.submit_attempt(db, student.id, attempt_in)
        except ValueError as exc:
            if "khóa" in str(exc):
                blocked = True
        assert blocked, "Attempt should be blocked when assignment is submitted"
        print("  [PASS] Server-side lock actively blocks new attempt with ValueError")

        # 6. Teacher reopens assignment -> status must be REOPENED (Rule 1)
        reopened = await assignment_service.reopen_assignment(
            db, assignment.id, student.id, teacher.id, reason="Em xin làm lại do bấm nhầm"
        )
        await db.commit()
        assert reopened.status == SubmissionStatus.REOPENED.value
        assert reopened.attempt_no == 2
        assert reopened.reopened_by == teacher.id
        assert reopened.reopen_reason == "Em xin làm lại do bấm nhầm"
        print("  [PASS] Teacher can reopen assignment with audit reason (status=reopened, attempt_no=2)")

        # 7. Student can submit attempt again after reopen -> transitions to IN_PROGRESS
        prog2, att2 = await progress_service.submit_attempt(db, student.id, attempt_in)
        await db.commit()
        await db.refresh(reopened)
        assert att2 is not None
        assert reopened.status == SubmissionStatus.IN_PROGRESS.value
        print("  [PASS] Student can submit attempt again after assignment is reopened (status=in_progress)")

        # Cleanup test assignment data
        await db.execute(select(StudentAttempt).join(StudentProgress).where(StudentProgress.assignment_id == assignment.id))
        from sqlalchemy import delete
        await db.execute(delete(StudentAttempt).where(StudentAttempt.progress_id.in_(
            select(StudentProgress.id).where(StudentProgress.assignment_id == assignment.id)
        )))
        await db.execute(delete(StudentProgress).where(StudentProgress.assignment_id == assignment.id))
        await db.execute(delete(AssignmentSubmission).where(AssignmentSubmission.assignment_id == assignment.id))
        await db.delete(assignment)
        await db.commit()
        print("============================================================")
        print("ALL SUBMISSION LOCK TESTS PASSED!")
        print("============================================================")


if __name__ == "__main__":
    asyncio.run(run_test())
