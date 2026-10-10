# Handoff Report — CAMS-0004

## Timestamp
2026-10-10T00:00:00+07:00

## Reason
manual (User requested "resume CAMS-0004")

## Current State
- **Phase**: INTEGRATE
- **Status**: DONE
- **Progress**: Hoàn tất Sprint 2 (Classes & Enrollment). Khi vào phiên này, ledger ghi `IN_PROGRESS` nhưng đã lỗi thời — phần lớn Sprint 2 đã được triển khai ở các phiên trước (commit `d4d6e1f`). Đối chiếu lại toàn bộ checklist `docs/03_sprint_plan.md:54-66` cho thấy chỉ còn thiếu duy nhất endpoint "API lấy lịch học theo lớp", nay đã bổ sung.

## Gap Analysis (đầu phiên)
| Yêu cầu Sprint 2 | Trạng thái | Bằng chứng |
|---|---|---|
| Models `classes`, `class_enrollments` | Đã có | `backend/app/models/class_.py:22,50` |
| CRUD API `/api/classes` | Đã có | `classes.py:22,41,54,68,88` |
| API thêm/xóa học sinh vào lớp | Đã có | `classes.py:105,115,134` |
| **API lấy lịch học theo lớp** | **THIẾU → đã làm phiên này** | `classes.py:153` |
| `Classes.tsx` danh sách + filter level/tên | Đã có | `Classes.tsx:21-39` |
| `ClassForm.tsx` modal tạo/sửa | Đã có | `frontend/src/components/ClassForm.tsx` |
| `StudentList.tsx` + thêm/xóa học sinh | Đã có | `StudentList.tsx` (303 dòng) |
| `Schedule.tsx` calendar | Đã có | `Schedule.tsx` (183 dòng) |

## Completed
1. **Endpoint lịch học theo lớp** — `GET /api/classes/{class_id}/schedule`
   - Trả về: `{class_id, name, level, teacher_name, slots: [{day, time}]}`
   - Tái dùng `get_class_by_id()` nên thừa hưởng sẵn enrichment `teacher_name`.
   - 404 `Class not found` nếu lớp không tồn tại; `class_id` kiểu `uuid.UUID` nên input sai trả 422 trước khi chạm DB.
   - Dùng `get_current_user` — nhất quán với các read endpoint cùng module (`GET /{class_id}`, `GET /{class_id}/students`).
2. **Chuẩn hóa schedule** — `normalize_schedule_slots()` (pure function, tách riêng để test không cần DB)
   - `schedule_json` là JSONB tự do, nên hàm này chịu được: `None`, không phải dict, time là string đơn thay vì list, time rỗng/khoảng trắng, time không phải string.
   - Sort theo thứ tự tuần Mon→Sun (khớp `DAYS_FULL` của `Schedule.tsx`) rồi theo giờ; dedupe day+time trùng.
   - Day key lạ vẫn được giữ lại và sort xuống cuối — không âm thầm bỏ dữ liệu đã lưu.
3. **Schemas** — `ClassScheduleSlot`, `ClassScheduleRead` trong `app/schemas/class_.py`.

## Remaining
- Không còn task nào thuộc scope Sprint 2. Toàn bộ checklist đã đạt.

## Files Changed
- `backend/app/api/endpoints/classes.py` (thêm route + import schema)
- `backend/app/schemas/class_.py` (thêm 2 schema)
- `backend/app/services/class_service.py` (thêm `WEEKDAY_ORDER`, `normalize_schedule_slots`, `get_class_schedule`)
- `backend/tests/test_class_schedule.py` (mới)
- `.agents/state/CAMS-0004.json`
- `.agents/handoff/CAMS-0004-handoff.md`

## Tests
- **Unit**: `python tests/test_class_schedule.py` → 5/5 nhóm PASS (sort Mon→Sun, input lỏng/None/non-dict, dedupe, day key lạ, validate schema, route mounting).
- **Contract**: kiểm tra OpenAPI thực tế — `/api/classes/{class_id}/schedule` có mặt, response model `ClassScheduleRead` đúng shape đã chốt với user.
- **Regression**: `tests/test_puzzle_service.py` PASS, `tests/test_fen_builder.py` PASS → `app.main` import sạch, route `/{class_id}` không che `/{class_id}/schedule`.

## Blockers
- none

## Decisions Made
- **Scope "endpoint only"** (user chốt): chỉ thêm endpoint trả slot theo tuần. KHÔNG mở rộng thành dated sessions (`?from=&to=`) và KHÔNG refactor `Schedule.tsx` — trang calendar vẫn tự dựng client-side từ `getClasses({limit:100})`. Hệ quả: endpoint mới hiện chưa có consumer ở frontend, nó đáp ứng checklist Sprint 2 và phục vụ mobile/API client sau này.
- **Tách `normalize_schedule_slots()` thành pure function** thay vì nhúng trong service async — để test được theo đúng convention test hiện tại của repo (script standalone, không có conftest/pytest fixtures, không cần DB).
- **Giữ day key lạ thay vì loại bỏ** — tránh âm thầm mất dữ liệu người dùng đã lưu trong JSONB.
- **Dùng `get_current_user` thay vì `require_role`** — nhất quán với sibling read endpoints; siết quyền cho cả module là việc của task tenancy riêng (xem Pending Decisions).

## Pending Decisions
- **Tenancy scoping cho module classes** (pre-existing, cần task riêng): không endpoint read nào scope theo `center_id`/`branch_id`, nên mọi user đã đăng nhập có thể đọc bất kỳ lớp nào nếu biết UUID. Nghiêm trọng nhất: `GET /api/classes/{class_id}/students` trả `student_name` + `student_email` cho cả role `student` và `parent`. Cần user quyết định mô hình phân quyền mong muốn trước khi sửa (ảnh hưởng 6 endpoint).
- **Lệch enum level** (pre-existing, cosmetic): `ClassLevel` có `expert` nhưng `LEVEL_COLORS` ở frontend dùng `tournament`.

## Git State
- Branch: `main`
- Last commit: `9c3045e feat(classes): add class schedule endpoint (CAMS-0004)`
- Uncommitted changes: no

## Next Action
Sprint 2 đã đóng hoàn toàn. Finding tenancy ở Pending Decisions đã được mở thành task riêng **CAMS-0014** (`.agents/state/CAMS-0014.json` + `.agents/context/CAMS-0014-Context.yaml`, commit `8cb92cf`), hiện ở trạng thái `INTAKE` chờ user chốt permission model. Ứng viên task kế tiếp: CAMS-0014 (sau khi có quyết định) hoặc CAMS-0010 (state `VERIFYING`, chờ user test Teacher Review UI).
