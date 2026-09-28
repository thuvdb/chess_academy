# Giai đoạn 1: Phân tích Yêu cầu (Requirements Analysis)

> **CAMS — Chess Academy Management System**
> Tài liệu con của [SDLC.md](./SDLC.md)

---

## 1.1 Bối cảnh & Mục tiêu

**Bài toán:** Các trung tâm dạy cờ vua hiện nay quản lý học sinh, bài tập và học phí thủ công (sổ tay, Excel). Giáo viên mất nhiều thời gian nhập liệu bài toán cờ từ sách giấy. Học sinh không có nền tảng luyện tập tự động tại nhà.

**Mục tiêu dự án:** Xây dựng hệ thống quản lý học viện cờ vua toàn diện (Chess Academy Management System - CAMS):
- Quét bài toán cờ từ PDF/sách bằng AI (Computer Vision)
- Nền tảng luyện tập cờ vua tương tác cho học sinh
- Quản lý lớp học, học phí, tiến độ học viên
- Tổ chức giải đấu online nội bộ
- Ứng dụng mobile cho học sinh và phụ huynh

---

## 1.2 Stakeholders

| Vai trò | Mô tả | Ưu tiên |
|---|---|---|
| Admin Trung tâm | Quản lý toàn bộ hệ thống, tài chính, giáo viên | Cao |
| Giáo viên / HLV | Tạo lớp, giao bài, theo dõi tiến độ, chấm bài | Cao |
| Học sinh | Luyện tập bài toán, tham gia giải đấu | Cao |
| Phụ huynh | Theo dõi tiến độ con, thanh toán học phí | Trung bình |
| Super Admin | Quản lý nhiều trung tâm (v2.5) | Thấp |

---

## 1.3 Yêu cầu Chức năng (Functional Requirements)

### FR-01: Xác thực & Phân quyền
- **FR-01.1:** Đăng ký / Đăng nhập bằng email + password
- **FR-01.2:** Đăng nhập bằng Google OAuth
- **FR-01.3:** Đăng nhập bằng Facebook OAuth *(bổ sung)*
- **FR-01.4:** Phân quyền 4 cấp: Super Admin, Admin, Teacher, Student/Parent
- **FR-01.5:** Reset mật khẩu qua email
- **FR-01.6:** Quản lý phiên đăng nhập (JWT + Refresh Token)

### FR-02: Quản lý Trung tâm & Lớp học
- **FR-02.1:** Admin tạo/sửa/xóa thông tin trung tâm (tên, địa chỉ, logo, số điện thoại, email)
- **FR-02.2:** Admin thêm **Facebook Page URL** của trung tâm *(bổ sung)*
- **FR-02.3:** Admin tạo lớp học, gán giáo viên phụ trách
- **FR-02.4:** Giáo viên thêm/xóa học sinh vào lớp
- **FR-02.5:** Hỗ trợ nhiều cơ sở (branch) trong một trung tâm
- **FR-02.6:** Quản lý lịch học (thời khóa biểu) theo lớp

### FR-03: AI Quét Bài Toán Cờ (Computer Vision)
- **FR-03.1:** Upload file PDF chứa bài toán cờ vua
- **FR-03.2:** Hệ thống tự động tách từng trang PDF thành ảnh (300 DPI)
- **FR-03.3:** Service A — Board Detector: phát hiện vị trí bàn cờ trên trang, trả về bounding box + confidence score
- **FR-03.4:** Service B — Board Rectifier: perspective transform → ảnh bàn cờ chuẩn 640×640px
- **FR-03.5:** Service C — Piece Classifier: cắt 64 ô → classify 13 nhãn → build FEN
- **FR-03.6:** Hiển thị confidence score từng ô, cảnh báo ô có độ tin cậy thấp (< 70%)
- **FR-03.7:** Pipeline validation: FEN Candidate → FEN Validator → Chess Position Validator → Stockfish sanity check → Human Review
- **FR-03.8:** Giáo viên duyệt, chỉnh sửa FEN nếu AI nhận diện sai (human-in-the-loop)
- **FR-03.9:** Giáo viên nhập lời giải dạng PGN hoặc UCI; Stockfish tự gợi ý lời giải tối ưu

### FR-04: Kho Bài Toán (Puzzle Library)
- **FR-04.1:** Phân loại theo độ khó: Beginner / Intermediate / Advanced / Expert
- **FR-04.2:** Tag theo chủ đề: Chiếu hết, Chốt thăng, Phòng thủ, Khai cuộc, Tàn cuộc...
- **FR-04.3:** Tìm kiếm theo tag, độ khó, từ khóa, FEN, nguồn gốc
- **FR-04.4:** Chia sẻ bài toán giữa các giáo viên trong trung tâm
- **FR-04.5:** Import bài toán từ Lichess / Chess.com (PGN)
- **FR-04.6:** 3 cách tạo bài tập: từ PGN / từ FEN / từ bàn cờ thủ công *(bổ sung)*
- **FR-04.7:** Lưu nguồn gốc bài tập: `source_type`, `source_id`, `source_ply` *(bổ sung)*
- **FR-04.8:** Mỗi bài tập hỗ trợ nhiều lời giải (1:N `puzzle_solutions`) *(bổ sung)*

### FR-05: Giao Bài & Luyện Tập
- **FR-05.1:** Giáo viên giao bài tập cho lớp hoặc cá nhân
- **FR-05.2:** Đặt deadline cho bài tập
- **FR-05.3:** Học sinh giải bài trực tiếp trên giao diện bàn cờ tương tác
- **FR-05.4:** Kiểm tra nước đi, báo đúng/sai tức thì
- **FR-05.5:** Gợi ý (hint) có giới hạn số lần
- **FR-05.6:** Xem lại lời giải sau khi hoàn thành
- **FR-05.7:** Hệ thống điểm ELO nội bộ
- **FR-05.8:** Chấm điểm tự động bởi AI (so khớp nước đi) *(bổ sung)*
- **FR-05.9:** Chấm điểm thủ công bởi giáo viên (nhập điểm + nhận xét) *(bổ sung)*
- **FR-05.10:** Học sinh xem kết quả: Robot icon (auto AI) hoặc tên giáo viên + feedback (manual) *(bổ sung)*

### FR-06: Theo dõi Tiến độ & Analytics
- **FR-06.1:** Dashboard giáo viên: số bài hoàn thành, tỉ lệ đúng/sai, danh sách chưa nộp
- **FR-06.2:** Dashboard học sinh: ELO, streak, biểu đồ tiến bộ
- **FR-06.3:** Bảng xếp hạng theo lớp, theo trung tâm
- **FR-06.4:** Báo cáo xuất file Excel/PDF cho phụ huynh
- **FR-06.5:** Phân tích lỗi phổ biến nhất của từng học sinh

### FR-07: Quản lý Học phí & Thanh toán
- **FR-07.1:** Admin cấu hình gói học phí (theo tháng/học kỳ/khóa)
- **FR-07.2:** Gửi thông báo học phí đến phụ huynh qua email/push
- **FR-07.3:** Thanh toán online: VNPay, MoMo, ZaloPay, chuyển khoản ngân hàng/VietQR
- **FR-07.4:** Theo dõi trạng thái: pending / paid / overdue / cancelled
- **FR-07.5:** Xuất hóa đơn PDF
- **FR-07.6:** Báo cáo doanh thu theo tháng, theo lớp
- **FR-07.7:** Nhắc nhở tự động học phí sắp đến hạn
- **FR-07.8:** Admin xác nhận thanh toán chuyển khoản thủ công (Level 1 MVP) *(bổ sung)*

### FR-08: Giải đấu Online (Tournament)
- **FR-08.1:** Admin/Giáo viên tạo giải đấu nội bộ
- **FR-08.2:** Thể thức: Swiss System, Round Robin, Knockout
- **FR-08.3:** Học sinh đăng ký tham gia
- **FR-08.4:** Bắt cặp tự động theo ELO (Swiss/Monrad) hoặc ngẫu nhiên
- **FR-08.5:** Thi đấu online realtime qua WebSocket
- **FR-08.6:** Đồng hồ cờ vua: Blitz / Rapid / Classical
- **FR-08.7:** Bảng kết quả realtime
- **FR-08.8:** Cập nhật ELO sau mỗi ván
- **FR-08.9:** Lưu toàn bộ ván đấu dạng PGN

### FR-09: Thông báo (Notification)
- **FR-09.1:** Push notification mobile (Firebase FCM)
- **FR-09.2:** Email notification (bài tập mới, học phí, giải đấu)
- **FR-09.3:** Thông báo trong app (in-app notification center)

### FR-10: Ứng dụng Mobile
- **FR-10.1:** App iOS và Android (React Native / Expo)
- **FR-10.2:** Học sinh giải bài toán cờ trên mobile
- **FR-10.3:** Phụ huynh xem tiến độ và thanh toán học phí
- **FR-10.4:** Thông báo push realtime
- **FR-10.5:** Thi đấu online trực tiếp trên mobile
- **FR-10.6:** Offline cache bài tập (AsyncStorage)

---

## 1.4 Yêu cầu Phi Chức năng (Non-Functional Requirements)

| Mã | Yêu cầu | Chỉ tiêu |
|---|---|---|
| NFR-01 | Hiệu năng | API response < 500ms (P95), AI scan < 30s/trang |
| NFR-02 | Tính sẵn sàng | Uptime >= 99.5% |
| NFR-03 | Bảo mật | HTTPS, JWT, bcrypt, OWASP Top 10 |
| NFR-04 | Khả năng mở rộng | 500 học sinh đồng thời (v1), 10,000 (v2) |
| NFR-05 | Tương thích | Web: Chrome/Firefox/Safari/Edge; Mobile: iOS 14+, Android 10+ |
| NFR-06 | Dữ liệu | Backup hàng ngày (30d), hàng tuần (12w), hàng tháng (12m = 1 năm) |
| NFR-07 | Tuân thủ | PDPA (Bảo vệ dữ liệu cá nhân Việt Nam) |
| NFR-08 | Thanh toán | Idempotency, signature verification, duplicate callback protection |

---

## 1.5 User Stories (chính)

| ID | Vai trò | Tôi muốn... | Để... |
|---|---|---|---|
| US-01 | Giáo viên | Upload sách cờ PDF | Hệ thống tự tạo bài toán |
| US-02 | Giáo viên | Xem học sinh nào chưa làm bài | Nhắc nhở kịp thời |
| US-03 | Giáo viên | Chấm điểm và gửi nhận xét bài làm | Học sinh biết điểm yếu cần cải thiện |
| US-04 | Học sinh | Giải bài toán cờ mỗi ngày | Cải thiện ELO và kỹ năng |
| US-05 | Học sinh | Xem bảng xếp hạng lớp | Cạnh tranh lành mạnh |
| US-06 | Học sinh | Xem điểm AI chấm và feedback thầy | Rút kinh nghiệm sau mỗi bài |
| US-07 | Phụ huynh | Nhận thông báo học phí | Thanh toán đúng hạn |
| US-08 | Phụ huynh | Xem báo cáo tiến độ con | Biết con đang học ở mức nào |
| US-09 | Admin | Xem báo cáo doanh thu | Quản lý tài chính trung tâm |
| US-10 | Admin | Xác nhận chuyển khoản của phụ huynh | Cập nhật trạng thái hóa đơn |
| US-11 | Học sinh | Tham gia giải đấu online | Thi đấu thực tế với bạn cùng lớp |
