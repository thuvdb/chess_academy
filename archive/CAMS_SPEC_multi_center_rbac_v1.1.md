# CAMS – Đặc tả module Đa trung tâm, Phân quyền (RBAC), Cài đặt, Puzzle Bank, AI Scanner (v1.1)

> Tài liệu dành cho AI Agent (Antigravity IDE) triển khai. Đọc toàn bộ trước khi viết code.
> Dự án: `chess_academy` – backend Python (FastAPI) + PostgreSQL, frontend React (TypeScript), mobile Expo.
> Ngôn ngữ giao diện: tiếng Việt. Mã nguồn, tên bảng/cột/API: tiếng Anh.

---

## 0. Quy tắc làm việc cho Agent

1. **Không phỏng đoán cấu trúc code.** Trước khi sửa, đọc các file thực tế: `backend/app/models/*`, `backend/app/api/endpoints/*`, `backend/app/services/*` (đặc biệt `progress_service.py`, `puzzle_service.py`), `backend/app/seed.py`, `frontend/src/**`. Nếu spec này mâu thuẫn với code hiện có, **dừng lại và báo cáo**, không tự quyết.
2. **Mọi kiểm tra quyền thực hiện ở Backend.** Ẩn nút ở Frontend chỉ là UX, không phải bảo mật.
3. **Không hard-code** danh sách nghiệp vụ (xem mục 6). Dùng bảng DB + màn hình Cài đặt.
4. **Mỗi thay đổi schema = 1 migration (Alembic)**, có script backfill dữ liệu cũ; chạy dry-run trước, real-run sau; sao lưu `pg_dump` trước khi chạy.
5. Commit theo quy ước `CAMS-xxxx: <mô tả>`. Mỗi nhóm việc ở mục 9 là một commit riêng.
6. Không commit file trong `backend/storage/scans`, file `.env`, dump DB.
7. Viết test cho từng quy tắc phân quyền ở mục 3 (xem mục 8).

---

## 1. Vai trò (Roles)

| Role | Thuộc trung tâm? | Mô tả |
|---|---|---|
| `super_admin` | Không (`center_id = NULL`) | Chủ hệ thống, đứng trên mọi trung tâm |
| `center_admin` | Có (bắt buộc) | Quản trị viên của đúng 1 trung tâm |
| `teacher` | Có (bắt buộc) | Giáo viên của 1 trung tâm |
| `student` | Có (bắt buộc) | Học viên của 1 trung tâm |
| `parent` | Có (bắt buộc) | Phụ huynh, liên kết với ≥1 học viên cùng trung tâm |

Ràng buộc dữ liệu:
- `center_id IS NULL` **chỉ hợp lệ** với `super_admin`. Mọi role khác bắt buộc có `center_id` (CHECK constraint + validate ở service).
- Một `parent` chỉ được liên kết với `student` **cùng `center_id`**.
- Tài khoản test cũ có `center_id` trống (`teacher@cams.vn`, `student@cams.vn`…) phải được gán vào một trung tâm demo trong migration backfill (hoặc đánh dấu rõ là dữ liệu test và xóa khỏi môi trường thật).

> Lưu ý: nếu code hiện tại đang dùng tên role là `admin` thay vì `center_admin`, đổi tên bằng migration và cập nhật toàn bộ chỗ dùng; liệt kê các chỗ đã đổi trong báo cáo.

---

## 2. Mô hình dữ liệu (tối thiểu, đối chiếu với model hiện có)

Thêm/đảm bảo các bảng sau. Tất cả bảng nghiệp vụ có `center_id` (trừ bảng toàn cục) và `created_at`, `updated_at`, `created_by`.

- `centers`: `id`, `name`, `code` (unique), `address`, `phone`, `email`, `logo_url`, `is_active`.
- `users`: `id`, `email` (unique), `password_hash`, `full_name`, `phone`, `role`, `center_id` (nullable theo mục 1), `is_active`, `must_change_password`.
- `parent_student_links`: `parent_id`, `student_id`, `relationship` (lấy từ danh mục mục 6), unique `(parent_id, student_id)`.
- `courses`: `id`, `center_id`, `name`, `description`, `level_id` (FK danh mục), `is_active`.
- `classes`: `id`, `center_id`, `course_id`, `name`, `teacher_id`, `schedule` (JSON), `capacity`, `start_date`, `end_date`, `status`.
- `class_enrollments`: `id`, `class_id`, `student_id`, `status` (`active|transferred|removed`), `enrolled_at`, `left_at`, `transferred_from_class_id` (nullable). **Giữ lịch sử**, không xóa cứng khi remove/điều chuyển lớp.
- `tuition_packages`: `id`, `center_id`, `course_id`, `name`, `price`, `currency`, `sessions_count` hoặc `duration_months`, `is_active`. `course_id` phải thuộc cùng `center_id`. **Chỉ lưu gói**, không có bảng thu tiền, hóa đơn hay công nợ.
- `puzzles` (Puzzle Bank): thêm `center_id`, `owner_id` (người tạo: teacher, center_admin hoặc super_admin), `is_active` (ẩn/khóa), `deleted_at`. Phạm vi xem cố định là toàn trung tâm (mục 5.1), không có cột `visibility`.
- `scan_jobs` / `scanned_books` (AI Scanner): thêm `center_id` (nullable cho super_admin), `uploaded_by`.
- Danh mục cấu hình (mục 6): `catalog_items` (`id`, `center_id` nullable, `catalog_type`, `code`, `label`, `sort_order`, `is_active`).
- `audit_logs`: `id`, `actor_id`, `center_id`, `action`, `entity`, `entity_id`, `before`, `after`, `created_at`.

---

## 3. Ma trận phân quyền (nguồn sự thật duy nhất)

Ký hiệu: ✅ được · 🔒 chỉ trong trung tâm của mình · 👤 chỉ đối tượng do chính mình tạo · ❌ cấm.

| Chức năng | super_admin | center_admin | teacher | student | parent |
|---|---|---|---|---|---|
| Tạo/sửa/khóa **Trung tâm** | ✅ | ❌ | ❌ | ❌ | ❌ |
| Tạo **center_admin** | ✅ | ❌ | ❌ | ❌ | ❌ |
| Tạo **teacher** | ✅ (chọn trung tâm) | 🔒 | ❌ | ❌ | ❌ |
| Tạo **student** và **parent** (chỉ hai role này được tạo) | ✅ (chọn trung tâm) | 🔒 | ❌ | ❌ | ❌ |
| Gắn parent ↔ student | ✅ | 🔒 | ❌ | ❌ | ❌ |
| Tạo/sửa/xóa **Khóa học** | ✅ | 🔒 | ❌ (chỉ xem lớp được phân công) | ❌ | ❌ |
| Tạo **Lớp**, phân công giáo viên vào lớp | ✅ | 🔒 | ❌ | ❌ | ❌ |
| Thêm / xóa / sửa học viên trong lớp, điều chuyển lớp | ✅ | 🔒 | ❌ | ❌ | ❌ |
| Tạo/sửa **Gói học phí** | ✅ | 🔒 (không sửa được của trung tâm khác) | ❌ | ❌ | ❌ |
| Tạo/sửa/xóa **Puzzle** trong Puzzle Bank | ✅ | ✅ 🔒 (mọi puzzle của trung tâm mình, kể cả của teacher) | 👤 (chỉ puzzle của mình) | ❌ | ❌ |
| Ẩn/khóa puzzle | ✅ | ✅ 🔒 (kể cả của teacher) | 👤 | ❌ | ❌ |
| Xem puzzle trong Puzzle Bank | ✅ | 🔒 | 🔒 (cả trung tâm) | ❌ | ❌ |
| **Upload sách / quét** trong AI Scanner | ✅ | ✅ 🔒 | ❌ | ❌ | ❌ |
| Giao bài tập cho lớp | ✅ | 🔒 | 🔒 lớp mình dạy | ❌ | ❌ |
| Làm bài, xem rating bản thân | ❌ | ❌ | ❌ | ✅ | ❌ |
| Xem tiến độ/gói học phí của con | ❌ | ❌ | ❌ | ❌ | ✅ chỉ con đã liên kết |
| Menu **Cài đặt** | ✅ (cấp hệ thống) | ✅ (cấp trung tâm) | ✅ (cá nhân) | ✅ (cá nhân) | ✅ (cá nhân) |

Quy tắc chung:
- **Cách ly dữ liệu (tenant isolation):** mọi truy vấn của role khác `super_admin` phải bị ép `WHERE center_id = current_user.center_id`. Cài ở một chỗ duy nhất (dependency/repository base), **không** rải rác từng endpoint.
- Truy cập đối tượng của trung tâm khác trả **404** (không lộ sự tồn tại), không phải 403.
- `center_admin` **không được** tự đổi `center_id` của bất kỳ đối tượng nào, và không được tạo user có role `super_admin` hoặc `center_admin`.
- Payload tạo user bị validate whitelist role theo người gọi: `center_admin` chỉ được tạo `teacher|student|parent`. `teacher`, `student`, `parent` không có quyền tạo tài khoản nào, và không có tự đăng ký.
- Điều chuyển học viên chỉ trong **cùng trung tâm** (giữa các lớp). Chuyển người dùng sang trung tâm khác nằm ngoài phạm vi tài liệu này.
- Mọi hành động tạo/sửa/xóa/điều chuyển ghi `audit_logs`.

### Cách cài đặt kỹ thuật
- Tạo module `app/core/permissions.py` chứa: enum `Role`, hàm `require_roles(...)`, hàm `scope_query_to_center(query, user)`, hàm `assert_same_center(user, obj)`, hàm `assert_owner_or_admin(user, obj)` (cho phép chủ sở hữu, center_admin cùng trung tâm, hoặc super_admin).
- Endpoint chỉ khai báo dependency, ví dụ `Depends(require_roles(Role.SUPER_ADMIN, Role.CENTER_ADMIN))`.
- Token JWT chứa `sub`, `role`, `center_id`; nhưng **role/center_id luôn được xác nhận lại từ DB** khi xử lý yêu cầu nhạy cảm.

---

## 4. Quản trị trung tâm, người dùng, lớp học, học phí

### 4.1 Super Admin
- Trang **Quản lý Trung tâm**: danh sách, tạo, sửa, khóa/mở khóa (soft-disable, không xóa cứng).
- Trang **Quản lý Admin trung tâm**: tạo `center_admin`, gán trung tâm, đặt mật khẩu tạm (`must_change_password = true`), khóa/mở, reset mật khẩu.
- Có bộ lọc theo trung tâm ở mọi danh sách (users, lớp, puzzle…) để xem toàn hệ thống.

### 4.2 Center Admin (chỉ trong trung tâm của mình)
- **Người dùng:** tạo/sửa/khóa teacher, student, parent. Học viên và phụ huynh **chỉ** `center_admin` hoặc `super_admin` được tạo. Form tạo parent bắt buộc chọn ≥1 student của trung tâm.
- **Khóa học:** CRUD khóa học.
- **Lớp học:** tạo lớp từ khóa học, phân công giáo viên (giáo viên phải cùng trung tâm), đặt sĩ số tối đa.
- **Học viên trong lớp:** thêm, xóa, sửa thông tin ghi danh, **điều chuyển** sang lớp khác (ghi `transferred_from_class_id`, đóng bản ghi cũ `status=transferred`, tạo bản ghi mới). Kiểm tra sĩ số, không trùng ghi danh.
- **Gói học phí:** CRUD gói gắn với khóa học của trung tâm mình. Backend từ chối nếu `course.center_id != current_user.center_id`. Hệ thống **chỉ lưu gói**, không quản lý thu tiền hay công nợ.
- **Puzzle Bank:** tạo/sửa/xóa/ẩn-khóa mọi puzzle của trung tâm mình (mục 5.1).

### 4.3 Hiển thị trung tâm trên UI
- Header (cạnh avatar) của center_admin/teacher/student/parent hiển thị **tên trung tâm**.
- super_admin hiển thị nhãn "Toàn hệ thống" và có bộ chọn trung tâm để lọc.

---

## 5. Puzzle Bank, chấm điểm và AI Scanner

### 5.1 Puzzle Bank
- **Phạm vi xem (đã chốt):** mọi puzzle trong Puzzle Bank hiển thị cho **cả trung tâm** (teacher và center_admin của trung tâm đó đều xem và dùng để giao bài). Không chia sẻ xuyên trung tâm. Không có thiết lập cấu hình cho phần này.
- **Teacher:** tạo / sửa / xóa / ẩn **chỉ puzzle có `owner_id = mình`**. Sửa/xóa puzzle của giáo viên khác → 403 nếu cùng trung tâm, 404 nếu khác trung tâm. Nói cách khác, trong phạm vi teacher, chỉ chủ sở hữu mới sửa/xóa.
- **Center admin:** tạo / sửa / xóa / ẩn-khóa (`is_active=false`) **mọi puzzle của trung tâm mình**, kể cả puzzle của teacher. Puzzle trung tâm khác → 404. Khi sửa hoặc xóa puzzle do người khác sở hữu, ghi `audit_logs` với `before`/`after`.
- **Super admin:** toàn quyền trên mọi puzzle.
- Puzzle bị ẩn/khóa không xuất hiện trong danh sách chọn để giao bài mới, nhưng bài đã giao và lịch sử chấm điểm vẫn giữ nguyên.
- Xóa puzzle đã được giao bài hoặc đã có bài nộp: **soft-delete** (`deleted_at`), giữ nguyên lịch sử chấm điểm.

### 5.2 Định dạng đáp án Puzzle
- Đáp án mẫu (Master Solution) là chuỗi nước đi UCI **luân phiên**: học viên → máy → học viên …, ví dụ `e2e4, e7e5, g1f3`. Nước của máy do giáo viên nạp sẵn và được hệ thống tự phát lại sau khi học viên đi đúng.
- Lý do không dùng engine đi thay máy: puzzle là tình huống chiến thuật đã định sẵn; engine sẽ né đòn và phá ý đồ bài.
- Hiện UI nhập một **nhánh chính (main line)**. Việc hỗ trợ nhiều nhánh (Variation Tree) là tính năng giai đoạn sau; **Agent phải kiểm tra trong DB/model xem đã lưu được nhiều nhánh chưa** thay vì giả định.

### 5.3 Chấm điểm
- **Cấp 1 (đã có):** khớp đáp án mẫu → đúng.
- **Cấp 2 (đã tích hợp Stockfish, không làm lại):** nước đi ngoài đáp án mẫu được Stockfish đánh giá; chấp nhận nếu giữ được ưu thế, nếu tụt điểm nhiều thì tính sai và phân loại mức sai lầm. Agent **không viết lại** phần này. Nhiệm vụ của Agent chỉ gồm:
  1. Đọc code đang gọi Stockfish (đường dẫn engine, độ sâu/thời gian, ngưỡng centipawn, cách xử lý mate) và tóm tắt lại trong báo cáo.
  2. Đảm bảo logic chấm vẫn đúng khi puzzle thuộc trung tâm nào, không ảnh hưởng bởi thay đổi phân quyền.
  3. Nếu các tham số (độ sâu, thời gian, ngưỡng chấp nhận nước thay thế, ngưỡng phân loại sai lầm) đang **hard-code**, chuyển chúng sang bảng `settings` (mục 6) với giá trị mặc định bằng đúng giá trị hiện tại, để super_admin chỉnh trong tab Cài đặt (mục 7.1). Giữ nguyên hành vi mặc định.
- **Rating kiểu Elo** cho cả học viên và puzzle; K-factor theo trình độ (ví dụ K=32 với rating thấp, K=16 với rating cao); điểm thưởng cơ bản = `rating_puzzle / 100`, trừ 5 điểm nếu dùng gợi ý. Các hằng số này đọc từ cấu hình (mục 6), giá trị trên chỉ là mặc định. Agent đối chiếu với `progress_service.py`/`puzzle_service.py` và báo lại nếu khác.
- Bảng xếp hạng mặc định theo trung tâm.

### 5.4 AI Scanner
- Chỉ `super_admin` và `center_admin` được: upload sách (PDF), chạy quét, sửa/duyệt kết quả quét, xóa job quét.
- `teacher`, `student`, `parent`: **chặn hoàn toàn** ở Backend (403), ẩn menu ở Frontend.
- `center_admin`: job và sách thuộc `center_id` của mình, không xem/xóa job trung tâm khác.
- Giới hạn upload cấu hình được (dung lượng tối đa, định dạng cho phép, số trang tối đa) trong Cài đặt, kiểm tra cả ở Backend.
- Puzzle sinh ra từ quét thuộc về trung tâm; `owner_id` là **người duyệt/xuất bản** kết quả.
- File lưu ở storage cục bộ theo thư mục `scans/<center_id>/<job_id>/`; tên file được sinh lại (không dùng tên gốc người dùng), kiểm tra MIME và magic bytes, không phục vụ file trực tiếp mà qua endpoint có kiểm tra quyền.

---

## 6. Ràng buộc: KHÔNG hard-code, cấu hình qua giao diện

Các danh sách sau **không** được viết cứng trong code hoặc enum frontend. Lưu trong `catalog_items` (và bảng `settings` cho giá trị đơn), có seed mặc định bằng migration/seed nhưng người dùng có quyền được **thêm / sửa / sắp xếp / vô hiệu hóa**:

| Danh mục (`catalog_type`) | Ví dụ giá trị seed | Ai quản lý |
|---|---|---|
| `course_level` (cấp độ khóa học) | Cơ bản, Nâng cao… | center_admin (theo trung tâm); super_admin (mặc định hệ thống) |
| `puzzle_theme` (chủ đề chiến thuật) | Chiếu hết, Bắt đôi, Ghim… | super_admin (hệ thống); center_admin (bổ sung riêng trung tâm) |
| `puzzle_difficulty_band` | khoảng rating → nhãn | super_admin |
| `parent_relationship` | Bố, Mẹ, Người giám hộ | super_admin / center_admin |
| `class_status`, `enrollment_status` (nhãn hiển thị) | Đang học, Bảo lưu… | center_admin |
| `currency` | VND | center_admin |
| `class_schedule_slot` (khung giờ) | tự định nghĩa | center_admin |

Giá trị đơn trong `settings` (có phạm vi `system` hoặc `center`):
- Rating khởi tạo, hệ số K và ngưỡng K, điểm thưởng/phạt gợi ý, số lần làm lại bài tập về nhà, tham số Stockfish (độ sâu/thời gian, ngưỡng chấp nhận nước thay thế, ngưỡng phân loại sai lầm), giới hạn upload AI Scanner, độ dài tối thiểu mật khẩu, thời hạn mật khẩu tạm.
- Quy tắc đọc: giá trị cấp trung tâm ghi đè giá trị hệ thống (nếu mục đó cho phép ghi đè); nếu không có thì dùng giá trị hệ thống; nếu không có nữa dùng default trong seed.
- Mã/khóa kỹ thuật (`code`) của mục danh mục là bất biến sau khi tạo; chỉ `label` được đổi. Mục đã được dùng thì **vô hiệu hóa** thay vì xóa.
- API trả danh mục theo ngữ cảnh người gọi (hệ thống + trung tâm của họ). Frontend render dropdown từ API, không có mảng literal.

---

## 7. Menu Cài đặt (Settings) theo quyền – giao diện dạng Tab

Thêm mục **Cài đặt** vào sidebar. Tab hiển thị **tùy role**; role không có quyền không thấy tab **và** API tương ứng trả 403.

### 7.1 Super Admin – "Cài đặt hệ thống"
1. **Chung:** tên hệ thống, logo, ngôn ngữ, múi giờ mặc định.
2. **Trung tâm:** danh sách trung tâm và cấu hình mặc định áp cho trung tâm mới.
3. **Danh mục hệ thống:** quản lý các `catalog_type` cấp hệ thống (mục 6).
4. **Chấm điểm & Rating:** hệ số K, điểm thưởng, ngưỡng, và các tham số Stockfish (mục 5.3).
5. **AI Scanner:** giới hạn upload, định dạng, cấu hình engine OCR/AI.
6. **Bảo mật:** chính sách mật khẩu, thời gian phiên, nhật ký hoạt động (audit log toàn hệ thống).

### 7.2 Center Admin – "Cài đặt trung tâm"
1. **Thông tin trung tâm:** tên, địa chỉ, liên hệ, logo.
2. **Danh mục trung tâm:** cấp độ khóa học, khung giờ, trạng thái, quan hệ phụ huynh (thêm/sửa/ẩn).
3. **Học phí:** tiền tệ và quy tắc làm tròn; liên kết sang màn quản lý gói học phí.
4. **Bài tập & Puzzle:** số lần làm lại, chủ đề puzzle riêng trung tâm.
5. **AI Scanner:** hạn mức/ưu tiên cho trung tâm (trong giới hạn hệ thống).
6. **Nhật ký:** audit log của trung tâm.

### 7.3 Teacher / Student / Parent – "Cài đặt cá nhân"
- Tab **Hồ sơ** (tên, số điện thoại, ảnh đại diện), tab **Bảo mật** (đổi mật khẩu), tab **Thông báo**. Teacher có thêm tab **Bài tập mặc định** (độ khó, chủ đề ưa thích). Parent có tab **Con của tôi** (chỉ xem liên kết).

### 7.4 Yêu cầu UI chung
- Component Tabs dùng chung; mỗi tab lưu độc lập, có trạng thái đang lưu/lỗi/thành công, xác nhận khi thoát với dữ liệu chưa lưu.
- Có trạng thái trống, tải, lỗi; responsive; mọi chuỗi qua file i18n.
- Danh mục (mục 6) có giao diện bảng: thêm, sửa nhãn, kéo thả sắp xếp, bật/tắt.

---

## 8. Tiêu chí nghiệm thu và kiểm thử

Viết test tự động (pytest cho API; Playwright hoặc tương đương cho UI chính). Tối thiểu:

**Phân quyền & cách ly**
- [ ] `center_admin` gọi API tạo `center_admin`/`super_admin` → bị từ chối.
- [ ] `teacher`, `student`, `parent` gọi API tạo tài khoản (teacher/student/parent) → bị từ chối; `center_admin` tạo student/parent trong trung tâm mình → thành công, sang trung tâm khác → bị từ chối.
- [ ] `center_admin` trung tâm A đọc/sửa/xóa user, lớp, khóa học, gói học phí, puzzle của trung tâm B → 404.
- [ ] Tạo gói học phí với `course_id` thuộc trung tâm khác → bị từ chối.
- [ ] Phân công giáo viên trung tâm khác vào lớp → bị từ chối.
- [ ] Điều chuyển học viên giữa các lớp: lịch sử ghi đúng, sĩ số cập nhật, không điều chuyển sang lớp trung tâm khác.
- [ ] `parent` chỉ thấy dữ liệu của học viên đã liên kết; tạo liên kết với học viên trung tâm khác → bị từ chối.
- [ ] `teacher` sửa/xóa puzzle của giáo viên khác (cùng trung tâm hay khác) → bị từ chối; sửa/xóa puzzle của mình → thành công.
- [ ] `center_admin` tạo/sửa/xóa/ẩn puzzle của teacher trong trung tâm mình → thành công và có audit log; puzzle trung tâm khác → 404.
- [ ] Puzzle trong Puzzle Bank hiển thị cho mọi teacher của cùng trung tâm; không hiển thị ở trung tâm khác.
- [ ] Puzzle bị ẩn không xuất hiện khi chọn giao bài mới; bài đã giao vẫn xem được.
- [ ] `teacher`, `student`, `parent` gọi mọi endpoint AI Scanner (upload, quét, xóa, sửa kết quả) → 403; `center_admin` chỉ thao tác job của trung tâm mình; `super_admin` thao tác tất cả.
- [ ] Sửa `center_id` trong body request không có hiệu lực (server lấy từ người dùng đăng nhập).

**Cài đặt & không hard-code**
- [ ] Tìm trong mã nguồn không còn mảng/enum literal cho các danh mục ở mục 6 (kiểm tra bằng grep, báo cáo kết quả).
- [ ] `center_admin` thêm một cấp độ khóa học mới → xuất hiện trong dropdown tạo khóa học của trung tâm đó, không xuất hiện ở trung tâm khác.
- [ ] Mỗi role chỉ thấy đúng các tab ở mục 7; gọi API tab không thuộc quyền → 403.
- [ ] Đổi hệ số K hoặc ngưỡng Stockfish trong Cài đặt → lần chấm sau dùng giá trị mới; với giá trị mặc định, kết quả chấm không đổi so với trước khi refactor.

**Dữ liệu & vận hành**
- [ ] Migration chạy được trên bản sao DB hiện có; backfill không mất dữ liệu; có rollback.
- [ ] Tài khoản test cũ được xử lý theo mục 1.
- [ ] Audit log ghi đầy đủ các hành động quản trị.

---

## 9. Thứ tự triển khai đề xuất (mỗi bước một commit)

1. **Nền tảng phân quyền:** `Role`, `permissions.py`, tenant scope, ràng buộc `center_id`, migration + backfill, test cách ly dữ liệu.
2. **Trung tâm & Admin trung tâm:** API + giao diện cho super_admin; hiển thị tên trung tâm ở header.
3. **Quản lý người dùng theo trung tâm:** teacher/student/parent (chỉ center_admin/super_admin tạo), liên kết parent–student.
4. **Khóa học, lớp, ghi danh, điều chuyển lớp** (giữ lịch sử).
5. **Gói học phí** theo khóa học của trung tâm (chỉ lưu gói).
6. **Puzzle Bank:** `owner_id`, quyền sửa/xóa (teacher: của mình; center_admin: cả trung tâm; super_admin: tất cả), ẩn/khóa, soft-delete, xem theo toàn trung tâm.
7. **AI Scanner:** khóa quyền upload, cô lập theo trung tâm, lưu file an toàn.
8. **Danh mục & Settings:** bảng `catalog_items`/`settings`, đưa tham số Rating và Stockfish ra cấu hình, loại bỏ hard-code, menu Cài đặt dạng tab theo role.
9. **Kiểm thử tổng thể, rà soát grep hard-code, báo cáo.**

Sau mỗi bước, Agent báo cáo: file đã sửa, migration đã thêm, test đã chạy (pass/fail), điểm mâu thuẫn với code hiện có, và các giả định cần chủ dự án xác nhận.

---

## 10. Quyết định đã chốt và phạm vi

**Đã chốt bởi chủ dự án (Agent không đổi):**
1. `center_admin` được tạo/sửa/xóa và ẩn/khóa puzzle trong Puzzle Bank của trung tâm mình, kể cả puzzle của teacher.
2. Puzzle Bank hiển thị cho cả trung tâm (`puzzle_visibility = center`); teacher chỉ sửa/xóa puzzle của chính mình.
3. Học phí chỉ lưu **gói học phí**; không quản lý thu tiền, công nợ.
4. Học viên và phụ huynh chỉ do `center_admin` hoặc `super_admin` tạo.
5. Stockfish đã được tích hợp để đánh giá nước đi; Agent không làm lại, chỉ đưa tham số ra cấu hình nếu đang hard-code.

**Ngoài phạm vi tài liệu này:** chuyển giáo viên hoặc học viên giữa các trung tâm, giáo viên dạy nhiều trung tâm.
