# Báo cáo kỹ thuật: Chuẩn hóa Quy trình Chấm & Trả BTVN & Sửa lỗi hiển thị Tiến độ Giáo viên

**Ngày thực hiện:** 13/10/2026  
**Mục tiêu:**
1. Khắc phục lỗi cột "Tiến độ (5)" bên Giáo viên chỉ hiện `1 / 5` mặc dù học viên (Nguyễn Minh Triết) đã làm đủ cả 5 thế cờ.
2. Thêm màn hình Chấm bài & Xem chi tiết lời giải (`GradingModal`) cho Giáo viên: xem từng nước đi học viên đã đi (`moves_san`), so sánh với đáp án mẫu (`model_solutions`), nhập nhận xét và trả bài.
3. Bảo mật kết quả phía Học sinh: Khi vừa nộp bài (`submitted`), không lộ đáp án đúng/sai tức thì và ẩn số câu đúng; chỉ hiển thị kết quả và nhận xét khi Giáo viên đã bấm "Trả bài" (`returned`).

---

## 1. Phân tích Nguyên nhân gốc rễ (Root Cause)

1. **Hiển thị nhầm "Số câu đúng" thành "Tiến độ làm bài":**
   - Trong `AssignmentDetail.tsx`, bảng thống kê của giáo viên lấy `s.completed` (chỉ đếm các thế cờ có `status in ('completed', 'passed', 'solved')`, tức là giải đúng) để hiển thị vào cột `Tiến độ (5)`.
   - Vì học viên Triết làm 5 câu nhưng chỉ giải đúng 1 câu, nên cột Tiến độ bị hiển thị thành `1 / 5`. Trong khi đó số câu thực tế học sinh đã thực hiện (`s.puzzleMap.size`) là `5 / 5`.

2. **Thiếu luồng Chấm bài & Trả bài (Teacher Grading & Return Workflow):**
   - Trước đây trạng thái nộp bài chỉ dừng lại ở `submitted`. Giáo viên không có giao diện xem các nước đi học sinh đã đi để đánh giá tư duy cờ.
   - Học sinh khi nộp bài lại bị lộ câu nào đúng, câu nào sai và số điểm ngay lập tức, làm mất tính chất bài kiểm tra đánh giá (Assessment).

3. **Đánh giá giải pháp tránh Over-engineering (So với tài liệu đề xuất của Claude):**
   - Claude đề xuất tạo thêm bảng `assignment_submission_items` và `assignment_submission_events`.
   - **Thực tế:** CAMS đã có bảng `student_attempts` (lưu đầy đủ `attempt_no`, `moves_san`, `moves_uci`, `points_earned`, `is_correct`, `hint_used`) và `student_progress`. Việc tạo thêm bảng là dư thừa và gây phân mảnh dữ liệu.
   - **Giải pháp tối ưu:** Mở rộng bảng `assignment_submissions` với các trường `teacher_feedback`, `teacher_adjustment`, `graded_at`, `graded_by` và thêm trạng thái `returned` vào enum.

---

## 2. Chi tiết Giải pháp & Thay đổi Code

### A. Database Migration (Alembic)
- File: `backend/alembic/versions/28f9f6aa55d2_add_grading_fields_to_submissions.py`
- Mở rộng Check Constraint `ck_assignment_submission_status_enum` hỗ trợ: `'not_started', 'in_progress', 'submitted', 'graded', 'returned'`.
- Thêm các cột:
  - `teacher_feedback` (TEXT, nullable): Lời nhận xét của giáo viên.
  - `teacher_adjustment` (INTEGER, default 0): Điểm điều chỉnh / cộng thưởng của giáo viên.
  - `graded_at` (TIMESTAMP WITH TIME ZONE, nullable): Thời gian trả bài.
  - `graded_by` (UUID FK users, nullable): Giáo viên thực hiện chấm bài.

### B. Backend API & Services
- **`backend/app/models/base.py` & `assignment.py`:** Thêm `RETURNED = "returned"` vào `SubmissionStatus`, khai báo các trường chấm bài.
- **`backend/app/services/assignment_service.py`:**
  - `get_student_submission_detail(db, assignment_id, student_id)`: Trả về trạng thái submission và danh sách toàn bộ thế cờ, bao gồm đáp án mẫu và toàn bộ lượt giải của học sinh (`moves_san`, `moves_uci`, `is_correct`, `points_earned`).
  - `grade_and_return_assignment(db, assignment_id, student_id, teacher_id, feedback, adjustment)`: Chuyển trạng thái sang `returned`, cập nhật điểm số và ghi nhận xét.
  - Cập nhật `is_assignment_locked_for_student` khóa bài khi status in (`submitted`, `graded`, `returned`).
- **`backend/app/api/endpoints/assignments.py`:**
  - `GET /api/assignments/{assignment_id}/submissions/{student_id}`: API xem chi tiết bài làm của học sinh (phân quyền Teacher/Admin hoặc chính học sinh đó).
  - `POST /api/assignments/{assignment_id}/submissions/{student_id}/return`: API chấm và trả bài cho học sinh.

### C. Frontend UI/UX
- **`frontend/src/lib/puzzleApi.ts`:**
  - Cập nhật interface `AssignmentSubmission`, thêm `StudentSubmissionDetail`, `SubmissionDetailItem`.
  - Thêm hàm `getStudentSubmissionDetail` và `gradeAndReturnAssignment`.
- **`frontend/src/pages/AssignmentDetail.tsx`:**
  1. **Bảng Tiến độ Giáo viên:**
     - Tách bạch 2 cột rõ ràng: **Tiến độ làm ({totalPuzzles})** (`5 / 5` thế cờ) và **Giải đúng** (`1 / 5` thế cờ).
     - Thêm nút **"Chấm / Xem bài"** dẫn tới `GradingModal`.
  2. **Màn hình Chấm bài cho Giáo viên (`GradingModal`):**
     - Hiển thị danh sách các thế cờ kèm icon đúng / chưa đúng.
     - Tích hợp bàn cờ `Chessboard` xem FEN xuất phát của từng thế cờ.
     - Hiển thị dãy nước đi của học sinh (`moves_san`) và đối chiếu trực tiếp với đáp án mẫu (`model_solutions`).
     - Khung nhập nhận xét của Thầy/Cô (`teacherFeedback`) và điểm điều chỉnh (`teacherAdjustment`).
     - Nút "Lưu nhận xét & Trả bài cho học sinh 📝".
  3. **Bảo mật kết quả phía Học sinh:**
     - Khi `submitted` (chưa trả bài): Ẩn kết quả đúng/sai trên từng câu, ẩn điểm số; hiển thị "Đã nộp bài chính thức 🔒 — Chờ giáo viên chấm & trả bài".
     - Khi `returned`: Hiển thị thông báo "Đã có kết quả 🎉", hiển thị điểm chính thức và khối nhận xét của Thầy/Cô sang trọng, mở chi tiết câu đúng/sai để học sinh học hỏi.

---

## 3. Kết quả Kiểm thử (Verification)

1. **Kiểm tra Backend API:**
   - Chạy test script trên dữ liệu thật của học sinh Nguyễn Minh Triết:
     - Submission ID: `c9c4383b-6940-430b-b83f-6ec5bba69e23`, Status: `submitted`.
     - Lấy đủ 5 thế cờ, nước đi SAN của học sinh được trích xuất chính xác (ví dụ Item #2: `['Rxe4+', 'Kf8', 'Qd5']`).
2. **Kiểm tra Frontend Build:**
   - Chạy `npm run build` trên container `cams_frontend`: TypeScript check pass 100%, Vite build thành công không lỗi.
