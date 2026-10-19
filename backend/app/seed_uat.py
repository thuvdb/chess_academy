"""
CAMS UAT Seed Script — Khởi tạo dữ liệu kiểm thử Chấp nhận người dùng (UAT).
Đảm bảo tính bất đồng bộ (async), thứ tự khóa ngoại (FKs), và tính lũy đễ (idempotent).
"""

import asyncio
import logging
from datetime import datetime, timezone
import uuid
from typing import Any

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert

from app.core.database import async_session_factory
from app.core.security import hash_password
from app.models.base import (
    ClassLevel,
    EnrollmentStatus,
    PuzzleDifficulty,
    PuzzleSource,
    PuzzleType,
    SubscriptionPlan,
    UserRole,
)
from app.models.center import Branch, Center
from app.models.class_ import Class, ClassEnrollment
from app.models.puzzle import Puzzle, PuzzleSolution
from app.models.settings import CatalogItem, Setting
from app.models.user import User, parent_student

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("cams_seed_uat")


async def seed_settings_and_catalogs(db) -> None:
    """Bước 1: Khởi tạo danh mục hệ thống và cấu hình mặc định (Idempotent)."""
    logger.info("--- BƯỚC 1: Khởi tạo Settings & Catalogs ---")

    default_catalogs = [
        # course_level
        ("course_level", "beginner", "Cơ bản", 1),
        ("course_level", "intermediate", "Trung cấp", 2),
        ("course_level", "advanced", "Nâng cao", 3),
        ("course_level", "master", "Chuyên sâu", 4),
        # puzzle_theme
        ("puzzle_theme", "fork", "Bắt đôi (Fork)", 1),
        ("puzzle_theme", "pin", "Ghim quân (Pin)", 2),
        ("puzzle_theme", "skewer", "Xiên (Skewer)", 3),
        ("puzzle_theme", "discovered_attack", "Tấn công mở", 4),
        ("puzzle_theme", "double_check", "Chiếu kép", 5),
        ("puzzle_theme", "back_rank", "Hàng ngang cuối", 6),
        ("puzzle_theme", "deflection", "Đánh lạc hướng", 7),
        # puzzle_difficulty_band
        ("puzzle_difficulty_band", "easy", "Dễ (< 1000)", 1),
        ("puzzle_difficulty_band", "medium", "Trung bình (1000 - 1500)", 2),
        ("puzzle_difficulty_band", "hard", "Khó (> 1500)", 3),
        # parent_relationship
        ("parent_relationship", "father", "Bố", 1),
        ("parent_relationship", "mother", "Mẹ", 2),
        ("parent_relationship", "guardian", "Người giám hộ", 3),
        ("parent_relationship", "other", "Khác", 4),
        # class_status
        ("class_status", "active", "Đang mở", 1),
        ("class_status", "upcoming", "Sắp khai giảng", 2),
        ("class_status", "completed", "Đã hoàn thành", 3),
        # enrollment_status
        ("enrollment_status", "active", "Đang học", 1),
        ("enrollment_status", "reserved", "Bảo lưu", 2),
        ("enrollment_status", "dropped", "Nghỉ học", 3),
        # currency
        ("currency", "VND", "Việt Nam Đồng (đ)", 1),
        # class_schedule_slot
        ("class_schedule_slot", "slot_1", "08:00 - 09:30", 1),
        ("class_schedule_slot", "slot_2", "09:45 - 11:15", 2),
        ("class_schedule_slot", "slot_3", "14:00 - 15:30", 3),
        ("class_schedule_slot", "slot_4", "15:45 - 17:15", 4),
        ("class_schedule_slot", "slot_5", "18:00 - 19:30", 5),
        ("class_schedule_slot", "slot_6", "19:45 - 21:15", 6),
    ]

    for cat_type, code, label, order_idx in default_catalogs:
        stmt = select(CatalogItem).where(
            CatalogItem.catalog_type == cat_type,
            CatalogItem.code == code,
            CatalogItem.center_id.is_(None),
        )
        existing = (await db.execute(stmt)).scalar_one_or_none()
        if existing:
            existing.label = label
            existing.order_index = order_idx
            existing.is_active = True
        else:
            db.add(
                CatalogItem(
                    id=uuid.uuid4(),
                    center_id=None,
                    catalog_type=cat_type,
                    code=code,
                    label=label,
                    order_index=order_idx,
                    is_active=True,
                )
            )

    default_settings = [
        ("system_name", "CAMS - Chess Academy Management System", "string", "Tên hệ thống", "general", False),
        ("allow_public_register", "false", "bool", "Cho phép tự do đăng ký tài khoản học sinh", "security", False),
        ("rating_initial", "800", "int", "Điểm Elo/Rating khởi tạo cho học viên mới", "rating", False),
        ("k_factor_low", "32", "int", "Hệ số K khi rating < 1200", "rating", True),
        ("k_factor_high", "16", "int", "Hệ số K khi rating >= 2000", "rating", True),
        ("hint_penalty", "5", "int", "Số điểm trừ khi học sinh dùng gợi ý", "rating", True),
        ("stockfish_depth", "10", "int", "Độ sâu tìm kiếm mặc định của Stockfish engine", "engine", True),
        ("stockfish_time_limit", "1.0", "float", "Thời gian tính toán tối đa của Stockfish (giây)", "engine", True),
        ("max_upload_size_mb", "50", "int", "Dung lượng file PDF tải lên tối đa (MB)", "scanner", True),
        ("max_upload_pages", "20", "int", "Số trang quét tối đa mỗi lượt PDF", "scanner", True),
    ]

    for key, val, val_type, desc, cat, overridable in default_settings:
        stmt = select(Setting).where(
            Setting.key == key,
            Setting.center_id.is_(None),
        )
        existing_setting = (await db.execute(stmt)).scalar_one_or_none()
        if existing_setting:
            existing_setting.value = val
            existing_setting.value_type = val_type
            existing_setting.description = desc
            existing_setting.category = cat
            existing_setting.is_overridable = overridable
        else:
            db.add(
                Setting(
                    id=uuid.uuid4(),
                    center_id=None,
                    key=key,
                    value=val,
                    value_type=val_type,
                    description=desc,
                    category=cat,
                    is_overridable=overridable,
                )
            )

    await db.flush()
    logger.info("✓ Đã seed hoàn tất Settings và Catalogs.")


async def seed_center_and_branch(db) -> tuple[Center, Branch]:
    """Bước 2: Khởi tạo Trung tâm mẫu và Chi nhánh chính."""
    logger.info("--- BƯỚC 2: Khởi tạo Center & Branch ---")
    center_name = "Học Viện Cờ Vua CAMS"

    stmt = select(Center).where(Center.name == center_name)
    center = (await db.execute(stmt)).scalar_one_or_none()
    if not center:
        center = Center(
            id=uuid.uuid4(),
            name=center_name,
            address="Tòa nhà CAMS, Số 123 Đường Cờ Vua, Quận 1, TP. Hồ Chí Minh",
            phone="0901234567",
            email="contact@cams.test",
            facebook_page_url="https://facebook.com/camschessacademy",
            subscription_plan=SubscriptionPlan.PREMIUM.value,
        )
        db.add(center)
        await db.flush()
        logger.info(f"✓ Tạo mới Center: {center.name} (ID: {center.id})")
    else:
        center.subscription_plan = SubscriptionPlan.PREMIUM.value
        center.email = "contact@cams.test"
        center.phone = "0901234567"
        await db.flush()
        logger.info(f"✓ Cập nhật Center hiện có: {center.name} (ID: {center.id})")

    branch_name = "Cơ sở Chính - Quận 1"
    stmt_branch = select(Branch).where(
        Branch.center_id == center.id,
        Branch.name == branch_name,
    )
    branch = (await db.execute(stmt_branch)).scalar_one_or_none()
    if not branch:
        branch = Branch(
            id=uuid.uuid4(),
            center_id=center.id,
            name=branch_name,
            address="Số 123 Đường Cờ Vua, Phường Bến Nghé, Quận 1, TP. Hồ Chí Minh",
            phone="0901234567",
            is_active=True,
        )
        db.add(branch)
        await db.flush()
        logger.info(f"✓ Tạo mới Branch: {branch.name} (ID: {branch.id})")
    else:
        branch.is_active = True
        await db.flush()
        logger.info(f"✓ Cập nhật Branch hiện có: {branch.name} (ID: {branch.id})")

    return center, branch


async def seed_users(db, center: Center, branch: Branch) -> dict[str, User]:
    """Bước 3: Khởi tạo đầy đủ 6 Vai trò người dùng thử nghiệm UAT."""
    logger.info("--- BƯỚC 3: Khởi tạo Users (6 Roles chuẩn) ---")

    users_data = [
        # 1. Super Admin
        {
            "email": "superadmin@cams.test",
            "password": "Super@2026!",
            "full_name": "Vũ Tổng Quản",
            "role": UserRole.SUPER_ADMIN.value,
            "center_id": None,
            "branch_id": None,
            "elo_rating": 2200,
            "phone": "0911000001",
        },
        {
            "email": "super_admin@cams.vn",
            "password": "Super@2026!",
            "full_name": "Vũ Tổng Quản",
            "role": UserRole.SUPER_ADMIN.value,
            "center_id": None,
            "branch_id": None,
            "elo_rating": 2200,
            "phone": "0911000001",
        },
        # 2. Center Admin
        {
            "email": "admin@cams.test",
            "password": "Admin@2026!",
            "full_name": "Nguyễn Quản Trị",
            "role": UserRole.CENTER_ADMIN.value,
            "center_id": center.id,
            "branch_id": branch.id,
            "elo_rating": 1600,
            "phone": "0911000002",
        },
        {
            "email": "admin@cams.vn",
            "password": "Admin@2026!",
            "full_name": "Nguyễn Quản Trị",
            "role": UserRole.CENTER_ADMIN.value,
            "center_id": center.id,
            "branch_id": branch.id,
            "elo_rating": 1600,
            "phone": "0911000002",
        },
        # 3. Teachers
        {
            "email": "teacher1@cams.test",
            "password": "Teacher@2026!",
            "full_name": "Trần Văn Giáo",
            "role": UserRole.TEACHER.value,
            "center_id": center.id,
            "branch_id": branch.id,
            "elo_rating": 1850,
            "phone": "0911000003",
        },
        {
            "email": "teacher2@cams.test",
            "password": "Teacher@2026!",
            "full_name": "Lê Thị Hoa",
            "role": UserRole.TEACHER.value,
            "center_id": center.id,
            "branch_id": branch.id,
            "elo_rating": 1900,
            "phone": "0911000004",
        },
        {
            "email": "teacher@cams.vn",
            "password": "Teacher@2026!",
            "full_name": "Trần Văn Giáo",
            "role": UserRole.TEACHER.value,
            "center_id": center.id,
            "branch_id": branch.id,
            "elo_rating": 1850,
            "phone": "0911000003",
        },
        # 4. Students
        {
            "email": "student1@cams.test",
            "password": "Student@2026!",
            "full_name": "Phạm Minh Học",
            "role": UserRole.STUDENT.value,
            "center_id": center.id,
            "branch_id": branch.id,
            "elo_rating": 800,
            "phone": "0911000005",
        },
        {
            "email": "student2@cams.test",
            "password": "Student@2026!",
            "full_name": "Hoàng Bảo Long",
            "role": UserRole.STUDENT.value,
            "center_id": center.id,
            "branch_id": branch.id,
            "elo_rating": 800,
            "phone": "0911000006",
        },
        {
            "email": "student3@cams.test",
            "password": "Student@2026!",
            "full_name": "Võ Thị Mai",
            "role": UserRole.STUDENT.value,
            "center_id": center.id,
            "branch_id": branch.id,
            "elo_rating": 800,
            "phone": "0911000007",
        },
        {
            "email": "student@cams.vn",
            "password": "Student@2026!",
            "full_name": "Phạm Minh Học",
            "role": UserRole.STUDENT.value,
            "center_id": center.id,
            "branch_id": branch.id,
            "elo_rating": 800,
            "phone": "0911000005",
        },
        # 5. Parent
        {
            "email": "parent1@cams.test",
            "password": "Parent@2026!",
            "full_name": "Phạm Văn Cha",
            "role": UserRole.PARENT.value,
            "center_id": center.id,
            "branch_id": branch.id,
            "elo_rating": 800,
            "phone": "0911000008",
        },
    ]

    user_map: dict[str, User] = {}

    for udata in users_data:
        email = udata["email"]
        stmt = select(User).where(User.email == email)
        user = (await db.execute(stmt)).scalar_one_or_none()
        hashed_pwd = hash_password(udata["password"])

        if user:
            user.password_hash = hashed_pwd
            user.full_name = udata["full_name"]
            user.role = udata["role"]
            user.center_id = udata["center_id"]
            user.primary_branch_id = udata["branch_id"]
            user.elo_rating = udata["elo_rating"]
            user.phone = udata["phone"]
            user.is_active = True
            logger.info(f"✓ Cập nhật User hiện có: {email} | Role: {udata['role']}")
        else:
            user = User(
                id=uuid.uuid4(),
                email=email,
                password_hash=hashed_pwd,
                full_name=udata["full_name"],
                role=udata["role"],
                center_id=udata["center_id"],
                primary_branch_id=udata["branch_id"],
                elo_rating=udata["elo_rating"],
                phone=udata["phone"],
                is_active=True,
            )
            db.add(user)
            logger.info(f"✓ Tạo mới User: {email} | Role: {udata['role']}")

        await db.flush()
        user_map[email] = user

    return user_map


async def seed_parent_student_link(db, parent: User, student: User) -> None:
    """Bước 4: Liên kết Phụ huynh và Học sinh vào bảng parent_student."""
    logger.info("--- BƯỚC 4: Liên kết Parent - Student ---")
    stmt = select(parent_student).where(
        parent_student.c.parent_id == parent.id,
        parent_student.c.student_id == student.id,
    )
    exists = (await db.execute(stmt)).first()
    if not exists:
        insert_stmt = parent_student.insert().values(
            parent_id=parent.id,
            student_id=student.id,
        )
        await db.execute(insert_stmt)
        await db.flush()
        logger.info(f"✓ Đã liên kết: {parent.full_name} ({parent.email}) -> {student.full_name} ({student.email})")
    else:
        logger.info(f"✓ Đã tồn tại liên kết: {parent.full_name} -> {student.full_name}")


async def seed_classes_and_enrollments(
    db, center: Center, branch: Branch, users: dict[str, User]
) -> None:
    """Bước 5: Tạo 2 lớp học mẫu và ghi danh học sinh."""
    logger.info("--- BƯỚC 5: Khởi tạo Lớp học & Ghi danh ---")

    teacher1 = users["teacher1@cams.test"]
    teacher2 = users["teacher2@cams.test"]
    student1 = users["student1@cams.test"]
    student2 = users["student2@cams.test"]
    student3 = users["student3@cams.test"]

    # 1. Lớp Cờ Vua Cơ Bản K2026
    class_1_name = "Cờ Vua Cơ Bản K2026"
    stmt1 = select(Class).where(
        Class.center_id == center.id,
        Class.name == class_1_name,
    )
    class_1 = (await db.execute(stmt1)).scalar_one_or_none()
    schedule_1 = {
        "mon": "18:00 - 19:30",
        "wed": "18:00 - 19:30",
        "room": "Phòng Cờ 101",
    }
    if not class_1:
        class_1 = Class(
            id=uuid.uuid4(),
            center_id=center.id,
            branch_id=branch.id,
            teacher_id=teacher1.id,
            name=class_1_name,
            level=ClassLevel.BEGINNER.value,
            max_students=20,
            schedule_json=schedule_1,
            is_active=True,
        )
        db.add(class_1)
        await db.flush()
        logger.info(f"✓ Tạo mới lớp: {class_1_name} (Teacher: {teacher1.full_name})")
    else:
        class_1.teacher_id = teacher1.id
        class_1.level = ClassLevel.BEGINNER.value
        class_1.max_students = 20
        class_1.schedule_json = schedule_1
        class_1.is_active = True
        await db.flush()
        logger.info(f"✓ Cập nhật lớp hiện có: {class_1_name}")

    # Ghi danh student1, student2, student3 vào lớp 1
    for st in [student1, student2, student3]:
        stmt_enroll = select(ClassEnrollment).where(
            ClassEnrollment.class_id == class_1.id,
            ClassEnrollment.student_id == st.id,
        )
        enrollment = (await db.execute(stmt_enroll)).scalar_one_or_none()
        if not enrollment:
            enrollment = ClassEnrollment(
                id=uuid.uuid4(),
                class_id=class_1.id,
                student_id=st.id,
                status=EnrollmentStatus.ACTIVE.value,
            )
            db.add(enrollment)
            logger.info(f"  + Ghi danh học sinh {st.full_name} ({st.email}) vào lớp {class_1_name}")
        else:
            enrollment.status = EnrollmentStatus.ACTIVE.value

    # 2. Lớp Chiến Thuật Trung Cấp
    class_2_name = "Chiến Thuật Trung Cấp"
    stmt2 = select(Class).where(
        Class.center_id == center.id,
        Class.name == class_2_name,
    )
    class_2 = (await db.execute(stmt2)).scalar_one_or_none()
    schedule_2 = {
        "tue": "18:00 - 19:30",
        "thu": "18:00 - 19:30",
        "room": "Phòng Chiến Thuật 202",
    }
    if not class_2:
        class_2 = Class(
            id=uuid.uuid4(),
            center_id=center.id,
            branch_id=branch.id,
            teacher_id=teacher2.id,
            name=class_2_name,
            level=ClassLevel.INTERMEDIATE.value,
            max_students=15,
            schedule_json=schedule_2,
            is_active=True,
        )
        db.add(class_2)
        await db.flush()
        logger.info(f"✓ Tạo mới lớp: {class_2_name} (Teacher: {teacher2.full_name})")
    else:
        class_2.teacher_id = teacher2.id
        class_2.level = ClassLevel.INTERMEDIATE.value
        class_2.max_students = 15
        class_2.schedule_json = schedule_2
        class_2.is_active = True
        await db.flush()
        logger.info(f"✓ Cập nhật lớp hiện có: {class_2_name}")

    await db.flush()


async def seed_sample_puzzles(db, center: Center, teacher: User) -> None:
    """Bước 6: Khởi tạo 2 bài toán mẫu UAT (đã verified, kèm giải thuật)."""
    logger.info("--- BƯỚC 6: Khởi tạo Sample Puzzles ---")

    now = datetime.now(timezone.utc)
    puzzles_data = [
        {
            "title": "Thế cờ Chiếu hết 1 nước - UAT",
            "description": "Trắng đi trước và chiếu hết đối thủ chỉ trong 1 nước cờ duy nhất (Bxf7#).",
            "fen": "r1bqkb1r/pppp1ppp/2n2n2/4p3/2B1P3/5N2/PPPP1PPP/RNBQK2R w KQkq - 0 1",
            "difficulty": PuzzleDifficulty.EASY.value,
            "puzzle_type": PuzzleType.MATE_IN_1.value,
            "source": PuzzleSource.MANUAL_FEN.value,
            "tags": ["mate_in_1", "tactic", "opening"],
            "rating": 1000,
            "mate_in": 1,
            "solutions": [
                {
                    "move_order": 1,
                    "move_uci": "c4f7",
                    "move_san": "Bxf7#",
                    "side": "w",
                    "is_best_move": True,
                    "explanation": "Tượng trắng c4 ăn tốt f7 chiếu hết vua đen không lối thoát.",
                }
            ],
        },
        {
            "title": "Thế cờ Tàn cuộc Vua Chốt - UAT",
            "description": "Đen đi trước để giữ thế cờ tàn cuộc hòa hoặc duy trì đối vua chính xác.",
            "fen": "8/4k3/4p3/4P3/3PK3/8/8/8 b - - 0 1",
            "difficulty": PuzzleDifficulty.MEDIUM.value,
            "puzzle_type": PuzzleType.ENDGAME.value,
            "source": PuzzleSource.MANUAL_FEN.value,
            "tags": ["endgame", "king_pawn", "opposition"],
            "rating": 1350,
            "mate_in": None,
            "solutions": [
                {
                    "move_order": 1,
                    "move_uci": "e7d7",
                    "move_san": "Kd7",
                    "side": "b",
                    "is_best_move": True,
                    "explanation": "Vua đen lùi về d7 giữ nguyên tắc đối vua và phòng thủ chốt trung tâm.",
                }
            ],
        },
    ]

    for pdata in puzzles_data:
        fen = pdata["fen"]
        stmt = select(Puzzle).where(
            Puzzle.center_id == center.id,
            Puzzle.fen == fen,
        )
        puzzle = (await db.execute(stmt)).scalar_one_or_none()

        if not puzzle:
            puzzle = Puzzle(
                id=uuid.uuid4(),
                center_id=center.id,
                created_by=teacher.id,
                title=pdata["title"],
                description=pdata["description"],
                fen=fen,
                difficulty=pdata["difficulty"],
                puzzle_type=pdata["puzzle_type"],
                source=pdata["source"],
                tags=pdata["tags"],
                rating=pdata["rating"],
                mate_in=pdata["mate_in"],
                solution_verified=True,
                solution_verified_at=now,
            )
            db.add(puzzle)
            await db.flush()
            logger.info(f"✓ Tạo mới Puzzle: {pdata['title']} (ID: {puzzle.id})")
        else:
            puzzle.title = pdata["title"]
            puzzle.description = pdata["description"]
            puzzle.difficulty = pdata["difficulty"]
            puzzle.puzzle_type = pdata["puzzle_type"]
            puzzle.tags = pdata["tags"]
            puzzle.rating = pdata["rating"]
            puzzle.solution_verified = True
            puzzle.solution_verified_at = now
            await db.flush()
            logger.info(f"✓ Cập nhật Puzzle hiện có: {pdata['title']}")

        # Thêm/cập nhật puzzle solutions
        for sdata in pdata["solutions"]:
            stmt_sol = select(PuzzleSolution).where(
                PuzzleSolution.puzzle_id == puzzle.id,
                PuzzleSolution.move_order == sdata["move_order"],
            )
            sol = (await db.execute(stmt_sol)).scalar_one_or_none()
            if not sol:
                sol = PuzzleSolution(
                    id=uuid.uuid4(),
                    puzzle_id=puzzle.id,
                    move_order=sdata["move_order"],
                    move_uci=sdata["move_uci"],
                    move_san=sdata["move_san"],
                    side=sdata["side"],
                    is_best_move=sdata["is_best_move"],
                    explanation=sdata["explanation"],
                )
                db.add(sol)
            else:
                sol.move_uci = sdata["move_uci"]
                sol.move_san = sdata["move_san"]
                sol.side = sdata["side"]
                sol.is_best_move = sdata["is_best_move"]
                sol.explanation = sdata["explanation"]

    await db.flush()


async def main() -> None:
    """Hàm điều phối chạy toàn bộ quá trình seed UAT theo thứ tự ràng buộc khóa ngoại."""
    logger.info("=================================================================")
    logger.info("BẮT ĐẦU KHỞI TẠO DỮ LIỆU UAT CAMS (seed_uat.py)...")
    logger.info("=================================================================")

    async with async_session_factory() as db:
        try:
            # Bước 1: Settings & Catalogs
            await seed_settings_and_catalogs(db)

            # Bước 2: Center & Branch
            center, branch = await seed_center_and_branch(db)

            # Bước 3: Users
            users = await seed_users(db, center, branch)

            # Bước 4: Parent - Student Link
            parent1 = users.get("parent1@cams.test")
            student1 = users.get("student1@cams.test")
            if parent1 and student1:
                await seed_parent_student_link(db, parent1, student1)

            # Bước 5: Classes & Enrollments
            await seed_classes_and_enrollments(db, center, branch, users)

            # Bước 6: Sample Puzzles
            teacher1 = users.get("teacher1@cams.test")
            if teacher1:
                await seed_sample_puzzles(db, center, teacher1)

            # Commit toàn bộ transaction
            await db.commit()
            logger.info("=================================================================")
            logger.info("🎉 THÀNH CÔNG: Dữ liệu UAT đã được khởi tạo hoàn tất và bảo toàn!")
            logger.info("=================================================================")

        except Exception as e:
            await db.rollback()
            logger.exception(f"❌ LỖI TRONG QUÁ TRÌNH SEED DỮ LIỆU: {e}")
            raise


if __name__ == "__main__":
    asyncio.run(main())
