# Báo cáo sửa lỗi: Học sinh bị thiếu thế cờ trong Bài tập về nhà (3/5 thế cờ)

**Ngày thực hiện:** 2026-10-13  
**Trạng thái:** `HOÀN THÀNH (DONE)`

---

## 1. Hiện tượng & Vấn đề phát hiện
- Giáo viên giao bài tập **"Các đòn chiến thuật"** gồm 5 thế cờ:
  1. `chess-tactics-for-students-John Bain-016-017.pdf - Trang 1 / Bàn 1`
  2. `chess-tactics-for-students-John Bain-015-015.pdf - Trang 1 / Bàn 0`
  3. `chess-camp-vol-3-checkmates-with-many-pieces... Trang 1 / Bàn 3`
  4. `chess-camp-vol-3-checkmates-with-many-pieces... Trang 4 / Bàn 2`
  5. `chess-camp-vol-3-checkmates-with-many-pieces... Trang 5 / Bàn 1`
- Khi tài khoản **Giáo viên** vào xem: Hiển thị đầy đủ **5 thế cờ**.
- Khi tài khoản **Học sinh (Nguyễn Minh Triết)** vào làm:
  - Chỉ nhìn thấy **3 thế cờ** (#3, #4, #5).
  - Làm xong 3 bài thì hệ thống báo hoàn thành bài tập, điều hướng quay lại trang bài tập.
  - Trên trang bài tập hiển thị: `Tiến độ làm bài: 3 / 5 thế cờ`, `Trạng thái: Đang thực hiện (2 bài chưa làm)`, nhưng danh sách bên dưới chỉ hiện `Danh sách thế cờ cần giải (3)`. Học sinh không có cách nào làm tiếp 2 bài còn lại.

---

## 2. Nguyên nhân gốc rễ (Root Cause)
1. **Lỗi logic tải bài tập phía Frontend:**
   - Cả `AssignmentDetail.tsx` và `Practice.tsx` trước đây không tải danh sách bài tập từ bài tập cụ thể, mà gọi `getPuzzles({ limit: 100 })` (API thư viện thế cờ chung) rồi lọc theo `asm.puzzle_ids`.
2. **Cơ chế lọc quyền hạn phía Backend API (`GET /puzzles`):**
   - Trong `backend/app/api/endpoints/puzzles.py`:
     ```python
     # Học sinh chỉ thấy bài đã chứng minh được lời giải
     verified_only = current_user.role == "student"
     ```
   - 2 thế cờ đầu tiên trích xuất từ sách chiến thuật John Bain là dạng bài **bắt quân/chiếu rút (tactic)**, không phải bài chiếu hết cưỡng bức, nên có cờ `solution_verified = False`.
   - Khi tài khoản giáo viên gọi `GET /puzzles`: `verified_only = False` $\to$ Nhận đủ 5 thế cờ.
   - Khi tài khoản học sinh gọi `GET /puzzles`: Backend tự động áp dụng `verified_only = True` $\to$ **Lọc bỏ 2 bài chiến thuật unverified**, học sinh chỉ nhận được 3 bài mate.
3. **Lỗ hổng về phân trang:**
   - Việc gọi `getPuzzles({ limit: 100 })` sẽ bỏ sót bất kỳ thế cờ nào ngoài phạm vi 100 bài đầu tiên của thư viện.

---

## 3. Giải pháp đã thực hiện

### 3.1 Backend: Cung cấp Endpoint chuyên dụng cho Bài tập
- **File `backend/app/services/assignment_service.py`:**
  - Thêm hàm `get_assignment_puzzles(db, assignment_id)`:
    - Truy vấn trực tiếp các `Puzzle` (kèm `solutions`) theo danh sách `puzzle_ids` của Assignment.
    - Bảo toàn đúng thứ tự các thế cờ mà giáo viên đã sắp xếp.
    - Không lọc theo `solution_verified`, vì các thế cờ trong bài tập đã được chính giáo viên chọn lọc và giao cho lớp.
- **File `backend/app/api/endpoints/assignments.py`:**
  - Thêm endpoint `GET /api/assignments/{assignment_id}/puzzles` trả về `list[PuzzleRead]`.
  - Cung cấp cho cả học sinh và giáo viên trong lớp.

### 3.2 Frontend: Tải thế cờ trực tiếp từ Assignment
- **File `frontend/src/lib/puzzleApi.ts`:**
  - Thêm hàm `getAssignmentPuzzles(assignmentId: string): Promise<PuzzleItem[]>`.
- **File `frontend/src/pages/AssignmentDetail.tsx`:**
  - Thay thế việc gọi `getPuzzles({ limit: 100 })` bằng `getAssignmentPuzzles(assignmentId)`.
  - Học sinh nhận đủ 100% các thế cờ trong bài tập (hiển thị 5/5 thế cờ).
- **File `frontend/src/pages/Practice.tsx`:**
  - Thay thế việc gọi `getPuzzles({ limit: 100 })` bằng `getAssignmentPuzzles(assignmentIdParam)`.
  - Danh sách bài tập nạp đủ 5 thế cờ, giúp học sinh giải tuần tự từ bài #1 đến bài #5 mà không bị kết thúc sớm ở bài #3.

---

## 4. Kết quả kiểm tra
1. **Kiểm tra API trực tiếp với Token Học sinh:**
   - Chạy script kiểm tra với tài khoản học sinh: `GET /api/assignments/06369618-7d0d-4cfe-b5ba-722437aeeca4/puzzles`
   - Kết quả: **Nhận đủ 5/5 thế cờ**, bao gồm cả 2 thế cờ chiến thuật John Bain.
2. **Frontend Typecheck & Build:**
   - `docker exec cams_frontend npm run build` $\to$ **Exit code 0 (thành công).**
