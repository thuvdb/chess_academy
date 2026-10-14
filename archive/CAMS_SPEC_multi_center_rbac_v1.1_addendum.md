# CAMS – Phụ lục điều chỉnh cho `CAMS_SPEC_multi_center_rbac_v1.1.md`

> Nạp **cùng** với spec v1.1. Khi phụ lục này khác spec v1.1, **phụ lục này thắng**.
> Căn cứ: báo cáo hiện trạng của Agent ngày 13/10/2026 và các tính năng đã làm sau khi viết spec v1.1 (quy trình bài tập: bài nộp, chấm, trả bài).

---

## 0. Quy tắc bổ sung cho Agent

1. **Không dò, đoán, bẻ khóa mật khẩu.** Không in hash, mật khẩu, giá trị `.env` ra log, báo cáo hay commit. Cần đặt lại mật khẩu tài khoản mẫu thì dùng script đặt mật khẩu mới (nhập lúc chạy hoặc tự sinh, in một lần).
2. Sao lưu `pg_dump` trước khi chạy migration; chạy dry-run trước, real-run sau; có rollback.
3. Không thay đổi quy trình chấm bài tập về nhà; chỉ thêm kiểm tra phân quyền và lọc theo trung tâm lên các bảng đã có.

---

## 1. Hiện trạng đã xác nhận (liên quan đến phân quyền)

- Vai trò hiện có trong DB: `super_admin`, `admin`, `teacher`, `student`; enum có sẵn `PARENT` nhưng **chưa có** bảng liên kết phụ huynh–học viên, endpoint hay giao diện cho phụ huynh.
- Có model `Center` (có `code`). Chưa xác nhận có API quản lý trung tâm.
- Tài khoản hiện có: một `super_admin` (center NULL), một `admin` (test), một `teacher` và một `student` mẫu (center NULL), và một tài khoản học viên thật (center NULL). Các tài khoản mẫu có mật khẩu yếu hoặc dùng chung hash.
- `POST /api/auth/register` nhận `role` và `center_id` từ client, **không kiểm tra quyền**. Đăng nhập Google/Facebook tự tạo user mới `role=student`, `center_id=NULL`.
- Không có API/giao diện để admin tạo giáo viên, học viên, phụ huynh. Trang Members chỉ đọc; Enroll chỉ gán người đã có tài khoản vào lớp.
- **Không có** `backend/app/seed.py` (spec v1.1 mục 0 nhắc nhầm file này).
- Các bảng của quy trình bài tập (bài nộp, kết quả từng thế cờ, sự kiện) đã có cột `center_id` lấy từ lớp của bài giao.

---

## 2. Điều chỉnh so với spec v1.1

### 2.1 Mục 0 của spec v1.1
Bỏ `backend/app/seed.py` khỏi danh sách file cần đọc.

### 2.2 Đổi tên vai trò `admin` → `center_admin`
- Migration đổi giá trị vai trò trong DB, **và** đổi mọi chỗ dùng chuỗi/enum `admin` trong backend (dependency, endpoint, service), frontend (kiểm tra vai trò, menu, route guard), test và script.
- Agent liệt kê trước các vị trí tìm thấy (grep) rồi mới sửa; báo lại nếu có chỗ mơ hồ giữa `admin` (vai trò) và `admin` (nghĩa khác).
- Không đổi nghĩa vai trò `super_admin`.

### 2.3 Vá `/register` và chính sách tự đăng ký (làm ở bước 1, trước mọi việc khác)
Chính sách tự đăng ký hiện tại **mâu thuẫn** với ràng buộc của spec v1.1 (mọi vai trò khác `super_admin` bắt buộc có `center_id`; học viên và phụ huynh **chỉ** `center_admin`/`super_admin` được tạo). Điều chỉnh:
1. `POST /api/auth/register`: Backend **bỏ qua `role` và `center_id` do client gửi**. Cấu hình `ALLOW_PUBLIC_REGISTER` (biến môi trường qua `settings`, mặc định `false`).
   - Khi `false`: trả 403, giao diện ẩn trang/liên kết "Đăng ký" (thông qua endpoint công khai chỉ đọc `GET /api/auth/config`).
   - Khi `true`: chỉ tạo được `student` không có trung tâm, **không** thuộc cấu hình khuyến nghị cho môi trường có nhiều trung tâm; ghi rõ trong tài liệu.
2. Đăng nhập Google/Facebook: **chỉ cho người dùng đã tồn tại** (khớp email với tài khoản do admin tạo). Không tự tạo user mới.
3. Trang đăng ký ở frontend không có lựa chọn vai trò và không còn xuất hiện khi cờ tắt.
4. Test: gọi trực tiếp API với `role=super_admin`/`admin`, với `center_id` bất kỳ → không tạo được vai trò đó; cờ tắt → 403; social login email lạ → không tạo user.

### 2.4 Tạo người dùng (bước 3 của spec v1.1)
- Thực hiện đúng spec v1.1 mục 4.2: API và giao diện "Thêm thành viên" cho `center_admin` (trong trung tâm mình) và `super_admin` (chọn trung tâm). Nút thêm đặt ở trang Members hiện có.
- Mật khẩu khi tạo: admin nhập hoặc hệ thống tự sinh; người dùng bị buộc đổi mật khẩu ở lần đăng nhập đầu (`must_change_password`).
- **Phụ huynh:** tạo bảng `parent_student_links` (spec v1.1 mục 2), endpoint tạo/gỡ liên kết và màn hình xem của phụ huynh theo spec (chỉ xem tiến độ/gói học phí của con đã liên kết). Nếu phần giao diện phụ huynh quá lớn, Agent báo lại và đề xuất chia nhỏ; phần Backend và quyền phải đủ trước.
- Giữ script `create_user.py` (nếu đã có từ Phase 0) cho việc tạo `super_admin` đầu tiên; script phải tuân thủ ràng buộc mới (mọi vai trò khác `super_admin` bắt buộc có trung tâm).

### 2.5 Backfill dữ liệu hiện có (migration + script, dry-run trước)
1. Tạo một **trung tâm mặc định** (tên do chủ dự án chỉ định; xem mục 4) nếu chưa có.
2. Người dùng có `center_id` rỗng:
   - `super_admin` giữ nguyên, `center_id=NULL`.
   - Vai trò khác: gán vào trung tâm mặc định (hoặc trung tâm chủ dự án chỉ định cho từng tài khoản).
3. Dữ liệu theo trung tâm:
   - Lớp học, khóa học, gói học phí, bài giao: gán `center_id` theo lớp hoặc người tạo; báo cáo bản ghi không suy ra được.
   - Puzzle: `center_id` và `owner_id` theo giáo viên tạo; nếu không xác định được người tạo thì `owner_id` là `center_admin` của trung tâm mặc định.
   - Bảng của quy trình bài tập (bài nộp, kết quả từng thế cờ, sự kiện): kiểm tra `center_id` đã đầy đủ; bổ sung nếu thiếu.
   - Job và sách của AI Scanner: `center_id` theo người tải lên.
4. Sau backfill, bật ràng buộc: `center_id NOT NULL` cho mọi bảng nghiệp vụ trừ trường hợp spec cho phép NULL (`super_admin`, job quét do `super_admin` tạo).
5. Đặt lại mật khẩu các tài khoản mẫu yếu; tài khoản học viên thật **không** đổi mật khẩu, không in dữ liệu cá nhân ra báo cáo.
6. Báo cáo: số bản ghi theo từng bảng đã gán trung tâm, số bản ghi không gán được (kèm lý do, không kèm dữ liệu cá nhân).

### 2.6 Liên hệ với quy trình bài tập
- Các endpoint của quy trình bài tập (tổng quan, chi tiết bài nộp, chấm, trả bài, mở lại) phải **thêm** kiểm tra: người gọi thuộc đúng trung tâm của bài giao (`center_id` của bài nộp); giáo viên chỉ thao tác lớp mình dạy; học viên chỉ xem bài nộp của mình; khác trung tâm → 404.
- Không đổi quy tắc trạng thái (409 khi sai trạng thái) và quy tắc công bố kết quả.

### 2.7 Dữ liệu kiểm thử cách ly
Tạo script (không dùng dữ liệu thật) sinh **hai trung tâm mẫu A và B**, mỗi trung tâm có: một `center_admin`, hai giáo viên, vài học viên, một khóa học, một lớp, một bài giao, vài puzzle và một gói học phí; mật khẩu tự sinh, in một lần. Dùng cho bộ test cách ly ở spec v1.1 mục 8 và cho đồng nghiệp test.

---

## 3. Thứ tự triển khai điều chỉnh

0. **Vá `/register`** và chính sách tự đăng ký (mục 2.3); kiểm tra khởi động với `JWT_SECRET_KEY` (xem tài liệu chuẩn bị triển khai).
1. Nền tảng phân quyền: `Role` (kèm đổi `admin` → `center_admin`), `permissions.py`, tenant scope, ràng buộc `center_id`, migration và backfill (mục 2.5), test cách ly.
2. Trung tâm và admin trung tâm (super_admin), tên trung tâm ở header.
3. Quản lý người dùng theo trung tâm (mục 2.4), liên kết phụ huynh.
4. Khóa học, lớp, ghi danh, điều chuyển lớp.
5. Gói học phí.
6. Puzzle Bank (quyền theo spec v1.1 mục 5.1).
7. AI Scanner.
8. Danh mục và Cài đặt dạng tab.
9. Cách ly quy trình bài tập (mục 2.6) và kiểm thử tổng thể.
10. Dữ liệu kiểm thử hai trung tâm (mục 2.7), báo cáo.

Mỗi bước một commit `CAMS-xxxx`.

---

## 4. Cần chủ dự án quyết định trước bước 1

1. Tên trung tâm mặc định để gán tài khoản và dữ liệu hiện có.
2. Tài khoản học viên thật hiện có thuộc trung tâm nào.
3. Xác nhận **tắt tự đăng ký và đăng nhập mạng xã hội tạo user mới** (mục 2.3). Đề xuất: tắt; mọi tài khoản do admin tạo.
4. Giao diện phụ huynh: làm đầy đủ ở phiên bản này hay chỉ làm Backend và quyền trước.
