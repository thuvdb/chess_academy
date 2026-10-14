"""
Automated Integration Tests for CAMS Homework Reopen Workflow, Unsubmitted Confidentiality,
Multi-Attempt Isolation, 409 Conflict Guard, and Score Divergence Fix.
"""
import asyncio
import os
import sys
import uuid
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi import HTTPException
from sqlalchemy import delete, select

from app.core.database import async_session_factory
from app.models.assignment import Assignment, AssignmentSubmission
from app.models.base import SubmissionStatus
from app.models.class_ import Class
from app.models.progress import StudentAttempt, StudentProgress
from app.models.puzzle import Puzzle
from app.models.user import User
from app.schemas.progress import StudentAttemptCreate
from app.services import assignment_service, progress_service


async def run_tests():
    print("================================================================================")
    print("STARTING TEST SUITE: Homework Reopen Workflow & Score Isolation")
    print("================================================================================")

    async with async_session_factory() as db:
        # Seed discovery
        teacher = (await db.execute(select(User).where(User.role == "teacher"))).scalars().first()
        student = (await db.execute(select(User).where(User.role == "student"))).scalars().first()
        puzzle = (await db.execute(select(Puzzle))).scalars().first()
        class_obj = (await db.execute(select(Class))).scalars().first()

        assert teacher and student and puzzle and class_obj, "Missing initial seed data"

        # Create fresh test assignment
        assignment = Assignment(
            class_id=class_obj.id,
            teacher_id=teacher.id,
            title="Auto Test Workflow " + str(uuid.uuid4())[:8],
            puzzle_ids=[puzzle.id],
        )
        db.add(assignment)
        await db.commit()
        await db.refresh(assignment)

        test_asm_id = assignment.id

        try:
            # ────────────────────────────────────────────────────────────────
            # BƯỚC KHỞI ĐẦU: Lần 1 học viên làm, nộp bài, giáo viên chấm & trả bài
            # ────────────────────────────────────────────────────────────────
            print("\n[PHASE 0] Initial Attempt 1: Do -> Submit -> Grade -> Return (Status: returned)")
            att_create = StudentAttemptCreate(
                puzzle_id=puzzle.id,
                assignment_id=test_asm_id,
                moves_uci=["e2e4"],
                moves_san=["e4"],
                time_spent_seconds=15,
            )
            prog1, att1 = await progress_service.submit_attempt(db, student.id, att_create)
            await db.commit()

            sub1 = await assignment_service.submit_assignment(db, test_asm_id, student.id)
            await db.commit()
            assert sub1.attempt_no == 1
            assert sub1.status == SubmissionStatus.SUBMITTED.value

            sub1_returned = await assignment_service.grade_and_return_assignment(
                db,
                test_asm_id,
                student.id,
                teacher.id,
                teacher_feedback="Bài làm lần 1 rất tốt",
                teacher_adjustment=1,
            )
            await db.commit()
            assert sub1_returned.status == SubmissionStatus.RETURNED.value
            sub1_points = sub1_returned.total_points
            print(f"  -> Attempt 1 hoàn tất: status={sub1_returned.status}, points={sub1_points}")

            # ────────────────────────────────────────────────────────────────
            # KỊCH BẢN 4: Ghi nước đi sau khi nộp/trả bài bị từ chối
            # ────────────────────────────────────────────────────────────────
            print("\n[KỊCH BẢN 4] Ghi nước đi sau khi nộp/trả bài bị từ chối")
            locked_error = False
            try:
                await progress_service.submit_attempt(db, student.id, att_create)
            except ValueError as ex:
                if "khóa" in str(ex):
                    locked_error = True
            assert locked_error, "Server phải từ chối ghi nước đi khi bài tập đang bị khóa"
            print("  [PASS] Kịch bản 4: Khi assignment đã trả/khóa, học viên không thể gửi attempt mới")

            # ────────────────────────────────────────────────────────────────
            # Mở lại bài tập (Tạo Attempt 2, status=reopened)
            # ────────────────────────────────────────────────────────────────
            print("\n[MỞ LẠI BÀI] Giáo viên mở lại bài cho học sinh")
            sub2 = await assignment_service.reopen_assignment(
                db, test_asm_id, student.id, teacher.id, reason="Cho phép sửa sai câu khó"
            )
            await db.commit()
            assert sub2.attempt_no == 2, f"Attempt no phải là 2, nhận được {sub2.attempt_no}"
            assert sub2.status == SubmissionStatus.REOPENED.value
            assert sub2.total_points == 0
            assert sub2.reopen_reason == "Cho phép sửa sai câu khó"
            print(f"  [PASS] Đã tạo Attempt 2: attempt_no={sub2.attempt_no}, status={sub2.status}")

            # Học viên thực hiện nước đi đầu tiên của lần 2 -> chuyển thành in_progress
            prog2, att2 = await progress_service.submit_attempt(db, student.id, att_create)
            await db.commit()
            await db.refresh(sub2)
            assert sub2.status == SubmissionStatus.IN_PROGRESS.value
            assert att2.submission_id == sub2.id, "StudentAttempt lần 2 phải gắn đúng submission_id của lần 2"
            print(f"  [PASS] Nước đi lần 2 chuyển trạng thái sang in_progress, submission_id khớp {sub2.id}")

            # ────────────────────────────────────────────────────────────────
            # KỊCH BẢN 1: Mở lại -> Làm bài chưa nộp -> API Giáo viên không có
            #             kết quả lần mới, chấm/trả bài trả 409 Conflict
            # ────────────────────────────────────────────────────────────────
            print("\n[KỊCH BẢN 1] Mở lại -> làm xong chưa nộp -> API giáo viên & 409 Conflict")
            detail_teacher = await assignment_service.get_student_submission_detail(
                db, test_asm_id, student.id, is_teacher_or_admin=True
            )
            sub_t = detail_teacher["submission"]
            assert sub_t["attempt_no"] == 2
            assert sub_t["status"] == "in_progress"
            assert sub_t["total_points"] == 0, "Điểm lần 2 chưa nộp phải là 0"
            assert sub_t["can_grade"] is False, "can_grade phải là False khi chưa nộp"

            # Thử chấm/trả bài khi chưa nộp -> PHẢI trả 409 Conflict
            conflict_caught = False
            try:
                await assignment_service.grade_and_return_assignment(
                    db,
                    test_asm_id,
                    student.id,
                    teacher.id,
                    teacher_feedback="Chấm sớm khi chưa nộp",
                )
            except HTTPException as http_ex:
                if http_ex.status_code == 409:
                    conflict_caught = True
            assert conflict_caught, "Phải quăng HTTPException 409 Conflict khi cố tình chấm/trả bài chưa nộp"
            print("  [PASS] Kịch bản 1: can_grade=False, điểm lần 2 bị cô lập, chấm bài trả 409 Conflict")

            # ────────────────────────────────────────────────────────────────
            # KỊCH BẢN 2: Mở lại -> API Học viên không chứa kết quả lần mới;
            #             trả về previous_submission của lần 1
            # ────────────────────────────────────────────────────────────────
            print("\n[KỊCH BẢN 2] API học viên bảo mật thông tin lần mới & xem kết quả lần cũ")
            detail_student = await assignment_service.get_student_submission_detail(
                db, test_asm_id, student.id, is_teacher_or_admin=False
            )
            sub_s = detail_student["submission"]
            assert sub_s["attempt_no"] == 2
            assert sub_s["total_points"] == 0
            assert sub_s["teacher_feedback"] is None
            assert sub_s["can_grade"] is False

            # Kiểm tra items của học viên: không có is_correct, model_solutions trống
            for itm in detail_student["items"]:
                assert itm["points_earned"] == 0
                assert itm["model_solutions"] == [], "Đáp án mẫu phải bị ẩn đối với học viên chưa nộp bài"
                for a in itm["all_attempts"]:
                    assert a["is_correct"] is None, "is_correct phải là None đối với học viên"

            # Phải có previous_submission là Lần 1 đã trả bài
            prev_sub = detail_student["previous_submission"]
            assert prev_sub is not None, "Phải trả về previous_submission"
            assert prev_sub["attempt_no"] == 1
            assert prev_sub["status"] == SubmissionStatus.RETURNED.value
            assert prev_sub["total_points"] == sub1_points
            print("  [PASS] Kịch bản 2: Học sinh không xem được kết quả/đáp án lần mới; thấy previous_submission Lần 1")

            # ────────────────────────────────────────────────────────────────
            # KỊCH BẢN 3: Học viên nộp lần 2 -> Mới chấm được -> Trả bài ->
            #             Điểm giáo viên và học viên khớp nhau
            # ────────────────────────────────────────────────────────────────
            print("\n[KỊCH BẢN 3] Học viên nộp lần 2 -> Giáo viên chấm & trả bài -> Khớp điểm 100%")
            # Học viên bấm nộp bài
            sub2_submitted = await assignment_service.submit_assignment(db, test_asm_id, student.id)
            await db.commit()
            assert sub2_submitted.attempt_no == 2
            assert sub2_submitted.status == SubmissionStatus.SUBMITTED.value

            # Lúc này giáo viên kiểm tra can_grade -> Phải là True
            detail_after_sub = await assignment_service.get_student_submission_detail(
                db, test_asm_id, student.id, is_teacher_or_admin=True
            )
            assert detail_after_sub["submission"]["can_grade"] is True

            # Giáo viên chấm và trả bài thành công
            sub2_returned = await assignment_service.grade_and_return_assignment(
                db,
                test_asm_id,
                student.id,
                teacher.id,
                teacher_feedback="Lần 2 làm rất tốt!",
                teacher_adjustment=2,
            )
            await db.commit()
            assert sub2_returned.status == SubmissionStatus.RETURNED.value

            # Kiểm tra điểm từ phía Giáo viên
            detail_teacher_final = await assignment_service.get_student_submission_detail(
                db, test_asm_id, student.id, is_teacher_or_admin=True
            )
            score_teacher = detail_teacher_final["submission"]["total_points"]

            # Kiểm tra điểm từ phía Học viên
            detail_student_final = await assignment_service.get_student_submission_detail(
                db, test_asm_id, student.id, is_teacher_or_admin=False
            )
            score_student = detail_student_final["submission"]["total_points"]

            assert score_teacher == score_student, f"Điểm lệch! Teacher={score_teacher}, Student={score_student}"
            assert score_teacher == sub2_returned.total_points
            print(f"  [PASS] Kịch bản 3: Điểm giáo viên ({score_teacher} pts) và học sinh ({score_student} pts) khớp 100%!")

            print("\n================================================================================")
            print("TẤT CẢ 4 KỊCH BẢN TEST BTVN ĐỀU PASS HOÀN TOÀN! 🎉")
            print("================================================================================")

        finally:
            # Dọn dẹp dữ liệu bài tập test
            await db.execute(delete(StudentAttempt).where(StudentAttempt.progress_id.in_(
                select(StudentProgress.id).where(StudentProgress.assignment_id == test_asm_id)
            )))
            await db.execute(delete(StudentProgress).where(StudentProgress.assignment_id == test_asm_id))
            await db.execute(delete(AssignmentSubmission).where(AssignmentSubmission.assignment_id == test_asm_id))
            await db.execute(delete(Assignment).where(Assignment.id == test_asm_id))
            await db.commit()


if __name__ == "__main__":
    asyncio.run(run_tests())
