# KỊCH BẢN KIỂM THỬ CHẤP NHẬN NGƯỜI DÙNG (UAT CHECKLIST)
## Hệ Thống Quản Lý Học Viện Cờ Vua CAMS (Chess Academy Management System)

> **Mã tài liệu:** `CAMS-UAT-DOC-01`  
> **Phiên bản:** `1.5` *(Chiến lược phân đợt Phased UAT — Đồng bộ 100% PROJECT_CONTEXT.md)*  
> **Ngày cập nhật:** 15/10/2026  
> **Trạng thái:** Sẵn sàng kiểm thử Đợt 1 (Core MVP v1.0) & Chuẩn bị Đợt 2 (v1.5)  
> **Mục tiêu:** Cung cấp kịch bản kiểm thử UAT chuẩn hóa cho người dùng nghiệp vụ (Super Admin, Quản trị trung tâm, Giáo viên, Học sinh, Phụ huynh) và Đội ngũ QA xác minh độ sẵn sàng phát hành theo từng đợt bàn giao.  
> **Tài liệu căn cứ:** `PROJECT_CONTEXT.md`, `01_requirements.md`, `02_system_design.md`, `AI_SCANNER_ARCHITECTURE.md`, `PAYMENT_ARCHITECTURE.md`, `TOURNAMENT_ARCHITECTURE.md`.

---

## 1. THÔNG TIN CHUNG & HƯỚNG DẪN CHUẨN BỊ MÔI TRƯỜNG TEST

### 1.1 Thông tin đường dẫn & Môi trường kiểm thử

| Thành phần | Đường dẫn (URL) / Cổng kết nối | Ghi chú kiểm tra kết nối |
| :--- | :--- | :--- |
| **Cổng Web ứng dụng (Frontend)** | `http://localhost:3000` | Giao diện Web Admin & Cổng học viên/giáo viên (React 19 + Vite 8) |
| **Cổng Dịch vụ API (Backend)** | `http://localhost:8000` | Nền tảng FastAPI REST API (Python 0.115.x + Uvicorn) |
| **Trang Tài liệu API (Swagger UI)** | `http://localhost:8000/docs` | Kiểm tra trực quan 15 APIRouter modules |
| **Điểm kiểm tra sức khỏe hệ thống** | `http://localhost:8000/health` | Kết quả mong đợi: `{"status":"ok"}` |
| **Điểm cấu hình xác thực (Public Auth)** | `http://localhost:8000/api/auth/config` | Trả về cờ đăng ký công khai, OAuth capabilities |
| **Cổng WebSocket đấu cờ trực tiếp** | `ws://localhost:8000/ws/game/{game_id}` | Kết nối realtime (kèm tham số truy vấn `?token=<JWT>`) |
| **Cơ sở dữ liệu & Bộ nhớ đệm** | Nội bộ mạng Docker (`cams_db`, `redis`) | **KHÔNG** mở cổng ra ngoài Internet (Bảo mật máy chủ) |

> **Hướng dẫn kiểm tra trước khi chạy UAT:**
> 1. Mở terminal kiểm tra trạng thái 6 container Docker: `docker-compose ps` (Tất cả `db`, `redis`, `backend`, `worker`, `beat`, `frontend` đều ở trạng thái `Up`).
> 2. Truy cập `http://localhost:8000/health` trên trình duyệt để xác nhận backend kết nối cơ sở dữ liệu thành công.
> 3. Kiểm tra bảo mật môi trường: Trong chế độ chạy Production (`DEBUG=false`), hệ thống từ chối khởi động nếu `JWT_SECRET_KEY < 32 ký tự`, `CORS_ORIGINS` chứa `*`, hoặc mật khẩu DB mặc định.

---

### 1.2 Danh sách tài khoản thử nghiệm theo từng Vai trò (6 Roles Chuẩn)

| Vai trò (Role) | Tài khoản (Email / Username) | Mật khẩu mặc định | Tên hiển thị | Phạm vi quyền hạn thực tế |
| :--- | :--- | :--- | :--- | :--- |
| **Quản trị cấp cao (Super Admin)** | `superadmin@cams.test` | `Super@2026!` | Vũ Tổng Quản | Quyền tối cao toàn hệ thống, truy cập và điều phối tất cả các Trung tâm cờ vua (Multi-center tenant root). |
| **Quản trị trung tâm (Center Admin)** | `admin@cams.test` | `Admin@2026!` | Nguyễn Quản Trị | Toàn quyền trong phạm vi Trung tâm: quản lý thành viên, lớp học, gói học phí, hóa đơn, cài đặt trung tâm. |
| **Giáo viên 1 (Teacher)** | `teacher1@cams.test` | `Teacher@2026!` | Trần Văn Giáo | Quản lý lớp cơ bản, tải quét sách cờ PDF qua AI Scanner, sửa FEN, giao bài tập, tạo giải đấu. |
| **Giáo viên 2 (Teacher)** | `teacher2@cams.test` | `Teacher@2026!` | Lê Thị Hoa | Quản lý lớp nâng cao, chấm điểm bài tập học sinh (thủ công & nhận xét), mở lại bài tập nộp lại. |
| **Học sinh 1 (Student)** | `student1@cams.test` | `Student@2026!` | Phạm Minh Học | Lớp cơ bản: luyện tập puzzle, làm và nộp bài tập, thi đấu giải trực tuyến, ELO khởi tạo 800. |
| **Học sinh 2 (Student)** | `student2@cams.test` | `Student@2026!` | Hoàng Bảo Long | Lớp cơ bản: đối thủ thi đấu đối kháng với Học sinh 1 trong giải đấu online, ELO khởi tạo 800. |
| **Học sinh 3 (Student)** | `student3@cams.test` | `Student@2026!` | Võ Thị Mai | Học viên thử nghiệm nộp bài tập quá hạn (Celery Beat tự động thu bài) và thanh toán học phí. |
| **Phụ huynh (Parent)** | `parent1@cams.test` | `Parent@2026!` | Phạm Văn Cha | Liên kết với Học sinh 1 qua `parent_student`: theo dõi tiến độ, nhận thông báo hóa đơn, quét mã VietQR. |

---

### 1.3 Dữ liệu mẫu cần chuẩn bị trước khi thực hiện UAT

1. **Dữ liệu Lớp học mẫu:**
   - Lớp 1: `Cờ Vua Cơ Bản K2026` (Cấp độ: `beginner`, Giáo viên phụ trách: `Trần Văn Giáo`, Sĩ số tối đa: 20 học viên, Thời khóa biểu: Thứ 3 & Thứ 5, 18:00 - 19:30).
   - Lớp 2: `Chiến Thuật Trung Cấp` (Cấp độ: `intermediate`, Giáo viên phụ trách: `Lê Thị Hoa`, Sĩ số tối đa: 15 học viên, Thời khóa biểu: Thứ 7, 08:30 - 11:00).
2. **File tài liệu PDF thử nghiệm AI Scanner:**
   - File `test_valid_tactics.pdf`: File PDF chuẩn (< 50MB) chứa 2–3 trang có các thế cờ rõ nét (in từ sách cờ vua, chuẩn 300 DPI).
   - File `test_fake_pdf.pdf`: File văn bản text thuần túy đổi đuôi thành `.pdf` (dùng để kiểm tra bộ lọc Magic Bytes `%PDF-`).
   - File `test_oversize.pdf`: File dung lượng > 50MB (kiểm tra bộ lọc giới hạn dung lượng tải lên).
   - File `test_invalid_format.docx` hoặc ảnh `.png` (kiểm tra bộ lọc MIME type `application/pdf`).
3. **Thế cờ mẫu chuẩn FEN & Stockfish Solution Tree:**
   - Thế cờ Chiếu hết 1 nước (Trắng đi): `r1bqkb1r/pppp1ppp/2n2n2/4p3/2B1P3/5N2/PPPP1PPP/RNBQK2R w KQkq - 0 1` -> Nước giải tối ưu: `Bxf7#` (hoặc `c4f7`).
   - Thế cờ Tàn cuộc (Đen đi): `8/4k3/4p3/4P3/3PK3/8/8/8 b - - 0 1`
4. **Cấu hình Ngân hàng nhận thanh toán (VietQR Level 1):**
   - Ngân hàng: `MB` (`VIETQR_BANK_ID`)
   - Số tài khoản: `1234567890` (`VIETQR_ACCOUNT_NO`)
   - Tên chủ tài khoản: `CAMS CHESS ACADEMY` (`VIETQR_ACCOUNT_NAME`)
   - Cú pháp nội dung chuyển khoản tự động: `INV-{id}`

---

## 2. BẢNG KỊCH BẢN UAT CHỨC NĂNG THEO CHIẾN LƯỢC PHÂN ĐỢT (PHASED UAT)

> ### 🟢 ĐỢT 1: UAT PHASE 1 — CORE MVP v1.0 (KIỂM THỬ NGAY)
> *Phạm vi bàn giao:* Hoàn thành toàn bộ chức năng cốt lõi học viện: Quản lý đăng nhập/phân quyền, Quản trị thành viên, Lớp học, Lịch học, AI Scanner quét sách PDF bóc tách thế cờ, Kho bài toán puzzle, Giao bài tập về nhà, Luyện tập tương tác và Bảng xếp hạng ELO.

---

### Module 2.1: Xác thực & Phân quyền (Authentication & Authorization)
*Đường dẫn UI:* `/login`, `/register`, `/profile` | *API:* `/api/auth`, `/api/users/me`

| Mã TC | Tên tính năng | Vai trò thực hiện | Các bước thao tác (Dành cho người dùng nghiệp vụ) | Kết quả mong đợi | Trạng thái |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **TC-AUTH-01** | Đăng nhập tài khoản hợp lệ | Admin / Teacher / Student | 1. Mở trình duyệt truy cập `http://localhost:3000/login`<br>2. Nhập Email: `admin@cams.test`<br>3. Nhập Mật khẩu: `Admin@2026!`<br>4. Nhấp nút **Đăng nhập**. | - Đăng nhập thành công, chuyển hướng vào Dashboard tương ứng vai trò.<br>- Góc phải thanh tiêu đề hiển thị đúng tên "Nguyễn Quản Trị" và vai trò `center_admin`.<br>- Trả về JWT Access Token (TTL 30 phút) và Refresh Token (TTL 7 ngày). | `[ ] Pass`<br>`[ ] Fail` |
| **TC-AUTH-02** | Xử lý khi nhập sai mật khẩu | Bất kỳ | 1. Truy cập trang đăng nhập.<br>2. Nhập Email: `admin@cams.test`<br>3. Nhập Mật khẩu: `SaiMatKhau@123`<br>4. Nhấp **Đăng nhập**. | - Không cho phép đăng nhập (HTTP 401).<br>- Hiển thị thông báo màu đỏ: *"Email hoặc mật khẩu không chính xác"*. | `[ ] Pass`<br>`[ ] Fail` |
| **TC-AUTH-03** | Khóa trường khi để trống thông tin | Bất kỳ | 1. Để trống cả Email và Mật khẩu.<br>2. Nhấp nút **Đăng nhập**. | - Form hiển thị cảnh báo yêu cầu nhập đầy đủ email và mật khẩu.<br>- Không gửi request lỗi lên server. | `[ ] Pass`<br>`[ ] Fail` |
| **TC-AUTH-04** | Đăng xuất khỏi hệ thống | Teacher | 1. Tại tài khoản đang đăng nhập, nhấp vào Avatar góc trên cùng bên phải.<br>2. Chọn **Đăng xuất**.<br>3. Thử bấm nút Back của trình duyệt. | - Hệ thống xóa phiên đăng nhập, điều hướng về `/login`.<br>- Bấm Back không truy cập lại được trang quản trị mà bị giữ lại ở trang đăng nhập. | `[ ] Pass`<br>`[ ] Fail` |
| **TC-AUTH-05** | Cập nhật thông tin cá nhân & Avatar | Student | 1. Đăng nhập bằng `student1@cams.test`.<br>2. Vào trang **Hồ sơ cá nhân** (`/profile`).<br>3. Thay đổi số điện thoại thành `0987654321` và thêm Tiểu sử: *"Học viên đội tuyển cờ"*. Tải lên ảnh avatar mới (`POST /api/users/me/avatar`). Nhấp **Lưu**.<br>4. Tải lại trang (F5). | - Thông báo cập nhật hồ sơ thành công.<br>- Dữ liệu số điện thoại, tiểu sử và ảnh đại diện mới (`/static/avatars/`) vẫn hiển thị chính xác sau khi tải lại trang. | `[ ] Pass`<br>`[ ] Fail` |
| **TC-AUTH-06** | Phân quyền hiển thị Menu theo vai trò | Student | 1. Đăng nhập bằng tài khoản `student1@cams.test`.<br>2. Quan sát thanh điều hướng (Sidebar) bên trái. | - Học sinh chỉ thấy: *Trang chủ, Luyện tập, Bài tập của tôi, Giải đấu, Bảng xếp hạng, Lịch học*.<br>- **Tuyệt đối không thấy**: menu *AI Scanner, Cấu hình học phí, Quản lý thành viên, Cài đặt*. | `[ ] Pass`<br>`[ ] Fail` |

---

### Module 2.2: Quản lý Trung tâm, Lớp học & Thành viên (Class & Member Management)
*Đường dẫn UI:* `/classes`, `/classes/:classId`, `/schedule`, `/members` | *API:* `/api/classes`, `/api/users`

| Mã TC | Tên tính năng | Vai trò thực hiện | Các bước thao tác | Kết quả mong đợi | Trạng thái |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **TC-CLASS-01** | Tạo mới lớp học | Center Admin | 1. Đăng nhập Admin, vào menu **Lớp học** (`/classes`).<br>2. Nhấp nút **+ Tạo lớp học mới**.<br>3. Nhập: Tên lớp: `Cờ Vua Thiếu Nhi 2026`, Cấp độ: `beginner`, Giáo viên phụ trách: chọn `Trần Văn Giáo`, Sĩ số: `15`.<br>4. Nhấp **Lưu lại**. | - Thông báo tạo lớp thành công (`POST /api/classes`).<br>- Lớp mới xuất hiện trên bảng danh sách lớp với sĩ số ban đầu là `0/15`, trạng thái `Đang hoạt động`. | `[ ] Pass`<br>`[ ] Fail` |
| **TC-CLASS-02** | Thêm học sinh vào lớp học | Teacher | 1. Đăng nhập `teacher1@cams.test`.<br>2. Vào lớp `Cờ Vua Thiếu Nhi 2026`.<br>3. Nhấp tab **Danh sách học sinh** -> chọn **+ Thêm học sinh**.<br>4. Tìm kiếm `Phạm Minh Học` (`student1@cams.test`) và nhấn **Xác nhận thêm**. | - Học sinh Phạm Minh Học được ghi nhận vào danh sách (`POST /api/classes/{id}/enroll`).<br>- Sĩ số lớp tự động tăng lên thành `1/15`. | `[ ] Pass`<br>`[ ] Fail` |
| **TC-CLASS-03** | Ngăn chặn thêm quá sĩ số lớp | Teacher | 1. Cố ý thêm học sinh vượt quá số lượng `max_students` đã cài đặt cho lớp học. | - Hệ thống hiển thị cảnh báo lỗi: *"Lớp học đã đạt sĩ số tối đa, không thể ghi danh thêm"*. | `[ ] Pass`<br>`[ ] Fail` |
| **TC-CLASS-04** | Xóa/Hủy ghi danh học sinh | Teacher | 1. Tại bảng danh sách học sinh của lớp, tìm học sinh cần xóa.<br>2. Nhấp biểu tượng **Thùng rác / Xóa khỏi lớp**.<br>3. Xác nhận hộp thoại cảnh báo: *"Bạn có chắc chắn muốn rút học sinh này khỏi lớp?"*. | - Học sinh biến mất khỏi danh sách lớp (`DELETE /api/classes/{id}/enrollments/{student_id}`).<br>- Sĩ số cập nhật giảm tương ứng.<br>- Tài khoản của học sinh trong hệ thống vẫn còn nguyên vẹn (chỉ xóa quan hệ ghi danh). | `[ ] Pass`<br>`[ ] Fail` |
| **TC-CLASS-05** | Học sinh xem thông tin lớp của mình | Student | 1. Đăng nhập bằng `student1@cams.test`.<br>2. Vào mục **Lớp học của tôi**. | - Hiển thị đúng thông tin lớp `Cờ Vua Thiếu Nhi 2026`, tên giáo viên phụ trách.<br>- Không xem được danh sách hay can thiệp vào các lớp học khác của trung tâm. | `[ ] Pass`<br>`[ ] Fail` |
| **TC-CLASS-06** | Xem thời khóa biểu tại trang /schedule | Teacher / Student | 1. Giáo viên hoặc học sinh đăng nhập vào hệ thống.<br>2. Truy cập trang **Lịch học** (`/schedule`).<br>3. Chuyển đổi giữa chế độ xem Tuần (Week view) và Tháng (Month view).<br>4. Nhấp vào một buổi học cụ thể trên lịch. | - Hiển thị đầy đủ các buổi học định kỳ được tạo từ `schedule_json` của các lớp mà người dùng đang phụ trách hoặc ghi danh.<br>- Khung chi tiết hiển thị đúng: Tên lớp, Giáo viên phụ trách, Phòng học/Chi nhánh, và khung giờ học chính xác. | `[ ] Pass`<br>`[ ] Fail` |
| **TC-USER-01** | Admin tạo user và liên kết Phụ huynh – Học sinh tại trang /members | Center Admin | 1. Đăng nhập Admin, vào menu **Quản lý thành viên** (`/members`).<br>2. Bấm **+ Thêm thành viên**, nhập thông tin tạo học sinh `student4@cams.test` và phụ huynh `parent4@cams.test` thuộc trung tâm.<br>3. Tại dòng hồ sơ của học sinh mới, chọn thao tác **Liên kết Phụ huynh**.<br>4. Chọn tài khoản phụ huynh vừa tạo và nhấn **Xác nhận liên kết** (`POST /api/users/{student_id}/link-parent`). | - Tạo thành công tài khoản gán đúng `center_id` của trung tâm.<br>- Quan hệ liên kết được ghi nhận vào bảng `parent_student`.<br>- Phụ huynh đăng nhập sẽ thấy học sinh được liên kết trong hồ sơ quản lý con của mình. | `[ ] Pass`<br>`[ ] Fail` |

---

### Module 2.3: AI Quét Bài Toán Cờ Từ PDF (AI Scanner)
*Đường dẫn UI:* `/scanner` | *API:* `/api/scan` | *Task Queue:* Celery Worker (`process_scan_job`)

| Mã TC | Tên tính năng | Vai trò thực hiện | Các bước thao tác | Kết quả mong đợi | Trạng thái |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **TC-SCAN-01** | Tải lên file PDF bài tập hợp lệ | Teacher | 1. Đăng nhập Giáo viên, vào menu **AI Scanner** (`/scanner`).<br>2. Bấm vùng upload hoặc kéo thả file `test_valid_tactics.pdf`.<br>3. Bấm nút **Bắt đầu quét & bóc tách bài toán**. | - File được tải lên thành công (`POST /api/scan/upload`).<br>- Hệ thống tạo một mã tác vụ quét (Scan Job) và Celery worker tiếp nhận xử lý nền bất đồng bộ (`process_scan_job`), hiển thị tiến trình quét: *"Đang xử lý trang 1/2..."*. | `[ ] Pass`<br>`[ ] Fail` |
| **TC-SCAN-02** | Chặn file sai định dạng hoặc quá dung lượng | Teacher | 1. Thử tải lên file ảnh `hinh_anh.png` hoặc file tài liệu `bai_tap.docx`.<br>2. Thử đổi đuôi file text thành `test.pdf` (kiểm tra Magic Bytes `%PDF-`).<br>3. Thử tải lên file PDF có dung lượng > 50MB. | - Hệ thống phát hiện và báo lỗi ngay tại trình duyệt: *"Định dạng không được hỗ trợ. Chỉ chấp nhận file định dạng .PDF hợp lệ"* hoặc *"Dung lượng file vượt quá giới hạn 50MB"*. | `[ ] Pass`<br>`[ ] Fail` |
| **TC-SCAN-03** | Hiển thị kết quả bóc tách & Cảnh báo độ tin cậy | Teacher | 1. Khi tiến trình quét hoàn thành, xem kết quả từng trang.<br>2. Nhấp vào bàn cờ số 1 được bóc tách.<br>3. Quan sát các bàn cờ có độ tin cậy rất cao. | - Hiển thị ảnh chụp thực tế trích xuất từ PDF song song với bàn cờ đồ họa số hóa.<br>- Hiển thị điểm tin cậy tổng quát (`confidence_board`).<br>- **Đối với bàn cờ có độ tin cậy rất cao (tất cả ô >= 95%, không xung đột luật cờ):** hệ thống tự động gán trạng thái **`auto_approved`**.<br>- **Các ô có độ tin cậy thấp (< 70%):** được viền màu vàng/cam kèm icon cảnh báo `⚠️` để giáo viên chú ý. | `[ ] Pass`<br>`[ ] Fail` |
| **TC-SCAN-04** | Giáo viên chỉnh sửa FEN (Human-in-the-loop) | Teacher | 1. Quan sát thấy một ô bị AI nhận diện sai (ví dụ: quân Mã đen thành Tốt đen).<br>2. Nhấp trực tiếp vào ô cờ sai trên bàn cờ hoặc thanh chỉnh sửa.<br>3. Chọn lại đúng quân `Mã Đen (n)`.<br>4. Chọn quyền đi tiếp theo: `Trắng đi (w)`.<br>5. Bấm **Lưu FEN đã sửa** (`PUT /api/scan/results/{id}/review`). | - Bàn cờ đồ họa cập nhật tức thì theo quân cờ mới chọn.<br>- Chuỗi FEN hiển thị tự động cập nhật khớp với thế cờ.<br>- Trạng thái kết quả chuyển thành `Đã chỉnh sửa (corrected)`. | `[ ] Pass`<br>`[ ] Fail` |
| **TC-SCAN-05** | Phê duyệt kết quả và tự động tạo Puzzle | Teacher | 1. Sau khi kiểm tra thế cờ đã chuẩn xác, đặt tên bài: *"Thế cờ Tactic Trang 1"*, độ khó: `Dễ`, chủ đề: `Chiếu hết`.*<br>2. Bấm nút **Phê duyệt & Chuyển vào Kho Bài Toán** (`POST /api/scan/results/{id}/approve`). | - Hệ thống ghi nhận trạng thái bàn cờ là `approved`.<br>- Tự động kích hoạt Stockfish kiểm tra nước đi tối ưu (`mate_solver.py`).<br>- Bài toán mới xuất hiện ngay trong **Kho Bài Toán** để sẵn sàng giao bài. | `[ ] Pass`<br>`[ ] Fail` |
| **TC-SCAN-06** | Từ chối bàn cờ bị lỗi/mờ | Teacher | 1. Với những vùng nhận diện nhầm hình minh họa thành bàn cờ hoặc ảnh quá mờ.<br>2. Bấm nút **Từ chối (Reject)**. | - Bàn cờ được đánh dấu `rejected`.<br>- Không sinh bài toán rác vào cơ sở dữ liệu kho bài. | `[ ] Pass`<br>`[ ] Fail` |
| **TC-SCAN-07** | Chặn quyền truy cập của học sinh & Bảo vệ file | Student | 1. Đăng nhập học sinh `student1@cams.test`.<br>2. Cố tình gõ đường dẫn `http://localhost:3000/scanner` trên thanh URL.<br>3. Mở trực tiếp link file ảnh quét không có chữ ký HMAC. | - Giao diện chặn truy cập, chuyển hướng về trang chủ học sinh kèm thông báo: *"Bạn không có quyền truy cập trang này"*.<br>- Đường dẫn file trích xuất yêu cầu chữ ký HMAC có thời hạn qua `/api/files/{path}` (HTTP 403 Forbidden nếu thiếu). | `[ ] Pass`<br>`[ ] Fail` |

---

### Module 2.4: Kho Bài Toán, Giao Bài & Luyện Tập (Puzzles, Practice & Assignments)
*Đường dẫn UI:* `/puzzles`, `/practice`, `/assignments`, `/assignments/:id`, `/leaderboard` | *API:* `/api/puzzles`, `/api/assignments`, `/api/progress`, `/api/leaderboard`

| Mã TC | Tên tính năng | Vai trò thực hiện | Các bước thao tác | Kết quả mong đợi | Trạng thái |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **TC-PUZ-01** | Tạo bài toán thủ công từ FEN & xác thực Stockfish | Teacher | 1. Vào **Kho Bài Toán** (`/puzzles`) -> chọn **+ Tạo mới**.<br>2. Dán chuỗi FEN: `r1bqkb1r/pppp1ppp/2n2n2/4p3/2B1P3/5N2/PPPP1PPP/RNBQK2R w KQkq - 0 1`.<br>3. Nhập tiêu đề: *"Thử nghiệm khai cuộc"*, nhập nước đi đúng: `Bxf7#` (hoặc `c4f7`).<br>4. Nhấp nút **Xác thực Stockfish** và bấm **Tạo bài toán**. | - Bài toán được tạo thành công (`POST /api/puzzles`), bàn cờ dựng đúng vị trí quân cờ theo FEN.<br>- Động cơ Stockfish xác thực lời giải, sinh cây biến thể (`solution_tree` JSONB) và đánh dấu `solution_verified=true`. | `[ ] Pass`<br>`[ ] Fail` |
| **TC-PUZ-02** | Giáo viên giao bài tập cho lớp học | Teacher | 1. Vào menu **Bài tập** (`/assignments`) -> chọn **+ Giao bài tập**.<br>2. Chọn lớp: `Cờ Vua Thiếu Nhi 2026`.<br>3. Chọn bài tập vừa tạo, đặt hạn nộp (Deadline) sau 3 ngày, số gợi ý tối đa: `2`.<br>4. Bấm **Xác nhận giao bài** (`POST /api/assignments`). | - Bài tập hiển thị trong danh sách bài tập của lớp với trạng thái `Đang mở`.<br>- Tất cả học sinh trong lớp nhận được thông báo về bài tập mới. | `[ ] Pass`<br>`[ ] Fail` |
| **TC-PUZ-03** | Học sinh giải bài tập — Nước đi chính xác | Student | 1. Đăng nhập `student1@cams.test`, vào **Bài tập của tôi**.<br>2. Chọn bài tập được giao, nhấp **Bắt đầu làm bài**.<br>3. Thực hiện kéo thả quân cờ đi nước đi chính xác.<br>4. Nhấp **Nộp bài** (`POST /api/assignments/{id}/submit`). | - Bàn cờ hiển thị hiệu ứng tích xanh ✅, thông báo *"Chính xác! Hoàn thành bài tập"*.<br>- Điểm số ELO nội bộ của học sinh được cộng thêm điểm thưởng.<br>- Trạng thái bài làm chuyển thành `Đã nộp (submitted)`. | `[ ] Pass`<br>`[ ] Fail` |
| **TC-PUZ-04** | Học sinh giải bài tập — Nước đi sai | Student | 1. Tại bài tập, học sinh cố ý đi một nước cờ sai so với lời giải. | - Bàn cờ tự động trả quân cờ về vị trí cũ kèm rung nhẹ hoặc thông báo đỏ ❌: *"Nước đi chưa chính xác, hãy thử lại!"*.<br>- Số lượt thử tăng lên 1, bài toán chưa được tính là hoàn thành. | `[ ] Pass`<br>`[ ] Fail` |
| **TC-PUZ-05** | Giới hạn số lần dùng gợi ý (Hint) | Student | 1. Trong lúc làm bài, nhấp nút **💡 Gợi ý** lần 1.<br>2. Nhấp nút gợi ý lần 2.<br>3. Thử nhấp gợi ý lần 3. | - Lần 1 và 2: Bàn cờ nhấp nháy làm nổi bật ô cờ/quân cờ gợi ý.<br>- Lần 3: Nút gợi ý bị vô hiệu hóa, hiển thị thông báo: *"Bạn đã sử dụng hết số lần gợi ý cho phép (2/2)"*. | `[ ] Pass`<br>`[ ] Fail` |
| **TC-PUZ-06** | Giáo viên chấm điểm thủ công & nhận xét | Teacher | 1. Đăng nhập giáo viên, mở bài tập đã giao.<br>2. Xem danh sách bài nộp của học sinh `student1`.<br>3. Nhấp nút **Chấm điểm & Nhận xét**.<br>4. Nhập điểm: `90/100`, nhận xét: *"Tư duy tốt, cần lưu ý thời gian suy nghĩ"*. Bấm **Lưu** (`POST /api/assignments/{id}/grade/{student_id}`). | - Điểm và nhận xét được lưu thành công (`GradingMethod = manual_teacher`).<br>- Phía học sinh hiển thị biểu tượng người thầy kèm nhận xét chi tiết của giáo viên thay cho biểu tượng Robot chấm tự động. | `[ ] Pass`<br>`[ ] Fail` |
| **TC-PUZ-07** | Giáo viên mở lại bài nộp (Reopen) cho học sinh làm lại | Teacher | 1. Đăng nhập giáo viên phụ trách lớp, vào chi tiết bài tập (`/assignments/:assignmentId`).<br>2. Xem danh sách bài nộp, mở bài nộp của học sinh có điểm chưa đạt hoặc cần làm lại.<br>3. Nhấp nút **Mở lại bài tập (Reopen)** (`POST /api/assignments/{assignment_id}/reopen/{student_id}`).<br>4. Nhập lý do yêu cầu làm lại: *"Em xem lại nước đi câu 2 và câu 4"*. Bấm xác nhận. | - Trạng thái bài nộp của học sinh chuyển từ `submitted`/`graded` sang `reopened`.<br>- Học sinh đăng nhập thấy bài tập được mở lại quyền làm bài, tăng số phiên bản bài làm (`version = version + 1`). | `[ ] Pass`<br>`[ ] Fail` |
| **TC-PUZ-08** | Hệ thống Celery Beat tự động thu bài khi quá hạn nộp (auto_submit_overdue_assignments) | Hệ thống | 1. Thiết lập 1 bài tập có hạn nộp (Deadline) vừa trôi qua.<br>2. Học sinh đã bắt đầu làm bài (`in_progress`) nhưng chưa nhấn nộp bài.<br>3. Quan sát tác vụ nền Celery Beat `auto_submit_overdue_assignments` (chạy định kỳ mỗi 10 phút). | - Worker tự động quét các bài nộp quá hạn chưa nộp.<br>- Tự động khóa và chuyển trạng thái bài làm sang `submitted` (hoặc `graded` tự động nếu cấu hình auto_ai).<br>- Học sinh không thể tiếp tục gửi nước đi mới sau khi đã bị hệ thống tự động thu bài. | `[ ] Pass`<br>`[ ] Fail` |
| **TC-PUZ-09** | Học sinh luyện tập tự do tại /practice và xem thứ hạng ELO tại /leaderboard | Student | 1. Đăng nhập học sinh `student1@cams.test`, ghi nhận điểm ELO ban đầu (ví dụ: 800).<br>2. Vào trang **Luyện tập** (`/practice`), chọn một thế cờ Tactic.<br>3. Kéo thả quân cờ thực hiện giải đúng thế cờ.<br>4. Truy cập trang **Bảng xếp hạng** (`/leaderboard`). | - Bàn cờ luyện tập hiển thị thông báo chúc mừng ✅ và cộng điểm thưởng ELO.<br>- Bảng xếp hạng ELO (`/leaderboard`) cập nhật ngay lập tức thứ hạng và điểm ELO mới của học sinh (`elo_rating` tăng lên). | `[ ] Pass`<br>`[ ] Fail` |

---

> ### 🟡 ĐỢT 2: UAT PHASE 2 — RELEASE v1.5 (CHỜ HOÀN THIỆN CODE)
> *Phạm vi bàn giao:* Phân hệ thanh toán học phí VietQR Level 1 (Hóa đơn, Mã QR, Đối soát thủ công) và Phân hệ Giải đấu Cờ vua Trực tuyến (Thi đấu realtime qua WebSocket, Đồng hồ countdown, Bảng xếp hạng Swiss/Buchholz).  
> *Lưu ý:* Các kịch bản dưới đây được đánh dấu `Pending Dev (v1.5)` — Chưa thực hiện trong Đợt 1.

---

### Module 2.5: Quản lý Học phí & Thanh toán [ĐỢT 2 - Chờ hoàn thiện v1.5]
*Đường dẫn UI:* `/fee-plans`, `/invoices` | *API:* `/api/fee-plans`, `/api/invoices`, `/api/payments`

| Mã TC | Tên tính năng | Vai trò thực hiện | Các bước thao tác | Kết quả mong đợi | Trạng thái |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **TC-PAY-01** | Tạo cấu hình gói học phí (Fee Plan) | Center Admin | 1. Đăng nhập Admin, vào menu **Học phí** -> tab **Gói học phí** (`/fee-plans`).<br>2. Bấm **+ Tạo gói mới**.<br>3. Nhập: Tên gói: `Học phí Khóa K2026`, Số tiền: `500000`, Chu kỳ: `monthly` (Theo tháng), Gán cho lớp: `Cờ Vua Thiếu Nhi 2026`.<br>4. Bấm **Lưu** (`POST /api/fee-plans`). | - Gói học phí mới được tạo và hiển thị rõ ràng trên danh sách với mức tiền `500.000 đ`. | `[ ] Pending Dev (v1.5)` |
| **TC-PAY-02** | Phát hành hóa đơn thu học phí cho học viên | Center Admin | 1. Vào tab **Hóa đơn** (`/invoices`) -> chọn **+ Tạo hóa đơn**.<br>2. Chọn học sinh `Phạm Minh Học`, chọn gói `Học phí Khóa K2026`, hạn thanh toán: ngày cuối tháng.<br>3. Nhấn **Phát hành hóa đơn** (`POST /api/invoices`). | - Hóa đơn mới được tạo với mã hóa đơn duy nhất dạng `INV-2026-XXXX`.<br>- Trạng thái ban đầu của hóa đơn: **`Đã gửi / Chờ thanh toán (sent)`** (khớp với enum `InvoiceStatus.sent`).<br>- Học sinh và phụ huynh nhận được thông báo hóa đơn mới. | `[ ] Pending Dev (v1.5)` |
| **TC-PAY-03** | Hiển thị mã QR thanh toán VietQR chuẩn (EMVCo) | Phụ huynh / Student | 1. Đăng nhập tài khoản phụ huynh `parent1@cams.test`.<br>2. Mở hóa đơn cần thanh toán, chọn nút **Thanh toán VietQR** (`POST /api/invoices/{id}/generate-qr`). | - Hiển thị mã QR tiêu chuẩn VietQR (EMVCo).<br>- Quét thử bằng app ngân hàng hiển thị đúng: Số tiền `500.000 đ`, Ngân hàng `MB Bank`, Số tài khoản `1234567890`, Nội dung chuyển khoản chứa đúng mã hóa đơn `INV-2026-XXXX`. | `[ ] Pending Dev (v1.5)` |
| **TC-PAY-04** | Admin duyệt xác nhận thanh toán (Level 1 Manual) | Center Admin | 1. Sau khi phụ huynh chuyển khoản, Admin kiểm tra sao kê ngân hàng.<br>2. Admin vào tab Hóa đơn, tìm đúng mã `INV-2026-XXXX` đang ở trạng thái **`Đã gửi / Chờ thanh toán (sent)`**.<br>3. Nhấp nút **Xác nhận đã thu tiền** (`POST /api/payments/confirm/{invoice_id}`).<br>4. Nhập ghi chú đối soát và bấm **Xác nhận**. | - Trạng thái hóa đơn lập tức chuyển thành **`Đã thanh toán (paid)`** kèm ngày giờ thu tiền.<br>- Bản ghi `payments` được tạo thành công với `payment_level = level1_manual`, trạng thái `success`.<br>- Phụ huynh và học sinh nhận được thông báo xác nhận: *"Học phí đã được thanh toán thành công"*. | `[ ] Pending Dev (v1.5)` |
| **TC-PAY-05** | Xử lý hóa đơn quá hạn (Overdue) | Hệ thống | 1. Xem xét các hóa đơn có hạn thanh toán trước ngày hiện tại và chưa được thanh toán. | - Hệ thống tự động chuyển trạng thái hóa đơn sang `Quá hạn (overdue)`.<br>- Dòng hóa đơn được đánh dấu cảnh báo màu đỏ trong danh sách quản lý của Admin. | `[ ] Pending Dev (v1.5)` |
| **TC-PAY-06** | Cách ly dữ liệu hóa đơn giữa các gia đình | Phụ huynh | 1. Đăng nhập bằng tài khoản phụ huynh học sinh khác.<br>2. Cố tình truy cập xem hóa đơn của học sinh `student1`. | - Hệ thống báo lỗi không tìm thấy hóa đơn hoặc từ chối truy cập (HTTP 404 Not Found).<br>- Phụ huynh chỉ nhìn thấy hóa đơn của con mình. | `[ ] Pending Dev (v1.5)` |
| **TC-PAY-07** | Chống xác nhận thanh toán trùng lặp / Idempotency khi hóa đơn đã ở trạng thái paid | Center Admin | 1. Chọn hóa đơn `INV-2026-XXXX` đã được xác nhận thanh toán trước đó (đang ở trạng thái `paid`).<br>2. Cố tình nhấn nút **Xác nhận thanh toán** lần thứ hai hoặc gửi request `POST /api/payments/confirm/{invoice_id}` (hoặc gọi webhook với cùng `idempotency_key` đã xử lý thành công).<br>3. Kiểm tra thông báo phản hồi của hệ thống và bảng dữ liệu thanh toán. | - Hệ thống từ chối thực hiện giao dịch trùng lặp, trả về cảnh báo hoặc mã lỗi HTTP 400: *"Hóa đơn này đã được thanh toán, không thể xác nhận lại"*/IDEMPOTENT_IGNORED.<br>- Số tiền không bị ghi nhận trùng lặp trong hệ thống báo cáo; bảng `payments` không sinh thêm bản ghi dư thừa cho cùng một hóa đơn. | `[ ] Pending Dev (v1.5)` |

---

### Module 2.6: Quản lý & Thi đấu Giải đấu Cờ vua Realtime [ĐỢT 2 - Chờ hoàn thiện v1.5]
*Đường dẫn UI:* `/tournaments`, `/tournaments/:id`, `/tournaments/:id/game/:gameId` | *API:* `/api/tournaments` | *Realtime:* `WS /ws/game/{game_id}`

| Mã TC | Tên tính năng | Vai trò thực hiện | Các bước thao tác | Kết quả mong đợi | Trạng thái |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **TC-TOUR-01** | Tạo mới giải đấu cờ vua | Teacher / Admin | 1. Vào menu **Giải đấu** (`/tournaments`) -> chọn **+ Tạo giải đấu**.<br>2. Nhập: Tên giải: `Giải Cờ Vua Mùa Thu 2026`, Thể thức: `Swiss System (Hệ Thụy Sĩ)`, Thời gian: `5+3 (Blitz)`, Số vòng: `3`, Số người tối đa: `8`.<br>3. Nhấp **Tạo giải đấu** (`POST /api/tournaments`). | - Giải đấu hiển thị trong danh sách giải đấu với trạng thái `Đang mở đăng ký (registration)`. | `[ ] Pending Dev (v1.5)` |
| **TC-TOUR-02** | Học sinh đăng ký tham gia giải đấu | Student 1 & 2 | 1. `student1` và `student2` lần lượt đăng nhập vào mục **Giải đấu**.<br>2. Nhấp nút **Đăng ký tham gia** tại giải `Giải Cờ Vua Mùa Thu 2026` (`POST /api/tournaments/{id}/register`). | - Thông báo đăng ký thành công.<br>- Nút chuyển thành `Đã đăng ký` (không được nhấn lại).<br>- Danh sách kỳ thủ của giải hiển thị đủ cả 2 học sinh. | `[ ] Pending Dev (v1.5)` |
| **TC-TOUR-03** | Bắt đầu giải đấu & Bắt cặp vòng 1 tự động | Teacher | 1. Đăng nhập giáo viên quản lý giải, mở trang chi tiết giải đấu.<br>2. Nhấp nút **Bắt đầu giải đấu** (`POST /api/tournaments/{id}/start`).<br>3. Xác nhận chốt danh sách kỳ thủ. | - Trạng thái giải đấu chuyển sang `Đang diễn ra (in_progress)`.<br>- Thuật toán ghép cặp Swiss tự động sinh cặp đấu Vòng 1: `Phạm Minh Học (Trắng) vs Hoàng Bảo Long (Đen)`. | `[ ] Pending Dev (v1.5)` |
| **TC-TOUR-04** | Đấu cờ trực tiếp thời gian thực (WebSocket) | Student 1 & 2 | 1. `student1` và `student2` mở 2 cửa sổ/máy tính khác nhau, cùng nhấn **Vào phòng thi đấu**.<br>2. Kết nối WebSocket tới `ws://localhost:8000/ws/game/{id}?token=<JWT>`.<br>3. `student1` (quân Trắng) thực hiện nước đi đầu tiên `e2-e4`. Quan sát màn hình của `student2` (quân Đen). | - Màn hình của `student2` nhận gói tin broadcast và cập nhật quân cờ `e4` ngay lập tức mà không cần tải lại trang.<br>- Đồng hồ của Trắng dừng lại và đồng hồ của Đen bắt đầu đếm ngược chính xác theo thời gian thực. | `[ ] Pending Dev (v1.5)` |
| **TC-TOUR-05** | Xử lý kết thúc ván đấu khi xin thua (Resign) | Student 2 | 1. Khi đang trong ván đấu, `student2` nhấn nút **Xin thua (Resign)**.<br>2. Xác nhận hộp thoại đồng ý xin thua. | - Ván đấu kết thúc ngay lập tức, hiển thị bảng kết quả: *"Trắng thắng do Đen xin thua"*.<br>- Bản ghi `tournament_games` cập nhật `result = white_wins`, biên bản PGN được lưu lại đầy đủ.<br>- Điểm ELO của 2 kỳ thủ được tính toán cập nhật lại. | `[ ] Pending Dev (v1.5)` |
| **TC-TOUR-06** | Xử lý rụng cờ (Timeout) khi hết thời gian | Student 1 & 2 | 1. Một bên người chơi để đồng hồ chạy về `00:00` mà không đi quân. | - Server phát hiện hết giờ, gửi sự kiện kết thúc ván.<br>- Thông báo người hết giờ bị xử thua theo luật cờ vua. | `[ ] Pending Dev (v1.5)` |
| **TC-TOUR-07** | Cập nhật bảng xếp hạng giải đấu (Standings) | Bất kỳ | 1. Mở tab **Bảng xếp hạng (Standings)** của giải đấu sau khi kết thúc vòng đấu. | - Học sinh thắng được ghi nhận `1 điểm`, học sinh thua `0 điểm`.<br>- Thứ hạng hiển thị chính xác theo điểm số và các hệ số phụ (Buchholz). | `[ ] Pending Dev (v1.5)` |
| **TC-TOUR-08** | Xử lý ván đấu Hòa (0.5 điểm) & Trọng tài cập nhật kết quả ván đấu thủ công, kết thúc giải (completed) | Teacher / Student | 1. Hai kỳ thủ chấp thuận đề nghị hòa cờ (Draw) trong ván đấu.<br>2. Hoặc Giáo viên/Trọng tài can thiệp cập nhật kết quả hòa thủ công qua API `PUT /api/tournaments/{id}/games/{game_id}` (`result = draw`).<br>3. Sau khi kết thúc tất cả các ván của vòng đấu cuối, Giáo viên bấm nút **Kết thúc giải đấu**. | - Ván đấu hòa ghi nhận `0.5 điểm` cho mỗi kỳ thủ trong bảng xếp hạng `tournament_standings`.<br>- Hệ thống tính toán điểm và hệ số phụ Buchholz chuẩn xác.<br>- Trạng thái giải đấu chuyển từ `in_progress` sang `completed`, danh hiệu giải đấu được lưu cố định. | `[ ] Pending Dev (v1.5)` |

---

## 3. BẢNG KỊCH BẢN UAT PHI CHỨC NĂNG (NON-FUNCTIONAL UAT)

> **Hướng dẫn phân định vai trò thực hiện kiểm thử phi chức năng:**
> - **🟢 [Dành cho Người dùng nghiệp vụ]:** Dành cho Giáo viên, Quản trị viên trung tâm hoặc Học viên trải nghiệm trực quan trên trình duyệt máy tính, điện thoại, máy tính bảng để đánh giá tính thẩm mỹ, độ mượt mà khi di chuyển quân cờ và khả năng tương thích màn hình.
> - **🔵 [Dành cho QA / Kỹ thuật]:** Dành cho Kỹ sư QA / Đội ngũ kỹ thuật sử dụng công cụ chuyên dụng như **Trình duyệt DevTools (F12)** (tab Network, Console, WS frames) hoặc **Postman / cURL** để đo lường mili-giây độ trễ, kiểm tra mã lỗi HTTP (`401`, `404`) và xác thực an toàn bảo mật.

### 3.1 Hiệu năng & Tốc độ phản hồi (Performance)

| Mã TC | Hạng mục kiểm tra | Phân loại đối tượng | Tiêu chuẩn chấp nhận (Acceptance Criteria) | Cách thức kiểm tra thực tế | Kết quả đo lường | Trạng thái |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **NFR-PERF-01** | Tốc độ phản hồi API thông thường | **[Dành cho QA / Kỹ thuật]** | Thời gian phản hồi P95 **< 500ms** cho các thao tác xem danh sách, chi tiết lớp, bài tập. | Mở tab Network trên DevTools (F12) của trình duyệt, lọc các request `/api/` khi tải các trang chính. | - Tải Dashboard: ___ ms<br>- Tải Lớp học: ___ ms<br>- Tải Bài tập: ___ ms | `[ ] Pass`<br>`[ ] Fail` |
| **NFR-PERF-02** | Tốc độ quét sách PDF của AI Scanner | **[Dành cho QA / Kỹ thuật]** | Tổng thời gian xử lý **< 30 giây/trang PDF** (Theo tiêu chuẩn NFR-01). | Tải lên file PDF 2 trang chuẩn, bấm đồng hồ từ lúc nhấn Quét đến lúc hiển thị kết quả. | - Tổng thời gian: ___ giây<br>- Trung bình: ___ giây/trang | `[ ] Pass`<br>`[ ] Fail` |
| **NFR-PERF-03** | Độ trễ Realtime khi truyền nước đi cờ | **[Dành cho QA / Kỹ thuật]** | Độ trễ truyền nhận gói tin nước đi qua WebSocket **< 1000ms** trong điều kiện mạng thông thường. | Quan sát thời điểm nhấc chuột thả quân ở máy A đến khi quân cờ xuất hiện trên màn hình máy B qua DevTools WS frame. | - Độ trễ đo được: ~ ___ ms | `[ ] Pass`<br>`[ ] Fail` |

---

### 3.2 Giao diện, Trải nghiệm & Tính tương thích (UI/UX Compatibility)

| Mã TC | Hạng mục kiểm tra | Phân loại đối tượng | Tiêu chuẩn chấp nhận | Các bước kiểm tra thực tế | Kết quả kiểm tra | Trạng thái |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **NFR-UI-01** | Tương thích trình duyệt Desktop | **[Dành cho Người dùng nghiệp vụ]** | Giao diện hiển thị chuẩn xác, không vỡ khung trên các trình duyệt phổ biến. | Mở hệ thống trên: Google Chrome, Microsoft Edge, Mozilla Firefox và Apple Safari. | `[ ]` Chrome: OK<br>`[ ]` Edge: OK<br>`[ ]` Firefox: OK<br>`[ ]` Safari: OK | `[ ] Pass`<br>`[ ] Fail` |
| **NFR-UI-02** | Độ co giãn linh hoạt (Responsive Mobile/Tablet) | **[Dành cho Người dùng nghiệp vụ]** | Giao diện tự động co dãn trên màn hình điện thoại (375px - 414px) và máy tính bảng (768px). | Bật chế độ Responsive Mode trên DevTools (F12), kiểm tra bố cục bàn cờ và menu: không bị tràn ngang, menu biến thành nút 3 gạch (hamburger). | - Bàn cờ co giãn chuẩn kích thước màn hình nhỏ, quân cờ bấm chạm mượt mà. | `[ ] Pass`<br>`[ ] Fail` |
| **NFR-UI-03** | Bàn cờ hiển thị sắc nét & Thao tác kéo thả | **[Dành cho Người dùng nghiệp vụ]** | Quân cờ SVG sắc nét, hỗ trợ cả 2 thao tác: Bấm ô đầu - bấm ô đích HOẶC Kéo-thả quân cờ. | Thử di chuyển quân cờ bằng chuột và bằng thao tác cảm ứng chạm trên thiết bị cảm ứng. | - Thao tác phản hồi chính xác, không bị kẹt hay giật lag quân cờ. | `[ ] Pass`<br>`[ ] Fail` |
| **NFR-UI-04** | Kiểm tra lỗi JavaScript Console | **[Dành cho QA / Kỹ thuật]** | Không có lỗi nghiêm trọng (đỏ `Uncaught Exception`) làm dừng ứng dụng. | Mở tab Console (F12) duyệt qua toàn bộ các màn hình chính của hệ thống. | - Không có lỗi cú pháp hoặc lỗi crash React. | `[ ] Pass`<br>`[ ] Fail` |

---

### 3.3 An toàn, Bảo mật & Phân quyền truy cập (Security & RBAC)

| Mã TC | Hạng mục kiểm tra | Phân loại đối tượng | Tiêu chuẩn chấp nhận | Các bước kiểm tra thực tế | Kết quả kiểm tra | Trạng thái |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **NFR-SEC-01** | Kiểm tra ma trận phân quyền giữa các vai trò (RBAC) | **[Dành cho QA / Kỹ thuật]** | Mỗi vai trò chỉ thao tác đúng nghiệp vụ được cấp phép, không thể can thiệp chéo. | Kiểm tra đối chiếu ma trận phân quyền theo bảng dưới: học sinh không thể sửa điểm, giáo viên không thể vào phần tài chính. | Đạt tiêu chuẩn phân quyền chặt chẽ. | `[ ] Pass`<br>`[ ] Fail` |
| **NFR-SEC-02** | Chống rò rỉ dữ liệu đa trung tâm (Tenant Isolation) | **[Dành cho QA / Kỹ thuật]** | Người dùng thuộc Trung tâm A **tuyệt đối không** nhìn thấy dữ liệu của Trung tâm B. | Cố tình truy cập ID lớp học/học sinh của trung tâm khác trên đường dẫn API qua Postman / DevTools. | Hệ thống trả về lỗi `404 Not Found` (không trả về 403 để tránh đoán ID). | `[ ] Pass`<br>`[ ] Fail` |
| **NFR-SEC-03** | Chặn truy cập API không có xác thực (Unauthorized) | **[Dành cho QA / Kỹ thuật]** | Không thể gọi các API nội bộ nếu không gửi kèm mã khóa Token hợp lệ. | Dùng Postman hoặc trình duyệt gọi trực tiếp `GET http://localhost:8000/api/classes` mà không có header Bearer Token. | Hệ thống chặn và trả về mã lỗi `401 Unauthorized`. | `[ ] Pass`<br>`[ ] Fail` |
| **NFR-SEC-04** | An toàn đường dẫn file bài quét | **[Dành cho QA / Kỹ thuật]** | File PDF sách cờ tải lên không bị truy cập công khai tự do. | Lấy đường dẫn file quét thử mở trên tab ẩn danh không đăng nhập qua Postman/Browser. | Bị từ chối truy cập (yêu cầu chữ ký URL HMAC có thời hạn qua `/api/files/{path}`). | `[ ] Pass`<br>`[ ] Fail` |

---

## 4. MA TRẬN PHÂN QUYỀN THAM CHIẾU (RBAC ACCESS MATRIX)

*(Dùng làm căn cứ đánh giá kịch bản `NFR-SEC-01`)*

| Nghiệp vụ / Quyền hạn | Quản trị cấp cao (Super Admin) | Quản trị trung tâm (Center Admin) | Giáo viên (Teacher) | Học sinh (Student) | Phụ huynh (Parent) |
| :--- | :---: | :---: | :---: | :---: | :---: |
| **Quản trị đa trung tâm, tạo Center mới** | **Toàn quyền** | Bị từ chối | Bị từ chối | Bị từ chối | Bị từ chối |
| **Cấu hình cài đặt trung tâm, thương hiệu** | **Toàn quyền** | **Phạm vi Trung tâm** | Bị từ chối | Bị từ chối | Bị từ chối |
| **Quản lý tài khoản thành viên (User CRUD)**| **Toàn hệ thống** | **Phạm vi Trung tâm** | Bị từ chối | Bị từ chối | Bị từ chối |
| **Liên kết / Hủy liên kết Phụ huynh - Học sinh**| **Cho phép** | **Cho phép** | Bị từ chối | Bị từ chối | Bị từ chối |
| **Tạo lớp học mới** | **Cho phép** | **Cho phép** | **Cho phép** | Bị từ chối | Bị từ chối |
| **Thêm / Bớt học sinh trong lớp** | **Cho phép** | **Cho phép** | **Cho phép (lớp mình)**| Bị từ chối | Bị từ chối |
| **Quét bài tập cờ bằng AI Scanner** | **Cho phép** | **Cho phép** | **Cho phép** | Bị từ chối | Bị từ chối |
| **Duyệt / Sửa kết quả FEN bài toán** | **Cho phép** | **Cho phép** | **Cho phép** | Bị từ chối | Bị từ chối |
| **Giao bài tập & Đặt hạn nộp** | **Cho phép** | **Cho phép** | **Cho phép** | Bị từ chối | Bị từ chối |
| **Làm bài tập & Nộp kết quả** | Bị từ chối | Bị từ chối | Bị từ chối | **Cho phép** | Bị từ chối |
| **Chấm điểm thủ công & Nhận xét** | **Cho phép** | **Cho phép** | **Cho phép** | Bị từ chối | Bị từ chối |
| **Cấu hình bảng giá học phí** | **Cho phép** | **Phạm vi Trung tâm** | Bị từ chối | Bị từ chối | Bị từ chối |
| **Phát hành hóa đơn học phí** | **Cho phép** | **Phạm vi Trung tâm** | Bị từ chối | Bị từ chối | Bị từ chối |
| **Xác nhận đã nhận chuyển khoản (Level 1)** | **Cho phép** | **Phạm vi Trung tâm** | Bị từ chối | Bị từ chối | Bị từ chối |
| **Xem hóa đơn & Mã VietQR thanh toán** | **Cho phép** | **Cho phép** | Bị từ chối | **Xem của mình** | **Xem của con** |
| **Tạo giải đấu & Bắt cặp thi đấu** | **Cho phép** | **Cho phép** | **Cho phép** | Bị từ chối | Bị từ chối |
| **Đăng ký tham gia thi đấu giải** | Bị từ chối | Bị từ chối | Bị từ chối | **Cho phép** | Bị từ chối |
| **Xem Bảng xếp hạng ELO & Lịch học** | **Cho phép** | **Cho phép** | **Cho phép** | **Cho phép** | **Cho phép** |

---

## 5. BẢNG TỔNG KẾT & TIÊU CHÍ NGHIỆM THU TỪNG GIAI ĐOẠN (PHASED SIGN-OFF)

### 5.1 Thống kê tiến độ thực hiện UAT theo Đợt bàn giao

#### Bảng 5.1.1: Tổng kết Đợt 1 — Core MVP v1.0 (Kiểm thử ngay)

| Phân hệ (Module) | Mã kịch bản | Số lượng | Số Pass | Số Fail | Tỷ lệ (%) | Trạng thái triển khai |
| :--- | :--- | :---: | :---: | :---: | :---: | :--- |
| **1. Xác thực & Phân quyền** | `TC-AUTH-01` → `TC-AUTH-06` | 6 | | | | Sẵn sàng test ngay |
| **2. Quản lý Lớp học & Thành viên** | `TC-CLASS-01` → `TC-CLASS-06`, `TC-USER-01` | 7 | | | | Sẵn sàng test ngay |
| **3. AI Scanner Quét Sách PDF** | `TC-SCAN-01` → `TC-SCAN-07` | 7 | | | | Sẵn sàng test ngay |
| **4. Kho Bài Toán & Luyện Tập** | `TC-PUZ-01` → `TC-PUZ-09` | 9 | | | | Sẵn sàng test ngay |
| **5. Kiểm thử Phi Chức Năng (NFR)** | `NFR-PERF (3)`, `NFR-UI (4)`, `NFR-SEC (4)` | 11 | | | | Sẵn sàng test ngay |
| **TỔNG KẾT ĐỢT 1 (Core v1.0)** | *(29 chức năng + 11 phi chức năng)* | **40** | | | | **Kiểm thử nghiệm thu ngay** |

---

#### Bảng 5.1.2: Tổng kết Đợt 2 — Release v1.5 (Chờ hoàn thiện code)

| Phân hệ (Module) | Mã kịch bản | Số lượng | Số Pass | Số Fail | Tỷ lệ (%) | Trạng thái triển khai |
| :--- | :--- | :---: | :---: | :---: | :---: | :--- |
| **1. Học Phí & Thanh Toán VietQR** | `TC-PAY-01` → `TC-PAY-07` | 7 | | | | Pending Dev (v1.5) |
| **2. Giải Đấu Cờ Vua Realtime** | `TC-TOUR-01` → `TC-TOUR-08` | 8 | | | | Pending Dev (v1.5) |
| **TỔNG KẾT ĐỢT 2 (Release v1.5)** | *(Chức năng Thanh toán & Giải đấu)* | **15** | | | | **Nghiệm thu sau khi Dev xong** |

> **TỔNG CỘNG CẢ 2 ĐỢT BÀN GIAO TOÀN HỆ THỐNG:** **55 kịch bản** (Đợt 1: 40 kịch bản bao gồm NFR; Đợt 2: 15 kịch bản v1.5).

---

### 5.2 Tiêu chí chấp nhận & Ký duyệt nghiệm thu độc lập từng Đợt

#### 5.2.1 Biên bản Nghiệm thu ĐỢT 1 (Core MVP v1.0)

**Tiêu chuẩn Acceptance Gate Đợt 1:**
- [ ] 29/29 kịch bản chức năng Đợt 1 đạt kết quả **Pass ≥ 95%** (Không còn lỗi mức độ Blocker/Critical).
- [ ] AI Scanner bóc tách chính xác bàn cờ, hỗ trợ đầy đủ luồng duyệt FEN (`auto_approved` và duyệt thủ công).
- [ ] Quản lý thành viên, lớp học, lịch học `/schedule`, giao bài tập và luyện tập puzzle mượt mà.
- [ ] Ma trận RBAC bảo vệ nghiêm ngặt, cơ chế Tenant Isolation luôn trả về `404 Not Found` khi truy cập sai trung tâm.

**Xác nhận Ký duyệt Đợt 1 (Core MVP v1.0):**

| Đại diện các bên tham gia | Họ và tên | Chức vụ | Ngày ký | Chữ ký xác nhận |
| :--- | :--- | :--- | :--- | :--- |
| **Đại diện Đội ngũ Kỹ thuật** | | Lead Backend / Tech Lead | ... / ... / 2026 | |
| **Đại diện Kiểm định Chất lượng** | | QA / Test Lead | ... / ... / 2026 | |
| **Đại diện Khối Chuyên môn & GV** | | Trưởng bộ môn Cờ Vua | ... / ... / 2026 | |
| **Đại diện Ban Giám Đốc Học Viện** | | Giám đốc Trung tâm / PO | ... / ... / 2026 | |

---

#### 5.2.2 Biên bản Nghiệm thu ĐỢT 2 (Release v1.5)

**Tiêu chuẩn Acceptance Gate Đợt 2:**
- [ ] 15/15 kịch bản Đợt 2 đạt kết quả **Pass 100%**.
- [ ] Quy trình tạo hóa đơn (`InvoiceStatus.sent`), tạo mã VietQR chuẩn EMVCo và thanh toán xác nhận học phí VietQR vận hành chính xác, chống xác nhận trùng lặp (`TC-PAY-07`).
- [ ] Đấu cờ trực tuyến qua WebSocket đồng bộ thời gian thực hai chiều, xử lý chính xác kết quả ván đấu Thắng/Hòa/Thua, đồng hồ cờ và đóng giải đấu (`TC-TOUR-08`).

**Xác nhận Ký duyệt Đợt 2 (Release v1.5):**

| Đại diện các bên tham gia | Họ và tên | Chức vụ | Ngày ký | Chữ ký xác nhận |
| :--- | :--- | :--- | :--- | :--- |
| **Đại diện Đội ngũ Kỹ thuật** | | Lead Backend / Tech Lead | ... / ... / 2026 | |
| **Đại diện Kiểm định Chất lượng** | | QA / Test Lead | ... / ... / 2026 | |
| **Đại diện Khối Chuyên môn & GV** | | Trưởng bộ môn Cờ Vua | ... / ... / 2026 | |
| **Đại diện Ban Giám Đốc Học Viện** | | Giám đốc Trung tâm / PO | ... / ... / 2026 | |
