# Báo cáo triển khai: Khóa cứng nộp bài (Submit Lock) & Mở lại bài tập (Reopen) cho CAMS E-learning

**Ngày thực hiện:** 2026-10-13  
**Mã Task Ledger:** `CAMS-0016`  
**Trạng thái:** `HOÀN THÀNH (DONE)`

---

## 1. Mục tiêu và Bối cảnh
Dựa trên đề xuất tại `archive/Đề xuất tối ưu quy trình e-learning Luyện tập và Bài tập về nhà.md` và sau khi giải quyết triệt để lỗi học viên giải 8/7 bài tập kèm 151 điểm do race condition:
- Triển khai **Khóa cứng nộp bài (Submit Lock)** phía server: Khi học sinh nộp bài (`submitted`), hệ thống khóa cứng không cho phép giải lại để thay đổi điểm số, ngăn chặn hoàn toàn việc làm lại nhiều lần để cộng dồn điểm trái phép.
- Triển khai **Mở lại bài (Reopen)** cho Giáo viên / Quản trị viên: Giáo viên có thể chủ động mở khóa cho học sinh làm lại kèm lý do rõ ràng.
- Triển khai **Tự động nộp bài khi quá hạn (Auto Submit Overdue)**: Tác vụ Celery chạy định kỳ mỗi 10 phút quét và khóa các bài tập đã quá `due_date`.
- Cập nhật **Giao diện người dùng (UI/UX)**:
  - Cho học sinh: Nút "Nộp bài tập 🔒", Modal xác nhận nộp bài hiển thị tiến độ và điểm số, Banner thông báo trạng thái khóa cứng, chuyển chế độ luyện tập sang "Xem lại (Read-only)" không ghi đè kết quả.
  - Cho giáo viên: Bảng tiến độ hiển thị huy hiệu `Đã nộp 🔒`, ngày nộp, nút `Mở lại bài (Reopen)` kèm Modal nhập lý do mở khóa.

---

## 2. Chi tiết các thay đổi kỹ thuật

### 2.1 Backend & Database
1. **Model `AssignmentSubmission` & Enum `SubmissionStatus`:**
   - File: `backend/app/models/base.py`:
     - Thêm `SubmissionStatus`: `not_started`, `in_progress`, `submitted`, `graded`.
   - File: `backend/app/models/assignment.py`:
     - Tạo model `AssignmentSubmission` lưu trữ:
       - `status` (`SubmissionStatus`)
       - `submitted_at`
       - `total_points`, `completed_puzzles`
       - `reopened_at`, `reopened_by`, `reopen_reason`
     - Ràng buộc: `UniqueConstraint('assignment_id', 'student_id', name='uq_assignment_submission_student')`.
2. **Database Migration Alembic:**
   - Migration file: `backend/alembic/versions/f920da3e1b23_add_assignment_submissions.py`.
   - Đã áp dụng thành công lên container `cams_postgres`:
     `docker exec cams_backend alembic upgrade head`.
   - Đã khởi tạo dữ liệu bản ghi submission mặc định cho các bài tập hiện có.
3. **Pydantic Schemas:**
   - File: `backend/app/schemas/assignment.py`:
     - `AssignmentSubmissionRead`
     - `AssignmentReopenRequest` (yêu cầu `student_id` và `reason`).
4. **Service Layer:**
   - File: `backend/app/services/assignment_service.py`:
     - `get_or_create_submission(db, assignment_id, student_id)`
     - `submit_assignment(db, assignment_id, student_id)`
     - `reopen_assignment(db, assignment_id, student_id, teacher_id, reason)`
     - `is_assignment_locked_for_student(db, assignment_id, student_id)`
   - File: `backend/app/services/progress_service.py`:
     - Kiểm tra `is_assignment_locked_for_student` trong hàm `submit_attempt(...)`. Nếu bài tập đã nộp, raise `ValueError("Bài tập này đã được nộp và khóa cứng...")`.
5. **API Endpoints:**
   - File: `backend/app/api/endpoints/assignments.py`:
     - `GET /{assignment_id}/my-submission`: Lấy trạng thái nộp bài của học sinh hiện tại.
     - `POST /{assignment_id}/submit`: Nộp và khóa cứng bài tập.
     - `POST /{assignment_id}/reopen`: Giáo viên mở lại bài kèm lý do.
     - `GET /{assignment_id}/progress`: Trả về danh sách tiến độ kèm `submission_status`, `submitted_at`, `reopened_at`, `reopen_reason`.
6. **Celery Auto-submit Task:**
   - File: `backend/app/tasks.py`:
     - Tác vụ `auto_submit_overdue_assignments()`: Quét các assignment quá hạn chưa nộp và tự động chuyển sang `submitted`.
   - File: `backend/app/core/celery_app.py`:
     - Thêm cấu hình beat schedule `auto-submit-overdue-assignments` chạy định kỳ mỗi 10 phút.

---

### 2.2 Frontend
1. **API Client (`frontend/src/lib/puzzleApi.ts`):**
   - Thêm interface `AssignmentSubmission`.
   - Thêm các hàm `getMyAssignmentSubmission`, `submitAssignment`, `reopenAssignment`.
2. **Chi tiết bài tập (`frontend/src/pages/AssignmentDetail.tsx`):**
   - Tích hợp kiểm tra trạng thái submission của học sinh khi tải trang.
   - Hiển thị nút "Nộp bài tập 🔒" khi đã làm ít nhất 1 bài.
   - Thêm Modal xác nhận nộp bài (hiển thị số câu làm được, điểm đạt được, cảnh báo khóa bài).
   - Thêm Banner trạng thái nộp bài (Màu emerald khi đã nộp, Màu amber khi được giáo viên mở lại kèm lý do).
   - Trong bảng tiến độ của Giáo viên:
     - Hiển thị badge trạng thái `Đã nộp 🔒` kèm thời gian nộp.
     - Thêm cột Thao tác với nút "Mở lại bài (Reopen)".
     - Modal mở lại bài cho giáo viên nhập lý do cụ thể trước khi xác nhận.
   - Các nút trong danh sách thế cờ tự động chuyển thành "Xem lại" (icon con mắt) khi bài tập đã khóa.
3. **Màn hình luyện tập (`frontend/src/pages/Practice.tsx`):**
   - Phát hiện trạng thái bài tập bị khóa từ `assignmentIdParam` và `readonlyParam`.
   - Hiển thị Banner trên đầu bàn cờ: "Bài tập này đã nộp và khóa cứng — Đang ở chế độ Xem lại (không tính thêm điểm hoặc ghi đè kết quả)".
   - Vô hiệu hóa việc gọi `submitPuzzleAttempt` khi bài tập đã khóa (chế độ xem lại an toàn 100%).
   - Tự động duy trì cờ xem lại khi chuyển giữa các thế cờ.

### 2.3 Chuẩn hóa chế độ Bài tập về nhà (BTVN vs Free Practice)
1. **Tách biệt luồng BTVN (`isAssignmentMode = Boolean(assignmentIdParam)`):**
   - Không toast báo "Nước đi chưa chính xác!" làm lộ kết quả hoặc gây ức chế cho học sinh.
   - Khi học sinh đi bất kỳ nước cờ nào (kể cả đi sai):
     - Hệ thống toast thông báo trung tính: `"Đã ghi nhận phương án giải của bạn."` (icon 📝).
     - Gửi toàn bộ dãy nước (`moves_uci`, `player_moves_uci`, `moves_san`) lên server lưu vào biên bản làm bài.
     - Hiển thị Overlay trung tính:
       - Tiêu đề: **"ĐÃ GHI NHẬN PHƯƠNG ÁN GIẢI"**
       - Mô tả: *"Phương án của bạn cho thế cờ này đã được lưu lại để gửi giáo viên chấm điểm."*
       - Nút chuyển bài: **"Bài kế tiếp (n/total)"** (hoặc "Hoàn thành bài tập" nếu là bài cuối).
     - **Giải quyết triệt để lỗi:** Trước đây khi học sinh làm sai, giao diện chặn kéo quân và không có nút chuyển bài, ép học sinh phải bấm "Đặt lại" để thử-sai từng quân cờ $\to$ nay học sinh được chuyển tiếp sang bài kế tiếp ngay lập tức.
   - Ẩn nút "Gợi ý (Hint)" trong chế độ BTVN để tránh lộ lời giải khi làm bài kiểm tra.
   - Vô hiệu hóa nút "Đặt lại" sau khi bài đã được ghi nhận phương án.
2. **Cập nhật Giao diện Chi tiết Bài tập (`AssignmentDetail.tsx`):**
   - Theo dõi `attemptedPuzzleIds` (danh sách các thế cờ học sinh đã làm, dù đúng hay sai).
   - Nút "Tiếp tục làm bài" tự động chọn `nextUnattemptedPuzzle` (thế cờ tiếp theo chưa làm), không đưa học sinh quay lại bài đã làm sai.
   - Thanh tiến độ làm bài hiển thị theo `attemptedPuzzleIds.size / totalPuzzles` (học sinh làm đủ số bài là đạt 100% tiến độ làm bài).
   - Danh sách thế cờ hiển thị huy hiệu rõ ràng:
     - `Đã giải đúng` (màu xanh lá)
     - `Đã ghi nhận` (màu tím indigo)
     - `Chưa làm` (màu slate)
   - Nút "Nộp bài tập 🔒" hiển thị ngay khi học sinh đã làm ít nhất 1 bài, Modal xác nhận nộp bài hiển thị chi tiết số bài đã làm, số bài giải đúng và điểm số đạt được.

---

## 3. Kết quả kiểm thử (Verification)
1. **Backend Integration Tests:**
   - File: `backend/tests/test_submission_lock.py`
   - Chạy lệnh: `docker exec cams_backend python tests/test_submission_lock.py`
   - Kết quả: **ALL SUBMISSION LOCK TESTS PASSED!**
2. **Mate Solver Tests:**
   - File: `backend/tests/test_mate_solver.py`
   - Chạy lệnh: `docker exec cams_backend python tests/test_mate_solver.py`
   - Kết quả: **ALL TESTS PASSED in 16.8s**
3. **Celery Auto-submit Task Test:**
   - Chạy lệnh: `docker exec cams_backend python -c "from app.tasks import auto_submit_overdue_assignments; print(auto_submit_overdue_assignments.delay().get())"`
   - Kết quả: `{'status': 'ok', 'auto_submitted': 2}` $\to$ hoạt động chính xác.
4. **Frontend TypeScript & Vite Build:**
   - Chạy lệnh: `docker exec cams_frontend npm run build`
   - Kết quả: **Exit code 0, không có lỗi TypeScript hay cú pháp nào.**

---

## 4. Các file đã thay đổi / tạo mới
- `backend/app/models/base.py`
- `backend/app/models/assignment.py`
- `backend/alembic/versions/f920da3e1b23_add_assignment_submissions.py`
- `backend/app/schemas/assignment.py`
- `backend/app/services/assignment_service.py`
- `backend/app/services/progress_service.py`
- `backend/app/api/endpoints/assignments.py`
- `backend/app/tasks.py`
- `backend/app/core/celery_app.py`
- `backend/tests/test_submission_lock.py`
- `frontend/src/lib/puzzleApi.ts`
- `frontend/src/pages/AssignmentDetail.tsx`
- `frontend/src/pages/Practice.tsx`
- `archive/bugs/2026-10-13-assignment-submit-lock-and-reopen.md`
- `CLAUDE.md`
- `.agents/state/CAMS-0016.json`

