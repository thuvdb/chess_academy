# Cẩm Nang Dành Cho Giáo Viên (Teacher Guide)

> **Hệ thống:** CAMS — Chess Academy Management System  
> **Phiên bản áp dụng:** Core MVP v1.0 (Có lộ trình v1.5)  
> **Dành cho:** Giáo viên giảng dạy, Huấn luyện viên cờ vua tại trung tâm  
> **Ngày cập nhật:** 17/10/2026

---

## Mục Lục

1. [Đăng nhập & Cập nhật hồ sơ cá nhân](#1-đăng-nhập--cập-nhật-hồ-sơ-cá-nhân-profile)
2. [Quản lý lớp học & Xem lịch dạy](#2-quản-lý-lớp-học-classes--xem-lịch-dạy-schedule)
   - 2.1 Xem danh sách lớp học phụ trách
   - 2.2 Xem lịch dạy (Thời khóa biểu tuần)
   - 2.3 Thêm học sinh vào lớp học
   - 2.4 Rút (hủy ghi danh) học sinh khỏi lớp học
3. [Hướng dẫn sử dụng AI Scanner quét sách cờ PDF](#3-hướng-dẫn-sử-dụng-ai-scanner-quét-sách-cờ-pdf-scanner)
   - 3.1 Tiêu chuẩn file PDF đầu vào
   - 3.2 Tải file và theo dõi tiến trình bóc tách
   - 3.3 Đọc và đánh giá kết quả (Độ tin cậy & Cảnh báo < 70%)
   - 3.4 Chỉnh sửa quân cờ & lượt đi trực quan (Human-in-the-loop)
   - 3.5 Phê duyệt đưa vào kho bài hoặc Từ chối ảnh lỗi
4. [Quản lý Kho bài tập cờ vua](#4-quản-lý-kho-bài-tập-cờ-vua-puzzles)
   - 4.1 Tra cứu và lọc bài tập
   - 4.2 Tạo thế cờ thủ công bằng FEN & Kiểm tra lời giải bằng Stockfish
5. [Giao bài tập về nhà & Chấm bài](#5-giao-bài-tập-về-nhà--chấm-bài-assignments)
   - 5.1 Giao bài tập cho lớp học & Cài đặt Deadline, Hint
   - 5.2 Theo dõi tiến độ nộp bài của học sinh
   - 5.3 Chấm điểm & Nhận xét bài tập thủ công
   - 5.4 Mở lại bài tập (Reopen) cho học sinh làm lại
6. [Tính năng đang phát triển (Lộ trình v1.5 & v2.0)](#6-tính-năng-đang-phát-triển-lộ-trình-v15--v20)
   - 6.1 🏆 Tổ chức và điều hành Giải đấu cờ vua trực tuyến (`/tournaments`)

---

## 1. Đăng nhập & Cập nhật hồ sơ cá nhân (`/profile`)

### 1.1 Đăng nhập hệ thống

1. Mở trình duyệt web (Google Chrome, Microsoft Edge hoặc Safari) và truy cập địa chỉ hệ thống CAMS (ví dụ: `https://cams.example.com` hoặc `http://localhost:3000`).
2. Tại màn hình Đăng nhập:
   - **Email:** Nhập địa chỉ email giáo viên do trung tâm cấp (ví dụ: `teacher1@cams.test`).
   - **Mật khẩu:** Nhập mật khẩu được bàn giao.
3. Nhấp nút **Đăng nhập**. Khi thành công, thanh điều hướng (Sidebar) bên trái sẽ hiển thị các mục làm việc dành cho giáo viên và thông tin tài khoản ở góc dưới.

### 1.2 Cập nhật hồ sơ cá nhân

1. Nhấp vào mục **Hồ sơ cá nhân** trên thanh điều hướng bên trái (hoặc nhấp trực tiếp vào tên của bạn ở góc chân Sidebar).
2. Tại trang `/profile`, bạn có thể:
   - Cập nhật **Số điện thoại** liên hệ.
   - Viết phần **Tiểu sử (Bio)** giới thiệu về kinh nghiệm thi đấu, đẳng cấp kiện tướng hoặc phương pháp giảng dạy.
   - Tải lên **Ảnh đại diện (Avatar)** cá nhân để học sinh và phụ huynh dễ nhận diện.
3. Nhấp **Lưu thông tin** để hoàn tất.

---

## 2. Quản lý lớp học (`/classes`) & Xem lịch dạy (`/schedule`)

### 2.1 Xem danh sách lớp học phụ trách

- Nhấp chọn **Lớp học** trên Sidebar.
- Giao diện hiển thị danh sách các lớp bạn được phân công phụ trách. Mỗi thẻ lớp học cung cấp nhanh: Tên lớp, Cấp độ học viên (Cơ bản / Trung cấp / Nâng cao / Thi đấu), Sĩ số hiện tại / Sĩ số tối đa và trạng thái hoạt động.
- Nhấp trực tiếp vào tên lớp để vào trang **Chi tiết lớp học**.

### 2.2 Xem lịch dạy theo tuần

- Nhấp chọn **Lịch học** trên Sidebar.
- Lịch học được hiển thị theo dạng thời khóa biểu tuần từ 07:00 đến 19:00, được đánh dấu bằng các ô màu trực quan:
  - 🟢 **Xanh lá:** Lớp Cơ bản (Beginner)
  - 🔵 **Xanh dương:** Lớp Trung cấp (Intermediate)
  - 🟣 **Tím:** Lớp Nâng cao (Advanced)
  - 🟡 **Vàng cam:** Lớp Thi đấu (Tournament)
- Bạn có thể nhấp vào các nút mũi tên `◀` hoặc `▶` để xem tuần trước/tuần sau, hoặc nhấp **Hôm nay** để quay lại ngày hiện tại.

### 2.3 Thêm học sinh vào lớp học

Khi trung tâm tiếp nhận thêm học viên mới và giao vào lớp của bạn:

1. Vào menu **Lớp học** → nhấp vào lớp cần xếp học sinh.
2. Tại trang chi tiết lớp học, nhấp nút **+ Thêm học sinh**.
3. Một hộp thoại tìm kiếm xuất hiện:
   - Gõ tên hoặc email của học sinh (ví dụ: `Phạm Minh Học` hoặc `student1@cams.test`).
   - Hệ thống hiển thị kết quả tìm kiếm theo thời gian thực.
4. Nhấp nút **Thêm** bên cạnh tên học sinh cần chọn.
5. Học sinh sẽ lập tức xuất hiện trong danh sách học viên của lớp, sĩ số tự động tăng tương ứng.

> **Lưu ý quan trọng về sĩ số tối đa:**  
> Nếu lớp học đã đạt sĩ số tối đa (ví dụ `15/15`), hệ thống sẽ cảnh báo: *"Lớp học đã đạt sĩ số tối đa, không thể ghi danh thêm"*. Trong trường hợp này, giáo viên cần liên hệ Quản trị viên để nâng hạn mức sĩ số lớp.

### 2.4 Rút (hủy ghi danh) học sinh khỏi lớp

Khi học sinh chuyển lớp hoặc nghỉ học:

1. Trong trang chi tiết lớp học, tìm học sinh cần chuyển trong bảng danh sách.
2. Nhấp vào biểu tượng **Thùng rác / Xóa** (🗑️) ở cột Thao tác.
3. Hộp thoại xác nhận hiện ra: *"Bạn có chắc chắn muốn rút học sinh này khỏi lớp?"* → Nhấp **Đồng ý**.
4. Học sinh sẽ được rút khỏi lớp học, sĩ số lớp giảm tương ứng.
5. *An toàn dữ liệu:* Thao tác này chỉ hủy liên kết giữa học sinh và lớp học, tài khoản và lịch sử bài tập của học sinh vẫn được bảo toàn trong hệ thống.

---

## 3. Hướng dẫn sử dụng AI Scanner quét sách cờ PDF (`/scanner`)

**Quét AI bàn cờ (AI Scanner)** là công cụ đắc lực giúp giáo viên số hóa hàng loạt bài tập từ sách giáo trình PDF thành dạng tương tác chỉ trong vài phút.

### 3.1 Tiêu chuẩn file PDF đầu vào

Để AI nhận diện với độ chính xác cao nhất:
- **Định dạng:** Bắt buộc là file `.pdf` hợp lệ (hệ thống kiểm tra chữ ký Magic Bytes `%PDF-`). Không đổi đuôi file `.png`, `.docx` thành `.pdf`.
- **Dung lượng:** Tối đa **50MB** cho mỗi file tải lên.
- **Chất lượng ảnh scan:** Nên đạt độ phân giải tối thiểu **300 DPI**. Bàn cờ in phẳng, không bị quăn góc, ánh sáng đồng đều và không bị vẹo phối cảnh quá mức.

### 3.2 Tải file và theo dõi tiến trình bóc tách

1. Nhấp chọn mục **Quét AI bàn cờ** trên Sidebar.
2. Nhấp nút **Upload PDF** (hoặc kéo thả file PDF vào khung tải lên).
3. Sau khi chọn file, hệ thống sẽ tự động tạo một tác vụ quét (**Scan Job**) tại cột bên trái với trạng thái chuyển dần:
   - 🟡 `pending`: Tác vụ đang xếp hàng chờ.
   - 🔵 `processing`: AI đang phân tích từng trang, tìm bàn cờ và phân loại quân cờ.
   - 🟢 `completed`: Bóc tách hoàn tất, sẵn sàng xem xét.
4. Thời gian xử lý trung bình dưới 30 giây cho mỗi trang tài liệu.

### 3.3 Đọc và đánh giá kết quả bóc tách

Khi tác vụ chuyển sang `completed`, nhấp vào file để xem danh sách các bàn cờ được bóc tách:
- **Ảnh bàn cờ gốc:** Ảnh trích xuất thực tế từ tài liệu PDF.
- **Bàn cờ số hóa đối chiếu:** Dựng lại dựa trên kết quả nhận diện của AI.
- **Điểm tin cậy (Confidence Score):**
  - **Tự động duyệt (`auto_approved`):** Các bàn cờ mà tất cả 64 ô đều đạt độ tin cậy ≥ 95% và không có xung đột luật cờ sẽ được hệ thống tự động gắn nhãn đạt chuẩn.
  - **Cảnh báo độ tin cậy thấp (< 70%):** Các ô cờ mà AI chưa chắc chắn sẽ được tô viền màu vàng/cam kèm biểu tượng cảnh báo `⚠️`. Giáo viên cần đặc biệt lưu ý kiểm tra các ô này.

### 3.4 Chỉnh sửa quân cờ & lượt đi trực quan (Human-in-the-loop)

Nếu phát hiện AI nhận diện sai (ví dụ: quân Mã đen bị nhận nhầm thành Tốt đen):

1. Nhấp trực tiếp vào ô cờ bị nhận diện sai trên bàn cờ đồ họa.
2. Bảng chọn quân cờ xuất hiện → Nhấp chọn đúng quân cờ (ví dụ: `Mã Đen ♞`).
3. Chọn quyền đi tiếp theo: **Trắng đi trước (w)** hoặc **Đen đi trước (b)**.
4. Nhấp nút **Lưu FEN đã sửa**.
5. Bàn cờ cập nhật ngay lập tức và trạng thái kết quả chuyển thành `corrected` (Đã chỉnh sửa).

### 3.5 Phê duyệt đưa vào kho bài hoặc Từ chối ảnh lỗi

- **Phê duyệt bàn cờ chuẩn:** Nhấp nút **Phê duyệt (Approve)**. Hệ thống sẽ tự động kích hoạt động cơ Stockfish kiểm tra nước đi tối ưu, sinh cây biến thể và chuyển thẳng thế cờ vào **Kho bài tập cờ** (`/puzzles`).
- **Lưu hàng loạt:** Bạn có thể bấm nút **Lưu tất cả vào Puzzle Bank** để chuyển toàn bộ các thế cờ đã duyệt trong phiên quét vào kho bài.
- **Từ chối bàn cờ lỗi:** Với các ảnh chụp bị nhầm hình minh họa, hình vẽ trang trí hoặc quá mờ không thể nhận dạng, nhấp nút **Từ chối (Reject)** để loại bỏ, tránh gây rác dữ liệu.

---

## 4. Quản lý Kho bài tập cờ vua (`/puzzles`)

### 4.1 Tra cứu và lọc bài tập

1. Nhấp chọn **Kho bài tập cờ** trên Sidebar.
2. Thư viện hiển thị toàn bộ bài tập chiến thuật đã được số hóa kèm hình thu nhỏ bàn cờ, mã FEN, cấp độ và chủ đề.
3. Sử dụng thanh công cụ để tìm kiếm:
   - Tìm theo từ khóa tiêu đề hoặc tên sách nguồn.
   - Lọc theo **Cấp độ:** Dễ / Trung bình / Khó / Chuyên gia.
   - Lọc theo **Chủ đề:** Chiếu hết (Checkmate), Ghim quân (Pin), Xiên (Skewer), Tấn công đôi (Fork), Tàn cuộc chốt...

### 4.2 Tạo thế cờ thủ công bằng FEN & Kiểm tra lời giải Stockfish

Ngoài việc quét bằng AI Scanner, giáo viên có thể chủ động tạo bài tập từ chuỗi FEN:

1. Trong trang Kho bài tập cờ, nhấp nút **+ Tạo mới**.
2. Nhập thông tin:
   - **Tiêu đề:** Đặt tên bài tập (ví dụ: *Thế cờ chiếu hết 1 nước - Tàn cuộc xe*).
   - **Chuỗi FEN:** Dán chuỗi FEN hợp lệ (ví dụ: `r1bqkb1r/pppp1ppp/2n2n2/4p3/2B1P3/5N2/PPPP1PPP/RNBQK2R w KQkq - 0 1`).
   - **Lời giải (UCI hoặc SAN):** Nhập nước đi đúng (ví dụ: `Bxf7#` hoặc `c4f7`).
   - **Cấp độ & Chủ đề:** Chọn mức tương ứng cho học sinh.
3. Nhấp nút **Xác thực Stockfish**:
   - Động cơ Stockfish sẽ tự động tính toán nước đi. Nếu nước đi hợp lệ và đạt điều kiện chiến thuật, hệ thống sẽ đánh dấu `solution_verified = true` và sinh cây biến thể lời giải.
4. Nhấp **Tạo bài toán** để hoàn tất lưu trữ.

---

## 5. Giao bài tập về nhà & Chấm bài (`/assignments`)

### 5.1 Giao bài tập cho lớp học

1. Nhấp chọn **Bài tập về nhà** trên Sidebar → Nhấp nút **+ Giao bài tập**.
2. Điền thông tin phiếu giao bài:
   - **Lớp nhận bài:** Chọn lớp học bạn đang phụ trách.
   - **Chọn bài tập:** Chọn một hoặc nhiều thế cờ từ Kho bài tập cờ.
   - **Hạn nộp (Deadline):** Thiết lập ngày và giờ cụ thể (ví dụ: 23:59 Chủ Nhật).
   - **Số lượt gợi ý tối đa (Hint Limit):** Thiết lập số lần học sinh được bấm xem gợi ý (mặc định: 2 lần).
3. Nhấp **Xác nhận giao bài**. Tất cả học sinh trong lớp sẽ nhìn thấy bài tập trong tài khoản của mình.

### 5.2 Theo dõi tiến độ nộp bài

- Trong danh sách bài tập, nhấp vào bài tập đã giao để xem chi tiết (`/assignments/:id`).
- Bảng danh sách bài nộp hiển thị rõ ràng:
  - Tên học sinh.
  - Trạng thái: `Chưa làm`, `Đang làm`, `Đã nộp`, hoặc `Đã chấm`.
  - Số lượt thử (Attempts) và số lần đã dùng gợi ý (Hints used).
  - Điểm số và thời gian nộp bài.

### 5.3 Chấm điểm & Nhận xét thủ công

Mặc dù hệ thống có cơ chế tự động chấm điểm qua AI, giáo viên luôn có quyền chấm điểm và gửi lời khuyên sư phạm:

1. Tại dòng bài làm của học sinh có trạng thái `Đã nộp`, nhấp **Chấm điểm & Nhận xét**.
2. Nhập:
   - **Điểm số:** Theo thang điểm 100 (ví dụ: `90/100`).
   - **Nhận xét chuyên môn:** Viết phản hồi cụ thể (ví dụ: *"Nước đi rất chuẩn xác và quyết đoán! Chú ý quan sát thêm thời gian suy nghĩ nhé."*).
3. Nhấp **Lưu kết quả**.
4. Phía học sinh khi xem lại bài tập sẽ nhìn thấy huy hiệu chấm thủ công kèm lời nhắn trực tiếp từ giáo viên.

### 5.4 Mở lại bài tập (Reopen) cho học sinh làm lại

Trong trường hợp học sinh nộp nhầm, chưa đạt yêu cầu hoặc giáo viên muốn học sinh rèn luyện lại:

1. Tại bài làm của học sinh đó, nhấp nút **Mở lại bài tập (Reopen)**.
2. Nhập lý do yêu cầu làm lại (ví dụ: *"Em hãy xem lại nước đi ở nước thứ 2 khi đối phương đổi quân"*).
3. Nhấp **Xác nhận**.
4. Trạng thái bài tập phía học sinh sẽ chuyển sang `reopened` (Đã mở lại) và học sinh được quyền thực hiện giải lại từ đầu. Số phiên bản bài làm sẽ tự động tăng lên để giáo viên đối chiếu sự tiến bộ.

---

## 6. Tính năng đang phát triển (Lộ trình v1.5 & v2.0)

> 🔔 **Thông báo:** Các tính năng dưới đây đang được đội ngũ kỹ thuật hoàn thiện và sẽ chính thức phát hành trong phiên bản **v1.5 / v2.0**.

### 6.1 🏆 Tổ chức và điều hành Giải đấu cờ vua trực tuyến (`/tournaments`)

*Dự kiến ra mắt: Phiên bản v1.5*

- **Tạo giải đấu nội bộ:** Giáo viên có thể tự khởi tạo giải đấu cho trung tâm hoặc liên lớp theo thể thức **Hệ Thụy Sĩ (Swiss System)** hoặc **Vòng tròn (Round Robin)**.
- **Tùy chỉnh thời gian thi đấu:** Hỗ trợ Blitz (Chớp 5+3), Rapid (Nhanh 10+5) hoặc Tiêu chuẩn.
- **Bắt cặp tự động:** Hệ thống tự động xếp cặp thi đấu từng vòng theo điểm số và hệ số Buchholz.
- **Giám sát ván đấu Realtime:** Theo dõi trực tiếp bàn cờ thi đấu của các kỳ thủ qua WebSocket thời gian thực, can thiệp xử hòa hoặc xử thua khi có vi phạm điều lệ.
- **Bảng xếp hạng giải đấu tự động:** Tự động tính điểm (Thắng 1, Hòa 0.5, Thua 0) và xếp hạng chung cuộc khi đóng giải.

---

*Cần thêm hỗ trợ kỹ thuật? Vui lòng liên hệ Quản trị viên Trung tâm hoặc gửi yêu cầu hỗ trợ nội bộ.*
