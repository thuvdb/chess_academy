# Cẩm Nang Dành Cho Quản Trị Viên Trung Tâm (Admin Guide)

> **Hệ thống:** CAMS — Chess Academy Management System  
> **Phiên bản áp dụng:** Core MVP v1.0 (Có lộ trình v1.5)  
> **Dành cho:** Quản trị viên trung tâm (Center Admin), Quản trị cấp cao (Super Admin)  
> **Ngày cập nhật:** 17/10/2026

---

## Mục Lục

1. [Tổng quan Bảng điều khiển (Dashboard thống kê trung tâm)](#1-tổng-quan-bảng-điều-khiển-dashboard-thống-kê-trung-tâm)
2. [Quản lý thành viên & Nhân sự (/members)](#2-quản-lý-thành-viên--nhân-sự-members)
   - 2.1 Xem và tìm kiếm danh sách người dùng
   - 2.2 Tạo tài khoản mới theo từng vai trò (Teacher, Student, Parent)
   - 2.3 Thao tác Liên kết tài khoản Phụ huynh với Học sinh
   - 2.4 Chỉnh sửa thông tin & Khóa/Mở khóa tài khoản
3. [Quản lý toàn bộ Lớp học (/classes)](#3-quản-lý-toàn-bộ-lớp-học-classes)
   - 3.1 Tạo lớp học mới và thiết lập thông số
   - 3.2 Phân công giáo viên phụ trách & Thiết lập cấp độ
   - 3.3 Quản lý sĩ số tối đa và bảo vệ hạn mức lớp
   - 3.4 Giám sát học viên và sĩ số các lớp
4. [Tính năng đang phát triển (Lộ trình v1.5)](#4-tính-năng-đang-phát-triển-lộ-trình-v15)
   - 4.1 💰 Thiết lập Gói học phí trung tâm (/fee-plans)
   - 4.2 🧾 Phát hành Hóa đơn thu học phí & Xác nhận thanh toán VietQR Level 1 (/invoices)
   - 4.3 🏆 Tổ chức và điều hành Giải đấu cờ vua trực tuyến (/tournaments)

---

## 1. Tổng quan Bảng điều khiển (Dashboard thống kê trung tâm)

Sau khi đăng nhập với tài khoản Quản trị viên trung tâm (ví dụ: `admin@cams.test`), trang **Tổng quan** (`/`) là trung tâm chỉ huy hoạt động đào tạo của cơ sở:

- **Các chỉ số chính:**
  - **Tổng số lớp học:** Số lượng lớp đang hoạt động trong trung tâm.
  - **Tổng số học viên:** Số học sinh đang theo học thực tế.
  - **Đội ngũ giáo viên:** Số lượng giáo viên, huấn luyện viên trực thuộc trung tâm.
  - **Hoạt động bài tập:** Thống kê số bài tập đã giao và tỷ lệ hoàn thành bài tập của học sinh trong tuần.
- **Thanh điều hướng Sidebar dành cho Admin:** Hiển thị đầy đủ quyền quản trị cao nhất: *Tổng quan, Lớp học, Lịch học, Quét AI bàn cờ, Kho bài tập cờ, Luyện tập, Bài tập về nhà, Bảng xếp hạng, Gói học phí, Học phí & Hóa đơn, Giải đấu, Quản lý thành viên, Hồ sơ cá nhân, Cài đặt*.

---

## 2. Quản lý thành viên & Nhân sự (`/members`)

Trang **Quản lý thành viên** cho phép Admin nắm toàn quyền kiểm soát nhân sự, tài khoản học viên và phụ huynh thuộc trung tâm mình quản lý.

### 2.1 Xem và tìm kiếm danh sách người dùng

1. Nhấp chọn **Quản lý thành viên** trên thanh điều hướng bên trái.
2. Bảng danh sách hiển thị chi tiết: Họ tên, Email, Số điện thoại, Vai trò (kèm huy hiệu màu sắc trực quan) và Cơ sở trực thuộc.
3. **Tìm kiếm nhanh:** Gõ tên hoặc email vào ô tìm kiếm ở góc trên để lọc tức thì danh sách thành viên.

### 2.2 Tạo tài khoản mới theo từng vai trò

Để cấp tài khoản mới cho nhân sự hoặc học viên mới ghi danh:

1. Nhấp nút **+ Thêm thành viên** (với Super Admin: nút **Tạo tài khoản / Admin**).
2. Hộp thoại tạo thành viên xuất hiện, nhập các thông tin:
   - **Họ và tên:** Nhập tên đầy đủ (ví dụ: `Trần Văn Giáo` hoặc `Phạm Minh Học`).
   - **Email đăng nhập:** Địa chỉ email hợp lệ của người dùng (dùng làm tên đăng nhập).
   - **Mật khẩu khởi tạo:** Thiết lập mật khẩu ban đầu (ví dụ: `Teacher@2026!` hoặc `Student@2026!`).
   - **Vai trò (Role):** Chọn một trong các vai trò phù hợp:
     - 👨‍🏫 **Giáo viên (Teacher):** Có quyền quản lý lớp được phân công, dùng AI Scanner, tạo bài tập, chấm điểm.
     - 🎓 **Học sinh (Student):** Chỉ có quyền làm bài tập, luyện tập tự do và tham gia giải đấu.
     - 👨‍👩‍👧 **Phụ huynh (Parent):** Theo dõi tiến độ học tập và hóa đơn học phí của con.
     - 🏢 **Admin trung tâm (Center Admin):** Dành cho cấp phó quản lý trung tâm (nếu có).
3. Nhấp **Xác nhận tạo** để hoàn tất.

### 2.3 Thao tác Liên kết tài khoản Phụ huynh với Học sinh

Để phụ huynh có thể theo dõi kết quả học tập và nhận thông báo học phí của con mình, Admin cần thực hiện liên kết giữa 2 tài khoản:

1. Trong danh sách thành viên, tìm tài khoản của **Học sinh** cần liên kết.
2. Tại cột Thao tác bên phải dòng của học sinh, nhấp vào nút **Liên kết Phụ huynh**.
3. Một danh sách tìm kiếm tài khoản phụ huynh hiện ra:
   - Chọn tài khoản phụ huynh tương ứng (ví dụ: `Phạm Văn Cha - parent1@cams.test`).
4. Nhấp nút **Xác nhận liên kết**.
5. Hệ thống sẽ thiết lập quan hệ liên kết dữ liệu an toàn. Khi phụ huynh đăng nhập vào hệ thống, họ sẽ xem được lớp học, bài tập và hóa đơn của học sinh này một cách độc lập và bảo mật.

### 2.4 Chỉnh sửa thông tin & Khóa/Mở khóa tài khoản

- **Chỉnh sửa:** Nhấp nút **Sửa** tại dòng thành viên để cập nhật vai trò, họ tên hoặc đổi cơ sở trực thuộc (dành cho Super Admin).
- **Khóa tài khoản tạm thời:** Nếu học viên tạm nghỉ học dài hạn hoặc giáo viên thôi việc, Admin có thể chuyển trạng thái sang **Đã khóa** để vô hiệu hóa quyền đăng nhập mà vẫn giữ nguyên lịch sử điểm số và bài tập trong quá khứ.

---

## 3. Quản lý toàn bộ Lớp học (`/classes`)

### 3.1 Tạo lớp học mới và thiết lập thông số

Khi trung tâm khai giảng khóa học mới:

1. Nhấp chọn **Lớp học** trên thanh điều hướng Sidebar.
2. Nhấp nút **+ Tạo lớp học mới**.
3. Điền các trường thông tin chuẩn hóa:
   - **Tên lớp học:** Đặt tên rõ ràng (ví dụ: `Cờ Vua Thiếu Nhi K2026`, `Lớp Chiến Thuật Nâng Cao`).
   - **Cấp độ giảng dạy:** Chọn một trong 4 cấp độ:
     - *Cơ bản (Beginner)*
     - *Trung cấp (Intermediate)*
     - *Nâng cao (Advanced)*
     - *Thi đấu (Tournament)*
   - **Giáo viên phụ trách:** Chọn giáo viên từ danh sách nhân sự của trung tâm.
   - **Sĩ số tối đa (Max Students):** Nhập giới hạn học viên (ví dụ: `15` hoặc `20`).
   - **Thời khóa biểu tuần (Schedule):** Thiết lập các ngày học định kỳ và khung giờ (ví dụ: Thứ 3 & Thứ 5, từ 18:00 đến 19:30).
4. Nhấp nút **Lưu lại**. Lớp học sẽ xuất hiện ngay trên danh sách với sĩ số khởi tạo là `0/[Sĩ_số_tối_đa]`.

### 3.2 Phân công giáo viên phụ trách

- Quản trị viên có toàn quyền thay đổi giáo viên phụ trách lớp bất kỳ lúc nào bằng cách vào trang chỉnh sửa lớp và chọn lại giáo viên mới.
- Giáo viên sau khi được phân công sẽ ngay lập tức nhìn thấy lớp học này trong tài khoản cá nhân của mình để điểm danh, giao bài và theo dõi tiến độ.

### 3.3 Quản lý sĩ số tối đa và bảo vệ hạn mức lớp

- Cơ chế bảo vệ hạn mức của CAMS ngăn ngừa tình trạng quá tải lớp học:
  - Khi giáo viên hoặc admin thêm học sinh vượt quá con số `Sĩ số tối đa` đã cài đặt, hệ thống sẽ tự động chặn thao tác và cảnh báo: *"Lớp học đã đạt sĩ số tối đa, không thể ghi danh thêm"*.
  - Muốn nhận thêm học sinh, Admin chỉ cần mở chỉnh sửa lớp học và nâng hạn mức sĩ số tối đa lên con số mong muốn.

### 3.4 Giám sát học viên và sĩ số các lớp

- Admin có thể nhấp vào bất kỳ lớp học nào để xem tình hình học viên:
  - Xem danh sách học sinh đang học tích cực (`Active`).
  - Xem danh sách học sinh đã rút hoặc bảo lưu (`Inactive`).
  - Kiểm tra thời khóa biểu tuần được đồng bộ tự động lên trang **Lịch học** (`/schedule`).

---

## 4. Tính năng đang phát triển (Lộ trình v1.5)

> 🔔 **Thông báo:** Các tính năng dưới đây đang được đội ngũ kỹ thuật hoàn thiện và sẽ chính thức phát hành trong phiên bản **v1.5 / v2.0**.

### 4.1 💰 Thiết lập Gói học phí trung tâm (`/fee-plans`)

*Dự kiến ra mắt: Phiên bản v1.5*

- **Cấu hình bảng giá linh hoạt:** Admin có thể tạo các gói học phí theo tháng, theo khóa hoặc theo số buổi (ví dụ: *Gói Khóa K2026 - 500.000 đ/tháng*).
- **Gán gói cho lớp học:** Tự động áp dụng mức học phí tương ứng cho từng lớp học cụ thể trong trung tâm.

### 4.2 🧾 Phát hành Hóa đơn thu học phí & Xác nhận thanh toán VietQR Level 1 (`/invoices`)

*Dự kiến ra mắt: Phiên bản v1.5*

- **Phát hành hóa đơn định kỳ:** Tự động hoặc thủ công tạo hóa đơn học phí gửi đến từng học viên kèm mã định danh duy nhất (ví dụ: `INV-2026-0001`).
- **Tích hợp mã VietQR tự động:** Hóa đơn tự động sinh mã VietQR chuẩn ngân hàng với đúng số tài khoản trung tâm, số tiền và nội dung chuyển khoản.
- **Đối soát thủ công Level 1 tiện lợi:** Sau khi phụ huynh chuyển khoản, Admin kiểm tra sao kê ngân hàng và bấm nút **Xác nhận đã thu tiền** → Hóa đơn chuyển trạng thái sang `Đã thanh toán (paid)` tức thì.
- **Chống xác nhận trùng lặp:** Cơ chế bảo vệ Idempotency ngăn chặn việc nhấn xác nhận nhầm nhiều lần cho cùng một hóa đơn.

### 4.3 🏆 Tổ chức và điều hành Giải đấu cờ vua trực tuyến (`/tournaments`)

*Dự kiến ra mắt: Phiên bản v1.5*

- **Tạo giải đấu cờ vua cấp trung tâm:** Thiết lập thể thức Swiss (Hệ Thụy Sĩ), thời gian thi đấu và số vòng đấu.
- **Bắt cặp tự động & Điều hành realtime:** Quản lý danh sách kỳ thủ, theo dõi trực tiếp các ván cờ qua kết nối WebSocket thời gian thực và tự động trao huy chương/cập nhật bảng xếp hạng chung cuộc.

---

*Cần hỗ trợ về hạ tầng máy chủ hoặc cấu hình nâng cao? Vui lòng tham khảo tài liệu kỹ thuật tại thư mục `docs/03-operations/`.*
