# Báo cáo: Sửa lỗi luồng Mở lại BTVN, Bảo mật kết quả lần chưa nộp & Khắc phục lệch điểm giữa Giáo viên và Học sinh

**Ngày thực hiện:** 2026-10-13  
**Mã Task:** CAMS-0018  
**Tác giả:** Claude AI Pair Programmer (Orchestrator)

---

## 1. Vấn đề gốc (Root Cause Analysis)

1. **Lộ kết quả và cho phép Chấm/Trả bài sớm khi học sinh chưa nộp lại:**
   - Khi giáo viên bấm "Mở lại", hệ thống cũ tái sử dụng bản ghi `assignment_submissions` cũ và đổi trạng thái về `in_progress`.
   - Các nước đi của lần làm lại bị ghi đè trực tiếp lên bảng `student_attempts` và `student_progress`.
   - API không kiểm tra trạng thái trước khi chấm/trả bài, dẫn đến giáo viên vẫn thấy kết quả và trả bài được dù học sinh chưa hề bấm "Nộp bài".

2. **Lệch điểm (Học sinh thấy 11 pts, Giáo viên thấy 33 pts):**
   - **Học sinh:** Đọc điểm từ `AssignmentSubmission.total_points` (vốn được lưu ở lần 1 = 11 pts, lần 2 chưa nộp nên trường này chưa tính lại).
   - **Giáo viên:** Màn hình tiến độ giáo viên tự cộng dồn `rec.points_earned` từ `StudentProgress`. Trong khi đó, mỗi lần học sinh thử giải thế cờ, hàm `submit_attempt` lại cộng dồn hoặc ghi đè điểm vào `student_progress` (11 + 11 + 11 = 33 pts).
   - Hai giao diện đọc điểm từ hai nguồn dữ liệu khác nhau khi chưa có sự cô lập theo từng lần nộp (`attempt_no`).

---

## 2. Các giải pháp đã triển khai (7 Quy tắc Chuẩn hóa)

### Quy tắc 1 & DB Migration (`3a1f8b7c4d2e`)
- Thêm `attempt_no` (Integer default 1), `version` (Integer default 1) vào `assignment_submissions`.
- Thay thế Unique constraint cũ bằng `UniqueConstraint("assignment_id", "student_id", "attempt_no")`.
- Mở rộng Check constraint status cho phép giá trị `'reopened'`.
- Thêm cột `submission_id` vào `student_attempts` để gắn chặt nước đi vào đúng phiên làm bài.
- Khi giáo viên Mở lại: Tạo mới bản ghi `AssignmentSubmission` (`attempt_no = latest.attempt_no + 1`, `status = 'reopened'`, `version = 1`). Lần cũ giữ nguyên chỉ đọc (`read-only`).
- Khi học sinh đi nước đầu tiên của lần làm lại: Chuyển `status` từ `'reopened'` $\to$ `'in_progress'`.

### Quy tắc 2 & 3: Bỏ tự nộp, Kiểm tra trạng thái 409 Conflict & Khóa Concurrency
- Nộp bài chỉ thực hiện qua `POST /api/assignments/{id}/submit`.
- Endpoint Chấm bài / Trả bài (`/return`) dùng `with_for_update()` và kiểm tra trạng thái nghiêm ngặt:
  - Nếu `status not in ('submitted', 'graded')`: Quăng ngay lỗi **HTTP 409 Conflict**.
  - Kiểm tra `expected_version` để chống race condition ghi đè đồng thời.

### Quy tắc 4 & 5: Bảo mật thông tin khi chưa nộp bài
- **Phía Giáo viên:**
  - Bảng tiến độ hiển thị huy hiệu: *"Đang làm lại (Lần N)"*.
  - Ẩn điểm của lần chưa nộp, hiển thị điểm của lần trước đã nộp (nếu có).
  - Nút "Chấm / Xem bài" mở Modal có thanh chọn Lịch sử lần nộp (`Lần 1` vs `Lần 2`). Khi đang xem lần chưa nộp:
    - Nút "Lưu nhận xét & Trả bài" bị **vô hiệu hóa (DISABLED)**.
    - Hiển thị banner cảnh báo giải thích rõ học sinh chưa nộp bài.
- **Phía Học viên:**
  - Trong lúc làm lại, hệ thống không trả câu đúng/sai, không trả đáp án mẫu (`model_solutions`), không tính điểm live.
  - Hiển thị box xem lại kết quả và lời nhận xét của lần trước (`previous_submission`).

### Quy tắc 6: Thống nhất một nguồn điểm duy nhất
- Cả Giáo viên và Học viên đều đọc điểm bài tập từ `AssignmentSubmission.total_points`.
- Điểm BTVN không tính vào `StudentProgress` tổng của bảng xếp hạng cho đến khi bài tập được chính thức chấm và trả bài.

### Quy tắc 7: Tách dữ liệu Nguyễn Minh Triết an toàn
- Đã sao lưu dữ liệu gốc vào file `archive/backups/backup_triet_attempts_1791894650.json`.
- Tách thành 2 bản ghi riêng biệt:
  - Lần 1: `attempt_no = 1`, `status = 'returned'`, `total_points = 11`, `completed_puzzles = 1` (gắn 18 StudentAttempts ban đầu).
  - Lần 2: `attempt_no = 2`, `status = 'in_progress'`, `total_points = 0`, `completed_puzzles = 0` (gắn 5 StudentAttempts làm lại).
  - Đã reset `StudentProgress` về trạng thái 11 pts của Lần 1.

---

## 3. Các file đã thay đổi

- **Database Migration:**
  - `backend/alembic/versions/3a1f8b7c4d2e_add_submission_attempt_and_version.py`
- **Backend Models & Schemas:**
  - `backend/app/models/base.py`
  - `backend/app/models/assignment.py`
  - `backend/app/models/progress.py`
  - `backend/app/schemas/assignment.py`
- **Backend Services & API:**
  - `backend/app/services/assignment_service.py`
  - `backend/app/services/progress_service.py`
  - `backend/app/api/endpoints/assignments.py`
- **Frontend UI & API Client:**
  - `frontend/src/lib/puzzleApi.ts`
  - `frontend/src/pages/AssignmentDetail.tsx`
- **Test Suites:**
  - `backend/tests/test_homework_workflow.py` (Mới)
  - `backend/tests/test_submission_lock.py` (Cập nhật)

---

## 4. Kết quả kiểm thử (Automated Tests Verification)

Chạy test suite `test_homework_workflow.py` kiểm thử 4 kịch bản:
1. **Kịch bản 1 (Mở lại $\to$ Chưa nộp $\to$ API giáo viên ẩn kết quả & Chấm bài trả 409):** **PASS**
2. **Kịch bản 2 (API học viên bảo mật thông tin lần mới & xem previous_submission):** **PASS**
3. **Kịch bản 3 (Học viên nộp lần 2 $\to$ Mới chấm được $\to$ Trả bài $\to$ Điểm giáo viên và học sinh khớp 100%):** **PASS**
4. **Kịch bản 4 (Ghi nước đi khi bài tập đang khóa bị từ chối):** **PASS**

Frontend build test:
- `tsc -b && vite build` $\to$ **PASS (Built in 2.27s, 0 error)**
