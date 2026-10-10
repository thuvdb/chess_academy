# Handoff Report — CAMS-0014

## Timestamp
2026-10-10T22:36:00+07:00

## Reason
manual

## Current State
- **Phase**: PHASE 3 DELEGATE / IMPLEMENTATION
- **Status**: IN_PROGRESS
- **Progress**: Đã chốt kiến trúc phân quyền và triển khai các hàm helper, cập nhật service layer; đang sẵn sàng cập nhật router endpoints và unit tests.

## Completed
- Người dùng đã chốt 2 blocking decisions:
  1. Student / Parent chỉ thấy họ tên bạn học trong danh sách lớp, ẩn hoàn toàn email; chỉ giáo viên phụ trách lớp và Admin/Super Admin mới thấy email.
  2. `super_admin` xem và quản trị toàn hệ thống (cross-center), `admin` chỉ quản trị trung tâm của mình (`current_user.center_id`).
- Đã thêm `ensure_class_access` và `ensure_class_ownership` vào `backend/app/api/access.py` với quy tắc trả về 404 để không leak sự tồn tại của resource sang center khác.
- Đã sửa safe attribute lookup `getattr(puzzle, "created_by", None)` trong `ensure_puzzle_access` (`backend/app/api/access.py`).
- Đã nâng cấp `class_service.get_classes` hỗ trợ tham số `center_id` để query filtering.
- Đã nâng cấp `class_service.get_class_enrollments` hỗ trợ cờ `include_email` (nếu `False` sẽ trả `student_email: None`).

## Remaining
1. Cập nhật `backend/app/api/endpoints/classes.py`:
   - `list_classes`: nếu caller không phải `super_admin`, lọc theo `current_user.center_id`.
   - `get_class`: gọi `ensure_class_access(cls, current_user)`.
   - `create_class`: gán hoặc kiểm tra `center_id` cho role `admin` / `teacher`.
   - `update_class`: gọi `ensure_class_ownership(existing, current_user)`.
   - `delete_class`: kiểm tra quyền admin cùng center với lớp.
   - `list_class_students`: gọi `ensure_class_access`, tính toán `include_email = (is_admin or is_class_teacher)` và truyền vào service.
   - `enroll_student`: gọi `ensure_class_ownership(cls, current_user)`.
   - `unenroll_student`: gọi `ensure_class_ownership(cls, current_user)`.
   - `get_class_schedule`: gọi `ensure_class_access(cls, current_user)`.
2. Viết test regression trong `backend/tests/test_security_access.py` để verify F1, F2, F3:
   - F1: Student/Parent gọi endpoint học sinh chỉ nhận `student_email=None`.
   - F2: Khác center nhận 404 cho `get_class`, `schedule`, `students`; `list_classes` chỉ trả lớp cùng center.
   - F3: Teacher chỉ enroll/unenroll được lớp do mình phụ trách.
3. Chạy QA verification và Security review.

## Files Changed
- `backend/app/api/access.py`: Bổ sung `ensure_class_access`, `ensure_class_ownership` và fix `getattr(puzzle, "created_by", None)`.
- `backend/app/services/class_service.py`: Thêm `center_id` filter cho `get_classes` và `include_email` flag cho `get_class_enrollments`.
- `.agents/state/CAMS-0014.json`: Chuyển sang state `IN_PROGRESS` và cập nhật thông tin handoff.

## Tests
- `python -m pytest tests/test_security_access.py` (trong `backend/`): 12 passed. (Test `test_pdf_page_limit_constant` fail do hằng số `MAX_PAGES_PER_SCAN` trước đó đã nâng lên 500 cho AI scanner).
- Các unit tests mới cho CAMS-0014: chưa viết.

## Blockers
- Không có blocker. Tất cả quyết định kiến trúc đã được người dùng chốt.

## Decisions Made
1. **Roster PII (F1)**: Student / Parent chỉ thấy tên bạn học, ẩn hoàn toàn email; chỉ giáo viên phụ trách lớp và Admin/Super Admin mới thấy email.
2. **Tenancy Scoping (F2)**: `super_admin` xem toàn hệ thống, `admin` chỉ quản trị trung tâm của mình (`center_id`). Các role giáo viên, học sinh, phụ huynh cũng bị giới hạn trong trung tâm của mình. Truy cập khác center trả về 404 để không để lộ sự tồn tại của tài nguyên.
3. **Teacher Ownership (F3)**: Giáo viên chỉ được sửa thông tin, enroll và unenroll học sinh trong lớp mà mình trực tiếp phụ trách (`teacher_id == current_user.id`).

## Pending Decisions
- Không còn (tất cả các quyết định đã được giải quyết).

## Git State
- Branch: `main`
- Last commit: `3461190 chore: handoff checkpoint for CAMS-0014`
- Uncommitted changes: yes (`backend/app/api/access.py`, `backend/app/services/class_service.py`, `.agents/state/CAMS-0014.json`)

## Next Action
1. Mở `backend/app/api/endpoints/classes.py`, áp dụng `ensure_class_access`, `ensure_class_ownership`, và lọc theo `current_user.center_id`.
2. Bổ sung các test cases cho F1, F2, F3 vào `backend/tests/test_security_access.py`.
3. Chạy `python -m pytest tests/test_security_access.py` để đảm bảo toàn bộ tests pass.
4. Cập nhật trạng thái `CAMS-0014.json` sang `DONE` sau khi chạy QA & Security review.
