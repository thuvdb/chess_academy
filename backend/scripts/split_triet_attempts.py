"""
Script to safely separate Nguyen Minh Triet's assignment data into Attempt 1 and Attempt 2.
Includes dry-run and backup functionality.
"""
import asyncio
import json
import os
import uuid
from datetime import datetime, timezone
from sqlalchemy import select, update
from app.core.database import async_session_factory
from app.models.assignment import Assignment, AssignmentSubmission
from app.models.progress import StudentProgress, StudentAttempt

BACKUP_DIR = "/app/archive/backups"
ASSIGNMENT_ID = uuid.UUID("06369618-7d0d-4cfe-b5ba-722437aeeca4")
STUDENT_ID = uuid.UUID("b3fd71ef-81d9-4f17-b21b-e2c63a6c284e")
SPLIT_TIMESTAMP = datetime.fromisoformat("2026-10-13T10:01:04+00:00")


async def run_migration(dry_run: bool = True):
    print(f"=== SCRIPT TÁCH DỮ LIỆU ATTEMPT: Nguyễn Minh Triết (dry_run={dry_run}) ===")
    os.makedirs(BACKUP_DIR, exist_ok=True)
    backup_file = os.path.join(BACKUP_DIR, f"backup_triet_attempts_{int(datetime.now().timestamp())}.json")

    async with async_session_factory() as db:
        # 1. Fetch current submission
        sub_stmt = select(AssignmentSubmission).where(
            AssignmentSubmission.assignment_id == ASSIGNMENT_ID,
            AssignmentSubmission.student_id == STUDENT_ID,
        )
        res = await db.execute(sub_stmt)
        submissions = res.scalars().all()
        if not submissions:
            print("Không tìm thấy submission của Minh Triết!")
            return

        sub1 = submissions[0]
        print(f"Submission hiện tại: ID={sub1.id}, attempt_no={sub1.attempt_no}, status={sub1.status}, pts={sub1.total_points}")

        # 2. Fetch progress and attempts
        prog_stmt = select(StudentProgress).where(
            StudentProgress.assignment_id == ASSIGNMENT_ID,
            StudentProgress.student_id == STUDENT_ID,
        )
        p_res = await db.execute(prog_stmt)
        progs = p_res.scalars().all()

        backup_data = {
            "submissions": [
                {
                    "id": str(s.id),
                    "assignment_id": str(s.assignment_id),
                    "student_id": str(s.student_id),
                    "attempt_no": s.attempt_no,
                    "version": s.version,
                    "status": s.status,
                    "total_points": s.total_points,
                    "completed_puzzles": s.completed_puzzles,
                    "teacher_feedback": s.teacher_feedback,
                    "teacher_adjustment": s.teacher_adjustment,
                    "submitted_at": s.submitted_at.isoformat() if s.submitted_at else None,
                    "graded_at": s.graded_at.isoformat() if s.graded_at else None,
                    "reopened_at": s.reopened_at.isoformat() if s.reopened_at else None,
                    "reopen_reason": s.reopen_reason,
                }
                for s in submissions
            ],
            "progress": [],
            "attempts": [],
        }

        attempts_list = []
        for p in progs:
            backup_data["progress"].append({
                "id": str(p.id),
                "puzzle_id": str(p.puzzle_id),
                "status": p.status,
                "points_earned": p.points_earned,
                "attempts": p.attempts,
            })
            att_stmt = select(StudentAttempt).where(StudentAttempt.progress_id == p.id)
            att_res = await db.execute(att_stmt)
            for a in att_res.scalars().all():
                attempts_list.append(a)
                backup_data["attempts"].append({
                    "id": str(a.id),
                    "progress_id": str(a.progress_id),
                    "attempt_no": a.attempt_no,
                    "moves_san": a.moves_san,
                    "is_correct": a.is_correct,
                    "points_earned": a.points_earned,
                    "completed_at": a.completed_at.isoformat() if a.completed_at else None,
                    "submission_id": str(a.submission_id) if a.submission_id else None,
                })

        # Save backup
        with open(backup_file, "w", encoding="utf-8") as f:
            json.dump(backup_data, f, ensure_ascii=False, indent=2)
        print(f"Đã sao lưu dữ liệu ra file: {backup_file}")

        # 3. Classify attempts
        att_batch1 = [a for a in attempts_list if a.completed_at and a.completed_at < SPLIT_TIMESTAMP]
        att_batch2 = [a for a in attempts_list if a.completed_at and a.completed_at >= SPLIT_TIMESTAMP]

        print(f"\nPhân loại lượt giải (StudentAttempts):")
        print(f"- Lần 1 (trước {SPLIT_TIMESTAMP}): {len(att_batch1)} lượt đi")
        print(f"- Lần 2 (từ {SPLIT_TIMESTAMP} trở đi): {len(att_batch2)} lượt đi")

        # 4. Plan separation
        # Attempt 1 (Returned, 11 pts)
        sub1_id = sub1.id
        # Attempt 2 (In_progress, unsubmitted)
        sub2_id = uuid.uuid4()

        print(f"\nKế hoạch cập nhật:")
        print(f"1. Cập nhật Submission Lần 1 (ID={sub1_id}):")
        print(f"   attempt_no = 1, status = 'returned', total_points = 11, completed_puzzles = 1")
        print(f"   Gán submission_id cho {len(att_batch1)} lượt đi của Lần 1.")

        print(f"2. Tạo mới Submission Lần 2 (ID={sub2_id}):")
        print(f"   attempt_no = 2, status = 'in_progress', total_points = 0, completed_puzzles = 0")
        print(f"   reopened_at = {sub1.reopened_at}, reopen_reason = '{sub1.reopen_reason}'")
        print(f"   submitted_at = None, graded_at = None, teacher_feedback = None")
        print(f"   Gán submission_id cho {len(att_batch2)} lượt đi của Lần 2.")

        if dry_run:
            print("\n[DRY-RUN HOÀN TẤT] Không có thay đổi nào được ghi vào cơ sở dữ liệu.")
            return

        # Execute updates
        # Update Sub 1
        sub1.attempt_no = 1
        sub1.status = "returned"
        sub1.total_points = 11
        sub1.completed_puzzles = 1
        sub1.version = 1

        for a in att_batch1:
            a.submission_id = sub1_id

        # Insert Sub 2
        sub2 = AssignmentSubmission(
            id=sub2_id,
            assignment_id=ASSIGNMENT_ID,
            student_id=STUDENT_ID,
            attempt_no=2,
            version=1,
            status="in_progress",
            total_points=0,
            completed_puzzles=0,
            reopened_at=sub1.reopened_at,
            reopened_by=sub1.reopened_by,
            reopen_reason=sub1.reopen_reason,
            submitted_at=None,
            graded_at=None,
            graded_by=None,
            teacher_feedback=None,
            teacher_adjustment=0,
        )
        db.add(sub2)

        for a in att_batch2:
            a.submission_id = sub2_id

        # Reset StudentProgress to reflect Lần 1 (since Lần 2 is still in_progress/unsubmitted)
        for p in progs:
            # find attempts of batch 1 for this progress
            p_batch1 = [a for a in att_batch1 if a.progress_id == p.id]
            if p_batch1:
                last_a = max(p_batch1, key=lambda x: x.attempt_no)
                if last_a.is_correct:
                    p.status = "solved"
                    p.points_earned = last_a.points_earned
                else:
                    p.status = "in_progress"
                    p.points_earned = 0
            else:
                p.status = "not_started"
                p.points_earned = 0

        await db.commit()
        print("\n🎉 [THÀNH CÔNG] Đã tách dữ liệu thành công vào cơ sở dữ liệu!")


if __name__ == "__main__":
    import sys
    dry_run = "--apply" not in sys.argv
    asyncio.run(run_migration(dry_run=dry_run))
