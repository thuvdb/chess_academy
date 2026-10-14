# Báo cáo xử lý sự cố: Lỗi hiển thị 8/7 thế cờ và nhân đôi điểm số học viên

## 1. Mục tiêu và phạm vi công việc
Giải quyết dứt điểm phản ánh của người dùng:
1. Giao diện giáo viên hiển thị học viên Triết hoàn thành **8 / 7** thế cờ (trong khi bài tập chỉ có 7 thế cờ).
2. Học viên Triết đạt **151 pts** trong khi giáo viên giải hết 7/7 chỉ đạt **77 pts**.
3. Khắc phục nguy cơ cộng dồn điểm số khi giải lại bài tập.

---

## 2. Nguyên nhân cốt lõi (Root Cause Analysis)

### 2.1. Lỗi hiển thị 8 / 7 thế cờ (Race condition nhân bản bản ghi)
- **Truy vấn thực tế DB:** Học viên Triết khi nộp thế cờ `1cc8b08b-7ed4-4029-b552-c7235caf9257` vào ngày 10/10/2026 lúc `18:39:41`, trình duyệt gửi **2 request đồng thời** chỉ cách nhau **1 mili-giây** (`18:39:41.624841` và `18:39:41.625714`).
- **Lỗ hổng Database & Backend:**
  - Bảng `student_progress` chưa có ràng buộc duy nhất (`UniqueConstraint`) trên bộ `(student_id, puzzle_id, assignment_id)`.
  - Hàm `get_or_create_progress` kiểm tra bằng `SELECT` thông thường, cả 2 request đồng thời đều thấy chưa có bản ghi nên đã tạo ra **2 bản ghi giống hệt nhau** (`7c1aa702` và `5c36d497`).
- **Lỗ hổng Frontend:**
  - Trong [AssignmentDetail.tsx](file:///c:/ProjectAI/chess_academy/frontend/src/pages/AssignmentDetail.tsx), thuật toán tính số bài hoàn thành duyệt qua toàn bộ mảng `progressData` và tăng `completed += 1` mà không lọc theo `Set(puzzle_id)` duy nhất. Do có 8 bản ghi (1 bản ghi bị nhân đôi) $\to$ giao diện hiển thị thành **8 / 7**.

### 2.2. Lỗi học viên Triết 151 pts vs Thầy giáo 77 pts (Cộng dồn điểm khi làm lại)
- Mỗi thế cờ của bài tập có điểm số cơ bản là **11 pts** (dựa trên puzzle rating). Giáo viên giải đúng 7 thế cờ $\to$ $7 \times 11 = \mathbf{77\text{ pts}}$.
- Ở phiên bản code cũ (trước ngày 11/10/2026), hàm `submit_attempt` mỗi lần nộp đúng đều thực hiện `progress.points_earned += points` mà không kiểm tra bài đã giải trước đó hay chưa.
- Do đó:
  - 1 thế cờ bị nhân đôi $\to$ $12 + 12 = 24\text{ pts}$.
  - 5 thế cờ Triết giải lại lần 2 $\to$ cộng dồn $12 + 11 = 23\text{ pts/thế cờ}$ $\to$ $5 \times 23 = 115\text{ pts}$.
  - 1 thế cờ Triết giải 1 lần $\to$ $12\text{ pts}$.
  - Tổng cộng: $24 + 115 + 12 = \mathbf{151\text{ pts}}$.

---

## 3. Các thay đổi đã thực hiện

### 3.1. Frontend (`frontend/src/pages/AssignmentDetail.tsx`)
- Dùng `Map<string, ProgressRecord>` gom nhóm theo `puzzle_id` để loại bỏ hoàn toàn các bản ghi trùng lặp do mạng hoặc race condition.
- Dùng `Set<string>` để tính `completedSet.size`, đảm bảo tiến độ không bao giờ vượt quá tổng số bài tập (`totalPuzzles`).
- Tính tổng điểm học viên bằng cách chỉ lấy điểm số tốt nhất của từng thế cờ duy nhất.

### 3.2. Backend API & Services
- `backend/app/api/endpoints/assignments.py`:
  - Trong `get_assignment_progress`, thêm bước deduplicate gom nhóm theo `(student_id, puzzle_id)` trước khi trả dữ liệu về client.
- `backend/app/services/progress_service.py`:
  - Cập nhật `get_or_create_progress`: Phân định rõ `assignment_id.is_(None)` khi luyện tập tự do và dùng `scalars().first()` an toàn.
  - Cập nhật `submit_attempt`: Điểm số gán bằng `progress.points_earned = points` (hoặc `max`), **không cộng dồn lũy kế (`+=`)** khi giải lại nhiều lần.

### 3.3. Database & Migration
- Dọn dẹp bản ghi trùng lặp `5c36d497-33f8-47b1-917f-5255ee9ce2dc` của Triết trong DB, đồng thời chuẩn hóa điểm số về đúng 11 pts/thế cờ.
- Tạo chỉ mục duy nhất trong PostgreSQL:
  ```sql
  CREATE UNIQUE INDEX uq_student_puzzle_assignment
  ON student_progress (student_id, puzzle_id, assignment_id) NULLS NOT DISTINCT;
  ```
- Tạo và chạy migration Alembic `e819fa2c4d11_add_unique_index_student_progress.py`.

---

## 4. Kết quả sau khi khắc phục

- **Dữ liệu bài tập trên giao diện giáo viên:**
  - Học viên **Nguyen Van Teacher**: Tiến độ **7 / 7** | Tổng điểm: **77 pts**
  - Học viên **Nguyễn Minh Triết**: Tiến độ **7 / 7** | Tổng điểm: **77 pts**
- **Kiểm thử tự động:**
  - Frontend Build (`npm run build`): **0 errors, build thành công**.
  - Backend Unit Tests: **All tests passed (100%)**.
