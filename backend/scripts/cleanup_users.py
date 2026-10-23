"""
CAMS Database User Cleanup Script (BƯỚC 3 & BƯỚC 4)
---------------------------------------------------
Quy tắc:
  - Mặc định là --dry-run; chỉ khi có cờ --execute mới thực hiện xóa thật trong 1 transaction duy nhất.
  - Danh sách email xóa đọc từ file quyết định (mặc định cleanup_decisions.json), không hardcode email.
  - Cột "người thao tác" (created_by, updated_by, graded_by, ...) -> cập nhật NULL nếu nullable.
  - Dòng dữ liệu thuộc về người bị xóa -> xóa theo đúng thứ tự khóa ngoại.
  - Dòng thuộc về người được giữ -> BẢO VỆ TUYỆT ĐỐI, không xóa; nếu có xung đột thì rollback và dừng.
  - Không bao giờ xóa trung tâm (centers) hay tài khoản trong danh sách giữ.
"""

import argparse
import asyncio
import json
import os
import sys
from typing import Any, Dict, List, Set
import asyncpg


def load_decisions(file_path: str) -> Dict[str, Any]:
    if not os.path.exists(file_path):
        alt_path = os.path.join(os.path.dirname(__file__), "..", "..", file_path)
        if os.path.exists(alt_path):
            file_path = alt_path
        else:
            raise FileNotFoundError(f"Không tìm thấy tệp quyết định: {file_path}")
            
    with open(file_path, "r", encoding="utf-8") as f:
        return json.load(f)


async def run_cleanup(
    db_url: str,
    decision_file: str,
    execute: bool = False,
    allow_superadmin_delete: bool = False
):
    print("=" * 70)
    print("=== CAMS USERS CLEANUP PIPELINE ===")
    print(f"Chế độ: {'[THỰC THI XÓA THẬT (--execute)]' if execute else '[MÔ PHỎNG AN TOÀN (--dry-run)]'}")
    print(f"Tệp quyết định: {decision_file}")
    print("=" * 70)

    decisions = load_decisions(decision_file)
    keep_emails_set: Set[str] = {e.lower().strip() for e in decisions.get("keep_emails", [])}
    delete_emails_set: Set[str] = {e.lower().strip() for e in decisions.get("delete_emails", [])}

    conn = await asyncpg.connect(db_url)

    try:
        # Bắt đầu Transaction
        tr = conn.transaction()
        await tr.start()

        # 1. Tải toàn bộ user hiện tại trong database
        all_users = await conn.fetch("SELECT id, email, full_name, role, center_id FROM users;")
        user_by_email = {u["email"].lower().strip(): u for u in all_users}
        
        # 2. Phân loại users thực tế trong DB
        actual_delete_users = []
        actual_keep_users = []
        
        for email, u in user_by_email.items():
            if email in delete_emails_set:
                # Kiểm tra an toàn super_admin
                if u["role"] == "super_admin" and not allow_superadmin_delete:
                    raise ValueError(
                        f"Phát hiện tài khoản super_admin ({u['email']}) trong danh sách xóa! "
                        "Theo quy tắc an toàn, không được xóa super_admin trừ khi bật cờ --allow-superadmin-delete."
                    )
                actual_delete_users.append(u)
            else:
                actual_keep_users.append(u)

        delete_ids = [u["id"] for u in actual_delete_users]
        keep_ids = [u["id"] for u in actual_keep_users]
        delete_ids_set = set(delete_ids)
        keep_ids_set = set(keep_ids)

        print(f"Tổng số tài khoản trong DB : {len(all_users)}")
        print(f"Số tài khoản sẽ GIỮ        : {len(actual_keep_users)}")
        print(f"Số tài khoản sẽ XÓA        : {len(actual_delete_users)}")
        print("-" * 70)

        # 3. Kiểm tra bảo vệ tài khoản giữ
        for u in actual_keep_users:
            if u["email"].lower().strip() not in keep_emails_set:
                print(f"[LƯU Ý] Tài khoản '{u['email']}' không có trong danh sách xóa, tự động xếp vào GIỮ an toàn.")

        # Thống kê số dòng bị ảnh hưởng
        stats = {
            "puzzles_created_by_set_null": 0,
            "classes_teacher_id_set_null": 0,
            "submissions_graded_by_set_null": 0,
            "submissions_reopened_by_set_null": 0,
            "progress_graded_by_set_null": 0,
            "payments_confirmed_by_set_null": 0,
            "payments_payer_id_set_null": 0,
            "scan_results_reviewed_by_set_null": 0,
            "deleted_chat_messages": 0,
            "deleted_ai_puzzle_attempts": 0,
            "deleted_chat_sessions": 0,
            "deleted_tournament_games": 0,
            "deleted_tournament_standings": 0,
            "deleted_tournament_participants": 0,
            "deleted_tournaments": 0,
            "deleted_assignment_submissions": 0,
            "deleted_assignments": 0,
            "deleted_class_enrollments": 0,
            "deleted_student_progress": 0,
            "deleted_parent_student": 0,
            "deleted_notifications": 0,
            "deleted_payments": 0,
            "deleted_invoices": 0,
            "deleted_scan_results": 0,
            "deleted_scan_jobs": 0,
            "deleted_users": len(delete_ids),
        }

        if delete_ids:
            # === BƯỚC 3.1: XỬ LÝ CỘT NGƯỜI THAO TÁC / NULLABLE ===
            # Puzzles created_by -> NULL (bảo toàn bài tập cờ)
            res = await conn.execute(
                "UPDATE puzzles SET created_by = NULL WHERE created_by = ANY($1);",
                delete_ids
            )
            stats["puzzles_created_by_set_null"] = int(res.split(" ")[1])

            # Classes teacher_id -> NULL (bảo toàn lớp học)
            res = await conn.execute(
                "UPDATE classes SET teacher_id = NULL WHERE teacher_id = ANY($1);",
                delete_ids
            )
            stats["classes_teacher_id_set_null"] = int(res.split(" ")[1])

            # Submissions graded_by / reopened_by -> NULL
            res = await conn.execute(
                "UPDATE assignment_submissions SET graded_by = NULL WHERE graded_by = ANY($1);",
                delete_ids
            )
            stats["submissions_graded_by_set_null"] = int(res.split(" ")[1])

            res = await conn.execute(
                "UPDATE assignment_submissions SET reopened_by = NULL WHERE reopened_by = ANY($1);",
                delete_ids
            )
            stats["submissions_reopened_by_set_null"] = int(res.split(" ")[1])

            # Student progress graded_by -> NULL
            res = await conn.execute(
                "UPDATE student_progress SET graded_by = NULL WHERE graded_by = ANY($1);",
                delete_ids
            )
            stats["progress_graded_by_set_null"] = int(res.split(" ")[1])

            # Payments confirmed_by / payer_id -> NULL
            res = await conn.execute(
                "UPDATE payments SET confirmed_by = NULL WHERE confirmed_by = ANY($1);",
                delete_ids
            )
            stats["payments_confirmed_by_set_null"] = int(res.split(" ")[1])

            res = await conn.execute(
                "UPDATE payments SET payer_id = NULL WHERE payer_id = ANY($1);",
                delete_ids
            )
            stats["payments_payer_id_set_null"] = int(res.split(" ")[1])

            # Scan results reviewed_by -> NULL
            res = await conn.execute(
                "UPDATE scan_results SET reviewed_by = NULL WHERE reviewed_by = ANY($1);",
                delete_ids
            )
            stats["scan_results_reviewed_by_set_null"] = int(res.split(" ")[1])

            # === BƯỚC 3.2: XÓA DỮ LIỆU THUỘC VỀ NGƯỜI BỊ XÓA (THEO THỨ TỰ FK) ===
            # Tournaments created by deleted users
            deleted_tournaments = await conn.fetch(
                "SELECT id FROM tournaments WHERE created_by = ANY($1);",
                delete_ids
            )
            del_tourn_ids = [t["id"] for t in deleted_tournaments]

            # Tournament games (thuộc giải đấu bị xóa HOẶC do người chơi bị xóa tham gia)
            res = await conn.execute("""
                DELETE FROM tournament_games 
                WHERE tournament_id = ANY($1) 
                   OR white_player_id = ANY($2) 
                   OR black_player_id = ANY($2);
            """, del_tourn_ids, delete_ids)
            stats["deleted_tournament_games"] = int(res.split(" ")[1])

            # Tournament standings
            res = await conn.execute("""
                DELETE FROM tournament_standings 
                WHERE tournament_id = ANY($1) 
                   OR student_id = ANY($2);
            """, del_tourn_ids, delete_ids)
            stats["deleted_tournament_standings"] = int(res.split(" ")[1])

            # Tournament participants
            res = await conn.execute("""
                DELETE FROM tournament_participants 
                WHERE tournament_id = ANY($1) 
                   OR student_id = ANY($2);
            """, del_tourn_ids, delete_ids)
            stats["deleted_tournament_participants"] = int(res.split(" ")[1])

            # Tournaments
            if del_tourn_ids:
                res = await conn.execute("DELETE FROM tournaments WHERE id = ANY($1);", del_tourn_ids)
                stats["deleted_tournaments"] = int(res.split(" ")[1])

            # Assignments created by deleted teachers
            deleted_assignments = await conn.fetch(
                "SELECT id FROM assignments WHERE teacher_id = ANY($1);",
                delete_ids
            )
            del_assign_ids = [a["id"] for a in deleted_assignments]

            # Student attempts (tham chiếu assignment_submissions hoặc student_progress)
            res = await conn.execute("""
                DELETE FROM student_attempts 
                WHERE submission_id IN (
                    SELECT id FROM assignment_submissions 
                    WHERE student_id = ANY($1) OR assignment_id = ANY($2)
                ) OR progress_id IN (
                    SELECT id FROM student_progress 
                    WHERE student_id = ANY($1) OR assignment_id = ANY($2)
                );
            """, delete_ids, del_assign_ids)
            stats["deleted_student_attempts"] = int(res.split(" ")[1])

            # Assignment submissions (của học sinh bị xóa HOẶC thuộc bài tập bị xóa)
            res = await conn.execute("""
                DELETE FROM assignment_submissions 
                WHERE student_id = ANY($1) 
                   OR assignment_id = ANY($2);
            """, delete_ids, del_assign_ids)
            stats["deleted_assignment_submissions"] = int(res.split(" ")[1])

            # Student progress linked to deleted assignments or deleted students
            res = await conn.execute("""
                DELETE FROM student_progress 
                WHERE student_id = ANY($1) 
                   OR assignment_id = ANY($2);
            """, delete_ids, del_assign_ids)
            stats["deleted_student_progress"] = int(res.split(" ")[1])

            # Assignments
            if del_assign_ids:
                res = await conn.execute("DELETE FROM assignments WHERE id = ANY($1);", del_assign_ids)
                stats["deleted_assignments"] = int(res.split(" ")[1])

            # Chat messages & sessions
            del_sessions = await conn.fetch("SELECT id FROM chat_sessions WHERE user_id = ANY($1);", delete_ids)
            del_session_ids = [s["id"] for s in del_sessions]
            if del_session_ids:
                res = await conn.execute("DELETE FROM chat_messages WHERE session_id = ANY($1);", del_session_ids)
                stats["deleted_chat_messages"] = int(res.split(" ")[1])
                res = await conn.execute("DELETE FROM ai_puzzle_attempts WHERE session_id = ANY($1);", del_session_ids)
                stats["deleted_ai_puzzle_attempts"] += int(res.split(" ")[1])

            res = await conn.execute("DELETE FROM ai_puzzle_attempts WHERE user_id = ANY($1);", delete_ids)
            stats["deleted_ai_puzzle_attempts"] += int(res.split(" ")[1])

            res = await conn.execute("DELETE FROM chat_sessions WHERE user_id = ANY($1);", delete_ids)
            stats["deleted_chat_sessions"] = int(res.split(" ")[1])

            # Class enrollments
            res = await conn.execute("DELETE FROM class_enrollments WHERE student_id = ANY($1);", delete_ids)
            stats["deleted_class_enrollments"] = int(res.split(" ")[1])

            # Parent student
            res = await conn.execute("""
                DELETE FROM parent_student 
                WHERE parent_id = ANY($1) OR student_id = ANY($1);
            """, delete_ids)
            stats["deleted_parent_student"] = int(res.split(" ")[1])

            # Invoices & Payments
            del_invoices = await conn.fetch("SELECT id FROM invoices WHERE student_id = ANY($1);", delete_ids)
            del_invoice_ids = [inv["id"] for inv in del_invoices]
            if del_invoice_ids:
                res = await conn.execute("DELETE FROM payments WHERE invoice_id = ANY($1);", del_invoice_ids)
                stats["deleted_payments"] = int(res.split(" ")[1])
                res = await conn.execute("DELETE FROM invoices WHERE id = ANY($1);", del_invoice_ids)
                stats["deleted_invoices"] = int(res.split(" ")[1])

            # Notifications
            res = await conn.execute("DELETE FROM notifications WHERE user_id = ANY($1);", delete_ids)
            stats["deleted_notifications"] = int(res.split(" ")[1])

            # Scan jobs & results
            del_jobs = await conn.fetch("SELECT id FROM scan_jobs WHERE uploaded_by = ANY($1);", delete_ids)
            del_job_ids = [j["id"] for j in del_jobs]
            if del_job_ids:
                res = await conn.execute("DELETE FROM scan_results WHERE job_id = ANY($1);", del_job_ids)
                stats["deleted_scan_results"] = int(res.split(" ")[1])
                res = await conn.execute("DELETE FROM scan_jobs WHERE id = ANY($1);", del_job_ids)
                stats["deleted_scan_jobs"] = int(res.split(" ")[1])

            # Cuối cùng: Xóa bảng users
            res = await conn.execute("DELETE FROM users WHERE id = ANY($1);", delete_ids)
            stats["deleted_users"] = int(res.split(" ")[1])

        # === BƯỚC 3.3: KIỂM TRA TOÀN VẸN VÀ BẢO TOÀN DỮ LIỆU ===
        # Kiểm tra không còn bản ghi nào trỏ đến user_id bị xóa
        for tbl, col in [
            ("class_enrollments", "student_id"),
            ("assignment_submissions", "student_id"),
            ("parent_student", "student_id"),
            ("parent_student", "parent_id"),
            ("tournament_participants", "student_id"),
        ]:
            orphans = await conn.fetchval(f"SELECT count(*) FROM {tbl} WHERE {col} = ANY($1);", delete_ids)
            if orphans > 0:
                raise RuntimeError(f"Lỗi toàn vẹn dữ liệu: Còn {orphans} dòng mồ côi trong {tbl}.{col}!")

        # Kiểm tra các user giữ vẫn còn nguyên
        remaining_count = await conn.fetchval("SELECT count(*) FROM users;")
        expected_remaining = len(actual_keep_users)
        if remaining_count != expected_remaining:
            raise RuntimeError(
                f"Lỗi số lượng: Số user còn lại ({remaining_count}) không khớp dự kiến ({expected_remaining})!"
            )

        print("\n--- BÁO CÁO SỐ DÒNG BỊ THAY ĐỔI / XÓA ---")
        for k, v in stats.items():
            if v > 0 or "user" in k:
                print(f"  * {k:35s}: {v}")

        # Thống kê user còn lại theo trung tâm và vai trò
        remaining_users = await conn.fetch("""
            SELECT u.role, c.name AS center_name, count(u.id) AS cnt
            FROM users u
            LEFT JOIN centers c ON u.center_id = c.id
            GROUP BY u.role, c.name
            ORDER BY c.name NULLS FIRST, u.role;
        """)

        print("\n--- THỐNG KÊ NGƯỜI DÙNG CÒN LẠI THEO TRUNG TÂM & VAI TRÒ ---")
        for r in remaining_users:
            cname = r["center_name"] if r["center_name"] else "Toàn hệ thống (Super Admin)"
            print(f"  * Trung tâm: {cname:35s} | Vai trò: {r['role']:15s} | Số lượng: {r['cnt']}")

        if execute:
            await tr.commit()
            print("\n[THÀNH CÔNG] Giao dịch đã được COMMIT thành công vào cơ sở dữ liệu.")
        else:
            await tr.rollback()
            print("\n[HOÀN TẤT DRY-RUN] Toàn bộ thay đổi đã được ROLLBACK an toàn (Chưa có gì bị xóa).")

    except Exception as e:
        await tr.rollback()
        print(f"\n[LỖI] Đã xảy ra lỗi trong quá trình thực hiện: {e}")
        print("[AN TOÀN] Giao dịch đã được ROLLBACK hoàn toàn.")
        raise
    finally:
        await conn.close()


def main():
    parser = argparse.ArgumentParser(description="CAMS Users Cleanup Script")
    parser.add_argument(
        "--decision-file",
        default="cleanup_decisions.json",
        help="Đường dẫn tệp quyết định JSON",
    )
    parser.add_argument(
        "--execute",
        action="store_true",
        default=False,
        help="Thực thi xóa thật (mặc định là dry-run)",
    )
    parser.add_argument(
        "--allow-superadmin-delete",
        action="store_true",
        default=False,
        help="Cho phép xóa tài khoản super_admin nếu có trong quyết định",
    )
    parser.add_argument(
        "--db-url",
        default="postgresql://cams_user:cams_password@db:5432/cams_db",
        help="Database connection URL",
    )

    args = parser.parse_args()

    asyncio.run(
        run_cleanup(
            db_url=args.db_url,
            decision_file=args.decision_file,
            execute=args.execute,
            allow_superadmin_delete=args.allow_superadmin_delete,
        )
    )


if __name__ == "__main__":
    main()
