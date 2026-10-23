"""
CAMS Integration Test Cleanup & Teardown Helper (BƯỚC 5)
--------------------------------------------------------
Cung cấp cơ chế quản lý vòng đời dữ liệu kiểm thử tự động:
1. Tiền tố nhận diện chuẩn hóa `qa_e2e_*`
2. Bộ theo dõi `TestDataTracker` tự động gom ID các thực thể sinh ra trong test
3. Cơ chế `teardown()` trong khối `finally` dọn dẹp sạch sẽ 100% dữ liệu thử nghiệm,
   kể cả khi test thất bại (Assert fail / Exception).
4. Sử dụng kết nối asyncpg độc lập, tránh xung đột connection pool giữa các event loops.
"""

import uuid
from typing import Any, Optional, Set
import asyncpg
from app.core.config import settings

QA_PREFIX = "qa_e2e"


def make_test_email(role: str = "user") -> str:
    """Tạo email với tiền tố test chuẩn hóa để nhận diện."""
    return f"{QA_PREFIX}_{role}_{uuid.uuid4().hex[:8]}@cams-qa.vn"



def make_test_center_name(tag: str = "center") -> str:
    """Tạo tên trung tâm test với tiền tố chuẩn hóa."""
    return f"QA E2E Center [{tag}_{uuid.uuid4().hex[:6]}]"


class TestDataTracker:
    """Bộ theo dõi và giải phóng dữ liệu test tự động."""

    def __init__(self):
        self.center_ids: Set[uuid.UUID] = set()
        self.user_ids: Set[uuid.UUID] = set()
        self.class_ids: Set[uuid.UUID] = set()
        self.tournament_ids: Set[uuid.UUID] = set()
        self.invoice_ids: Set[uuid.UUID] = set()
        self.fee_plan_ids: Set[uuid.UUID] = set()
        self.assignment_ids: Set[uuid.UUID] = set()
        self.scan_job_ids: Set[uuid.UUID] = set()

    def track_center(self, center_id: Any) -> uuid.UUID:
        uid = uuid.UUID(str(center_id)) if not isinstance(center_id, uuid.UUID) else center_id
        self.center_ids.add(uid)
        return uid

    def track_user(self, user_id: Any) -> uuid.UUID:
        uid = uuid.UUID(str(user_id)) if not isinstance(user_id, uuid.UUID) else user_id
        self.user_ids.add(uid)
        return uid

    def track_class(self, class_id: Any) -> uuid.UUID:
        uid = uuid.UUID(str(class_id)) if not isinstance(class_id, uuid.UUID) else class_id
        self.class_ids.add(uid)
        return uid

    def track_tournament(self, tournament_id: Any) -> uuid.UUID:
        uid = uuid.UUID(str(tournament_id)) if not isinstance(tournament_id, uuid.UUID) else tournament_id
        self.tournament_ids.add(uid)
        return uid

    def track_invoice(self, invoice_id: Any) -> uuid.UUID:
        uid = uuid.UUID(str(invoice_id)) if not isinstance(invoice_id, uuid.UUID) else invoice_id
        self.invoice_ids.add(uid)
        return uid

    def track_fee_plan(self, fee_plan_id: Any) -> uuid.UUID:
        uid = uuid.UUID(str(fee_plan_id)) if not isinstance(fee_plan_id, uuid.UUID) else fee_plan_id
        self.fee_plan_ids.add(uid)
        return uid

    def track_assignment(self, assignment_id: Any) -> uuid.UUID:
        uid = uuid.UUID(str(assignment_id)) if not isinstance(assignment_id, uuid.UUID) else assignment_id
        self.assignment_ids.add(uid)
        return uid

    def track_scan_job(self, scan_job_id: Any) -> uuid.UUID:
        uid = uuid.UUID(str(scan_job_id)) if not isinstance(scan_job_id, uuid.UUID) else scan_job_id
        self.scan_job_ids.add(uid)
        return uid

    async def teardown(self):
        """Xóa toàn bộ dữ liệu đã được theo dõi theo đúng trật tự khóa ngoại an toàn qua asyncpg."""
        print("\n[TEARDOWN] Bắt đầu dọn dẹp dữ liệu kiểm thử tự động...")
        db_url = str(settings.DATABASE_URL).replace("postgresql+asyncpg://", "postgresql://")
        conn = await asyncpg.connect(db_url)

        try:
            tr = conn.transaction()
            await tr.start()

            # 1. Scan results & jobs
            if self.scan_job_ids:
                j_ids = list(self.scan_job_ids)
                await conn.execute("DELETE FROM scan_results WHERE job_id = ANY($1);", j_ids)
                await conn.execute("DELETE FROM scan_jobs WHERE id = ANY($1);", j_ids)

            # 2. Payments & Invoices
            if self.invoice_ids:
                inv_ids = list(self.invoice_ids)
                await conn.execute("DELETE FROM payments WHERE invoice_id = ANY($1);", inv_ids)
                await conn.execute("DELETE FROM invoices WHERE id = ANY($1);", inv_ids)

            # 3. Fee plans
            if self.fee_plan_ids:
                fp_ids = list(self.fee_plan_ids)
                await conn.execute("DELETE FROM fee_plans WHERE id = ANY($1);", fp_ids)

            # 4. Tournament tables
            if self.tournament_ids or self.user_ids:
                t_ids = list(self.tournament_ids)
                u_ids = list(self.user_ids)
                await conn.execute("""
                    DELETE FROM tournament_games 
                    WHERE tournament_id = ANY($1) 
                       OR white_player_id = ANY($2) 
                       OR black_player_id = ANY($2);
                """, t_ids, u_ids)
                await conn.execute("""
                    DELETE FROM tournament_standings 
                    WHERE tournament_id = ANY($1) OR student_id = ANY($2);
                """, t_ids, u_ids)
                await conn.execute("""
                    DELETE FROM tournament_participants 
                    WHERE tournament_id = ANY($1) OR student_id = ANY($2);
                """, t_ids, u_ids)
                if t_ids:
                    await conn.execute("DELETE FROM tournaments WHERE id = ANY($1);", t_ids)

            # 5. Assignments, submissions & student attempts
            if self.assignment_ids or self.user_ids:
                a_ids = list(self.assignment_ids)
                u_ids = list(self.user_ids)
                await conn.execute("""
                    DELETE FROM student_attempts 
                    WHERE submission_id IN (
                        SELECT id FROM assignment_submissions 
                        WHERE student_id = ANY($1) OR assignment_id = ANY($2)
                    ) OR progress_id IN (
                        SELECT id FROM student_progress 
                        WHERE student_id = ANY($1) OR assignment_id = ANY($2)
                    );
                """, u_ids, a_ids)
                await conn.execute("""
                    DELETE FROM assignment_submissions 
                    WHERE student_id = ANY($1) OR assignment_id = ANY($2);
                """, u_ids, a_ids)
                await conn.execute("""
                    DELETE FROM student_progress 
                    WHERE student_id = ANY($1) OR assignment_id = ANY($2);
                """, u_ids, a_ids)
                if a_ids:
                    await conn.execute("DELETE FROM assignments WHERE id = ANY($1);", a_ids)

            # 6. Class enrollments & classes
            if self.class_ids or self.user_ids:
                c_ids = list(self.class_ids)
                u_ids = list(self.user_ids)
                await conn.execute("""
                    DELETE FROM class_enrollments 
                    WHERE class_id = ANY($1) OR student_id = ANY($2);
                """, c_ids, u_ids)
                if c_ids:
                    await conn.execute("DELETE FROM classes WHERE id = ANY($1);", c_ids)

            # 7. Parent-student, notifications, chat
            if self.user_ids:
                u_ids = list(self.user_ids)
                await conn.execute("""
                    DELETE FROM parent_student 
                    WHERE parent_id = ANY($1) OR student_id = ANY($1);
                """, u_ids)
                await conn.execute("DELETE FROM notifications WHERE user_id = ANY($1);", u_ids)
                await conn.execute("""
                    DELETE FROM chat_messages 
                    WHERE session_id IN (SELECT id FROM chat_sessions WHERE user_id = ANY($1));
                """, u_ids)
                await conn.execute("DELETE FROM ai_puzzle_attempts WHERE user_id = ANY($1);", u_ids)
                await conn.execute("DELETE FROM chat_sessions WHERE user_id = ANY($1);", u_ids)

            # 8. Users
            if self.user_ids:
                await conn.execute("DELETE FROM users WHERE id = ANY($1);", list(self.user_ids))

            # 9. Branches & Centers
            if self.center_ids:
                c_ids = list(self.center_ids)
                await conn.execute("DELETE FROM branches WHERE center_id = ANY($1);", c_ids)
                await conn.execute("DELETE FROM centers WHERE id = ANY($1);", c_ids)

            # 10. Fallback sweep: dọn dẹp sạch mọi bản ghi test mồ côi tiền tố qa_e2e_ (nếu có sót)
            await conn.execute("""
                DELETE FROM tournament_games WHERE tournament_id IN (SELECT id FROM tournaments WHERE created_by IN (SELECT id FROM users WHERE email LIKE 'qa_e2e_%'));
                DELETE FROM tournament_standings WHERE tournament_id IN (SELECT id FROM tournaments WHERE created_by IN (SELECT id FROM users WHERE email LIKE 'qa_e2e_%'));
                DELETE FROM tournament_participants WHERE tournament_id IN (SELECT id FROM tournaments WHERE created_by IN (SELECT id FROM users WHERE email LIKE 'qa_e2e_%'));
                DELETE FROM tournaments WHERE created_by IN (SELECT id FROM users WHERE email LIKE 'qa_e2e_%');
                DELETE FROM payments WHERE invoice_id IN (SELECT id FROM invoices WHERE student_id IN (SELECT id FROM users WHERE email LIKE 'qa_e2e_%'));
                DELETE FROM invoices WHERE student_id IN (SELECT id FROM users WHERE email LIKE 'qa_e2e_%');
                DELETE FROM fee_plans WHERE center_id IN (SELECT id FROM centers WHERE name LIKE 'QA E2E Center%');
                DELETE FROM class_enrollments WHERE student_id IN (SELECT id FROM users WHERE email LIKE 'qa_e2e_%');
                DELETE FROM classes WHERE center_id IN (SELECT id FROM centers WHERE name LIKE 'QA E2E Center%');
                DELETE FROM branches WHERE center_id IN (SELECT id FROM centers WHERE name LIKE 'QA E2E Center%');
                DELETE FROM users WHERE email LIKE 'qa_e2e_%';
                DELETE FROM centers WHERE name LIKE 'QA E2E Center%';
            """)

            await tr.commit()
            print("[TEARDOWN THÀNH CÔNG] Dữ liệu kiểm thử đã được dọn dẹp sạch sẽ 100%.")
        except Exception as e:
            await tr.rollback()
            print(f"[TEARDOWN LỖI] Không thể dọn dẹp dữ liệu test: {e}")
            raise
        finally:
            await conn.close()
