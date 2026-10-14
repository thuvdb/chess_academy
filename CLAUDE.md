# CLAUDE.md — Quy ước & Hướng dẫn cho Claude AI trong dự án CAMS

## 1. Quy ước báo cáo & Theo dõi phiên (Bắt buộc)
- **Báo cáo lỗi ghi vào `archive/bugs/<ngày>-<tên>.md`**, Claude sẽ theo mỗi phiên.
- Sau mỗi phiên làm việc, nếu phát hiện hoặc giải quyết lỗi/thay đổi quan trọng, luôn tạo một file tóm tắt chi tiết trong `archive/bugs/` theo định dạng `<YYYY-MM-DD>-<tên-ngắn-gọn>.md` ghi rõ:
  1. Mục tiêu và phạm vi công việc đã làm.
  2. Các file đã sửa đổi, thêm mới (`git status`).
  3. Trạng thái kiểm thử (Tests pass/fail).
  4. Phần việc đang dở dang / blocker / bước tiếp theo cần làm.

---

## 2. Thông tin dự án CAMS (Chess Academy Management System)
- **Stack:**
  - Backend: FastAPI, SQLAlchemy 2.0 (async), Alembic, Pydantic v2, python-chess, Celery, Redis.
  - Frontend: React 18, Vite, TypeScript, Tailwind CSS, react-chessboard, Lucide icons.
  - Mobile: React Native / Expo.
  - Database: PostgreSQL 16 (chạy qua Docker `cams_postgres`).
  - Containers chính: `cams_backend`, `cams_frontend`, `cams_postgres`, `cams_redis`, `cams_worker`, `cams_beat`.

---

## 3. Lệnh thường dùng

### Backend
```powershell
# Chạy unit tests trên host
& "C:\Program Files\Python313\python.exe" -m pytest tests/test_security_access.py
& "C:\Program Files\Python313\python.exe" -m pytest tests/test_puzzle_service.py
& "C:\Program Files\Python313\python.exe" -m pytest tests/test_mate_solver.py

# Hoặc chạy test mate solver trực tiếp trong container
docker exec cams_backend python tests/test_mate_solver.py

# Chạy migration DB
docker exec cams_backend alembic upgrade head
```

### Frontend
```powershell
# Typecheck & Build trong container
docker exec cams_frontend npm run build

# Typecheck độc lập
docker exec cams_frontend npx tsc -b
```

---

## 4. Nguyên tắc phát triển (SDLC)
- Tuân thủ quy tắc kiến trúc trong `.agents/rules/`:
  - `01-git-workflow.md`
  - `02-code-quality.md`
  - `04-orchestration-policy.md`
  - `05-result-contract.md`
- **Database Migrations:** Bất cứ khi nào thêm/sửa model SQLAlchemy, luôn tạo migration Alembic và chạy `alembic upgrade head` vào database trước khi kết thúc phiên. Không để model lệch so với schema DB thực tế.
- **Không để dở dang uncommitted code bí mật:** Ghi rõ trạng thái uncommitted trong báo cáo phiên nếu chưa commit.

---

## 5. Nhật ký báo cáo các phiên làm việc
- Báo cáo lỗi ghi vào [archive/bugs/2026-10-11-mate-solver-and-practice-error.md](file:///c:/ProjectAI/chess_academy/archive/bugs/2026-10-11-mate-solver-and-practice-error.md) (Xây dựng mate_solver & sửa lỗi làm bài tập)
- Báo cáo lỗi ghi vào [archive/bugs/2026-10-11-mate-solver-frontend-integration.md](file:///c:/ProjectAI/chess_academy/archive/bugs/2026-10-11-mate-solver-frontend-integration.md) (Tích hợp cây biến thể lên Practice UI)
- Báo cáo lỗi ghi vào [archive/bugs/2026-10-12-mate4-timeout-and-tree-view-issues.md](file:///c:/ProjectAI/chess_academy/archive/bugs/2026-10-12-mate4-timeout-and-tree-view-issues.md) (Phân tích timeout bài mate-in-4 & thiếu Tree view)
- Báo cáo lỗi ghi vào [archive/bugs/2026-10-12-mate4-solver-and-tree-view-resolved.md](file:///c:/ProjectAI/chess_academy/archive/bugs/2026-10-12-mate4-solver-and-tree-view-resolved.md) (Xử lý triệt để: Stockfish acceleration, auto classify mate 4, Tree View trong Edit modal, revalidate 68 bài DB)
- Báo cáo lỗi ghi vào [archive/bugs/2026-10-13-fix-assignment-duplicate-progress-and-points.md](file:///c:/ProjectAI/chess_academy/archive/bugs/2026-10-13-fix-assignment-duplicate-progress-and-points.md) (Xử lý lỗi 8/7 thế cờ, ngăn chặn race condition & dọn dẹp điểm số cộng dồn của Triết)
- Báo cáo lỗi ghi vào [archive/bugs/2026-10-13-assignment-submit-lock-and-reopen.md](file:///c:/ProjectAI/chess_academy/archive/bugs/2026-10-13-assignment-submit-lock-and-reopen.md) (Triển khai tính năng Khóa cứng nộp bài Submit Lock, Reopen cho Giáo viên, Tách chuẩn hóa luồng BTVN không chặn khi đi sai & chuyển tiếp bài tập)
- Báo cáo lỗi ghi vào [archive/bugs/2026-10-13-fix-assignment-puzzles-student-view-missing.md](file:///c:/ProjectAI/chess_academy/archive/bugs/2026-10-13-fix-assignment-puzzles-student-view-missing.md) (Khắc phục lỗi học sinh bị thiếu 2 thế cờ trong BTVN do filter verified_only, bổ sung endpoint get_assignment_puzzles chuyên dụng)
- Báo cáo lỗi ghi vào [archive/bugs/2026-10-13-teacher-grading-workflow-and-progress-fix.md](file:///c:/ProjectAI/chess_academy/archive/bugs/2026-10-13-teacher-grading-workflow-and-progress-fix.md) (Chuẩn hóa quy trình Chấm & Trả BTVN: Thêm modal xem lời giải của học sinh, so sánh đáp án mẫu, giáo viên nhập nhận xét và trả bài; sửa cột tiến độ giáo viên từ 1/5 thành 5/5; bảo mật kết quả không lộ đáp án khi học sinh vừa nộp)
- Báo cáo lỗi ghi vào [archive/bugs/2026-10-13-fix-homework-reopen-and-score-divergence.md](file:///c:/ProjectAI/chess_academy/archive/bugs/2026-10-13-fix-homework-reopen-and-score-divergence.md) (Khắc phục lỗi luồng Mở lại BTVN, bảo mật kết quả lần chưa nộp, chặn 409 Conflict khi chưa nộp bài, và đồng bộ thống nhất điểm số 11 pts giữa Giáo viên và Học sinh)

