# Hướng Dẫn Sử Dụng Tính Năng Quét AI Bàn Cờ (AI Scanner)

> **Hệ thống:** CAMS — Chess Academy Management System  
> **Phiên bản:** 1.0 (Core MVP)  
> **Đối tượng:** Quản trị viên (Admin), Giáo viên (Teacher)  
> **Đường dẫn:** `/scanner`  
> **Ngày cập nhật:** 17/10/2026

---

## Mục Lục

1. [Giới thiệu tính năng](#1-giới-thiệu-tính-năng)
2. [Yêu cầu file PDF đầu vào](#2-yêu-cầu-file-pdf-đầu-vào)
3. [Bước 1 — Tải lên file PDF](#3-bước-1--tải-lên-file-pdf)
4. [Bước 2 — Theo dõi tiến trình quét](#4-bước-2--theo-dõi-tiến-trình-quét)
5. [Bước 3 — Xem xét kết quả bóc tách](#5-bước-3--xem-xét-kết-quả-bóc-tách)
6. [Bước 4 — Chỉnh sửa FEN (Sửa lỗi AI)](#6-bước-4--chỉnh-sửa-fen-sửa-lỗi-ai)
7. [Bước 5 — Phê duyệt & Chuyển vào Kho bài tập cờ](#7-bước-5--phê-duyệt--chuyển-vào-kho-bài-tập-cờ)
8. [Bước 6 — Từ chối kết quả lỗi](#8-bước-6--từ-chối-kết-quả-lỗi)
9. [Lưu hàng loạt các thế cờ đã duyệt](#9-lưu-hàng-loạt-các-thế-cờ-đã-duyệt)
10. [Quản lý tác vụ quét (Scan Jobs)](#10-quản-lý-tác-vụ-quét-scan-jobs)
11. [Hiểu về độ tin cậy (Confidence Score)](#11-hiểu-về-độ-tin-cậy-confidence-score)
12. [Quy trình kỹ thuật phía sau (Tham khảo)](#12-quy-trình-kỹ-thuật-phía-sau-tham-khảo)
13. [Xử lý sự cố thường gặp](#13-xử-lý-sự-cố-thường-gặp)

---

## 1. Giới thiệu tính năng

**Quét AI bàn cờ** là tính năng đặc biệt của hệ thống CAMS, cho phép giáo viên tải lên sách cờ vua dạng PDF và sử dụng trí tuệ nhân tạo (AI) để tự động:

- **Phát hiện** vị trí các bàn cờ trên mỗi trang PDF.
- **Bóc tách** từng bàn cờ thành hình ảnh riêng biệt.
- **Nhận diện** từng quân cờ trên 64 ô và tạo ra chuỗi FEN (Forsyth-Edwards Notation) — ký hiệu chuẩn quốc tế mô tả thế cờ.
- **Đưa vào kho bài tập** sau khi giáo viên xem xét và phê duyệt.

Quy trình này giúp giáo viên tiết kiệm hàng giờ so với việc nhập thủ công từng thế cờ từ sách giấy.

> ⚠️ **Quyền truy cập:** Chỉ tài khoản có vai trò **Super Admin**, **Center Admin** hoặc **Giáo viên** mới có thể truy cập tính năng này. Học sinh và Phụ huynh bị chặn truy cập.

---

## 2. Yêu cầu file PDF đầu vào

Để AI nhận diện chính xác nhất, file PDF cần đáp ứng các tiêu chuẩn sau:

| Tiêu chuẩn | Yêu cầu |
| :--- | :--- |
| **Định dạng file** | PDF hợp lệ (Magic Bytes bắt đầu bằng `%PDF-`). File `.docx`, `.png`, `.jpg` hoặc file text đổi đuôi thành `.pdf` sẽ bị từ chối. |
| **Dung lượng tối đa** | 50 MB |
| **Chất lượng ảnh** | Tối thiểu 300 DPI. Ảnh mờ, nghiêng hoặc chụp từ xa sẽ giảm độ chính xác. |
| **Bàn cờ** | Bàn cờ in rõ nét trên trang sách, có đường viền phân biệt 64 ô. Bàn cờ đồ họa (diagram) cho kết quả tốt hơn ảnh chụp thực tế. |

> 💡 **Mẹo:** Sử dụng file PDF từ sách cờ vua điện tử (eBook) cho chất lượng tốt nhất. Nếu scan từ sách giấy, hãy dùng máy scan phẳng ở độ phân giải 300 DPI trở lên.

---

## 3. Bước 1 — Tải lên file PDF

1. Nhấp vào **Quét AI bàn cờ** trên thanh điều hướng.
2. Tại trang Scanner, nhấp nút **Upload PDF** (hoặc kéo thả file PDF vào vùng upload).
3. Chọn file PDF từ máy tính.
4. Hệ thống bắt đầu tải file lên và tự động khởi tạo tác vụ quét.

**Các trường hợp bị từ chối:**
- ❌ File không phải định dạng PDF → Thông báo: *"Định dạng không được hỗ trợ. Chỉ chấp nhận file định dạng .PDF hợp lệ"*
- ❌ File vượt quá 50MB → Thông báo: *"Dung lượng file vượt quá giới hạn 50MB"*

---

## 4. Bước 2 — Theo dõi tiến trình quét

Sau khi tải lên thành công:

1. Tác vụ quét xuất hiện trong danh sách **Scan Jobs** ở cột bên trái.
2. Trạng thái tác vụ chuyển qua các giai đoạn:

| Trạng thái | Ý nghĩa |
| :--- | :--- |
| 🟡 **pending** | Tác vụ đang chờ xử lý trong hàng đợi |
| 🔵 **processing** | AI đang quét và bóc tách bàn cờ từ PDF |
| 🟢 **completed** | Quét hoàn tất, kết quả sẵn sàng xem xét |
| 🔴 **failed** | Quét thất bại (xem thông báo lỗi) |

3. Nhấp vào tác vụ quét để xem kết quả khi trạng thái chuyển sang **completed**.

> ⏱️ **Thời gian xử lý:** Trung bình dưới 30 giây/trang PDF. File 10 trang thường hoàn thành trong 3–5 phút.

---

## 5. Bước 3 — Xem xét kết quả bóc tách

Sau khi tác vụ quét hoàn tất, nhấp vào tên file trong danh sách Scan Jobs:

### 5.1 Giao diện kết quả

Phần bên phải hiển thị danh sách các bàn cờ đã bóc tách, mỗi kết quả gồm:

- **Ảnh bàn cờ trích xuất:** Ảnh gốc cắt từ PDF
- **Bàn cờ đồ họa số hóa:** Bàn cờ tương tác dựng lại từ FEN mà AI tạo ra
- **Chuỗi FEN:** Ký hiệu chuẩn mô tả thế cờ
- **Điểm tin cậy (Confidence):** Phần trăm độ tin cậy của AI
- **Trạng thái duyệt:** Chờ duyệt (pending) / Đã duyệt (approved) / Đã sửa (corrected) / Đã từ chối (rejected) / Tự động duyệt (auto_approved)

### 5.2 Trạng thái tự động duyệt (Auto Approved)

Nếu **tất cả 64 ô** trên bàn cờ đều có độ tin cậy ≥ 95% và không có xung đột với luật cờ, hệ thống tự động gán trạng thái **auto_approved** — giáo viên không cần phê duyệt thủ công cho trường hợp này.

### 5.3 Cảnh báo độ tin cậy thấp

Các ô có độ tin cậy **dưới 70%** sẽ được đánh dấu viền vàng/cam kèm biểu tượng ⚠️ cảnh báo. Giáo viên cần kiểm tra kỹ các ô này vì AI có thể nhận diện sai.

---

## 6. Bước 4 — Chỉnh sửa FEN (Sửa lỗi AI)

Khi AI nhận diện sai (ví dụ: nhầm quân Mã đen thành Tốt đen):

### 6.1 Sửa FEN trực tiếp

1. Tại kết quả cần sửa, quan sát bàn cờ đồ họa và so sánh với ảnh gốc từ PDF.
2. Nếu phát hiện sai lệch, nhấp vào khu vực chỉnh sửa FEN.
3. Sửa chuỗi FEN trực tiếp hoặc sử dụng giao diện bàn cờ tương tác để:
   - Chọn lại đúng quân cờ cho ô bị nhận sai.
   - Chọn **Bên đi tiếp:** Trắng (w) hoặc Đen (b).
4. Nhấp **Lưu FEN đã sửa**.
5. Bàn cờ đồ họa cập nhật tức thì theo FEN mới.
6. Trạng thái chuyển thành **corrected** (Đã chỉnh sửa).

### 6.2 Mẹo chỉnh sửa FEN

- **So sánh song song:** Đặt ảnh gốc và bàn cờ đồ họa cạnh nhau, kiểm tra từng hàng từ hàng 8 (phía Đen) xuống hàng 1 (phía Trắng).
- **Chú ý các quân hay bị nhầm lẫn:**
  - Mã (Knight ♞) ↔ Tượng (Bishop ♝) — hình dáng gần giống trên một số bộ quân.
  - Hậu (Queen ♛) ↔ Vua (King ♚) — trên bàn cờ nhỏ có thể khó phân biệt.
  - Ô trống ↔ Tốt (Pawn ♟) — trên ảnh mờ, bóng đổ có thể tạo nhầm.

---

## 7. Bước 5 — Phê duyệt & Chuyển vào Kho bài tập cờ

Sau khi xác nhận thế cờ chính xác:

1. Nhấp nút **Phê duyệt** (✅) trên kết quả.
2. Hệ thống thực hiện:
   - Ghi nhận trạng thái bàn cờ là **approved**.
   - Tự động kích hoạt **Stockfish** kiểm tra nước đi tối ưu và sinh lời giải.
   - Tạo bài tập mới trong **Kho bài tập cờ** (`/puzzles`).
3. Thông báo: *"Đã duyệt và tạo bài tập vào Thư viện Puzzle Bank!"*.

> 💡 Bài tập sau khi được phê duyệt sẽ sẵn sàng để giáo viên giao cho học sinh qua trang **Bài tập về nhà**.

---

## 8. Bước 6 — Từ chối kết quả lỗi

Với những vùng bị AI nhận nhầm (ảnh minh họa, biểu đồ, bàn cờ quá mờ hoặc bị cắt lệch):

1. Nhấp nút **Từ chối** (❌) trên kết quả.
2. Bàn cờ được đánh dấu trạng thái **rejected**.
3. Kết quả bị từ chối sẽ **không** sinh bài tập vào kho — tránh tạo bài tập rác.

---

## 9. Lưu hàng loạt các thế cờ đã duyệt

Nếu bạn đã phê duyệt nhiều thế cờ trong một tác vụ quét:

1. Nhấp nút **Lưu vào Puzzle Bank** (nút tổng hợp) tại phần đầu danh sách kết quả.
2. Hệ thống đồng thời chuyển tất cả các thế cờ đã duyệt (chưa có puzzle_id) vào Kho bài tập cờ.
3. Thông báo: *"Đã lưu thành công X bài tập vào Puzzle Bank!"*.

---

## 10. Quản lý tác vụ quét (Scan Jobs)

### 10.1 Danh sách tác vụ

Cột bên trái hiển thị toàn bộ tác vụ quét đã thực hiện, bao gồm:
- Tên file PDF
- Trạng thái (pending / processing / completed / failed)
- Số bàn cờ tìm thấy / Số bàn cờ đã duyệt
- Thời gian tải lên

### 10.2 Làm mới danh sách

Nhấp nút **Refresh** để cập nhật trạng thái mới nhất (đặc biệt khi tác vụ đang processing).

### 10.3 Xóa tác vụ quét

Nhấp biểu tượng **🗑️ Xóa** trên tác vụ quét để xóa toàn bộ tác vụ và kết quả liên quan.

> ⚠️ **Lưu ý:** Xóa tác vụ quét không ảnh hưởng đến các bài tập đã được phê duyệt và lưu vào Kho bài tập cờ.

---

## 11. Hiểu về độ tin cậy (Confidence Score)

AI Scanner cung cấp hai loại điểm tin cậy:

### 11.1 Điểm tin cậy bàn cờ (Board Confidence)

Đánh giá tổng thể mức độ chắc chắn rằng vùng ảnh phát hiện **thực sự là một bàn cờ** (không phải biểu đồ, hình minh họa, hoặc bảng biểu khác).

### 11.2 Điểm tin cậy từng ô (Cell Confidence)

Đánh giá mức độ chắc chắn cho **từng ô trong 64 ô**, bao gồm:
- Quân cờ được nhận diện là gì (Vua, Hậu, Xe, Tượng, Mã, Tốt, hoặc ô trống).
- Phần trăm tin cậy.

| Mức tin cậy | Màu sắc | Hành động khuyến nghị |
| :--- | :--- | :--- |
| ≥ 95% | 🟢 Xanh | An toàn, thường không cần sửa |
| 70% – 94% | 🟡 Vàng | Nên kiểm tra, có khả năng đúng nhưng cần xác nhận |
| < 70% | 🔴 Đỏ/Cam | **Bắt buộc kiểm tra** — AI có thể nhận sai |

---

## 12. Quy trình kỹ thuật phía sau (Tham khảo)

> ℹ️ Phần này dành cho bạn đọc muốn hiểu cách AI Scanner hoạt động bên trong. **Không cần đọc phần này** để sử dụng tính năng.

Quy trình AI Scanner gồm 3 bước chính chạy nền (Celery Worker):

```
PDF Upload
    │
    ▼
┌──────────────────────────────────────────────┐
│ Service A — Board Detector (YOLOv8)          │
│ Phát hiện vị trí bàn cờ trên mỗi trang PDF  │
│ Trả về: Bounding Box + Confidence Score      │
└──────────────────────┬───────────────────────┘
                       │
                       ▼
┌──────────────────────────────────────────────┐
│ Service B — Board Rectifier (OpenCV)         │
│ Cắt & nắn thẳng bàn cờ → ảnh chuẩn 640×640 │
│ Xử lý: Perspective Transform, Denoise       │
└──────────────────────┬───────────────────────┘
                       │
                       ▼
┌──────────────────────────────────────────────┐
│ Service C — Piece Classifier (CNN/YOLOv8)    │
│ Chia 64 ô → Nhận diện 13 nhãn quân cờ       │
│ Trả về: FEN Candidate + Cell Confidences     │
└──────────────────────┬───────────────────────┘
                       │
                       ▼
┌──────────────────────────────────────────────┐
│ FEN Validator + Chess Position Validator      │
│ Kiểm tra FEN hợp lệ theo luật cờ            │
│ Stockfish Sanity Check → auto_approve nếu OK │
└──────────────────────┬───────────────────────┘
                       │
                       ▼
           Giáo viên xem xét & duyệt
                       │
                       ▼
              Kho bài tập cờ (/puzzles)
```

---

## 13. Xử lý sự cố thường gặp

### 13.1 File PDF tải lên bị từ chối

| Triệu chứng | Nguyên nhân | Cách khắc phục |
| :--- | :--- | :--- |
| *"Định dạng không được hỗ trợ"* | File không phải PDF thật (đuôi .docx, .png, hoặc file text đổi đuôi) | Đảm bảo file là PDF gốc, không đổi đuôi file |
| *"Dung lượng vượt quá giới hạn"* | File > 50MB | Chia nhỏ file PDF thành nhiều phần, mỗi phần < 50MB |

### 13.2 Kết quả quét không chính xác

| Triệu chứng | Nguyên nhân | Cách khắc phục |
| :--- | :--- | :--- |
| Bàn cờ không được phát hiện | Ảnh quá mờ, bàn cờ quá nhỏ trên trang, hoặc bàn cờ bị viền trang che mất | Scan lại sách với độ phân giải cao hơn (≥ 300 DPI), đảm bảo bàn cờ chiếm ≥ 20% diện tích trang |
| AI nhận nhầm hình minh họa thành bàn cờ | Hình vẽ có dạng lưới ô vuông giống bàn cờ | Từ chối (Reject) kết quả sai |
| Quân cờ bị nhận diện sai | Bộ quân cờ trong sách khác biệt, ảnh bị mờ, bóng đổ | Sửa FEN thủ công theo hướng dẫn Bước 4 |
| FEN tạo ra vi phạm luật cờ | AI nhận sai số lượng Vua hoặc vị trí quân | Sửa FEN thủ công, hệ thống tự kiểm tra lại sau khi sửa |

### 13.3 Tác vụ quét bị trạng thái "failed"

| Nguyên nhân có thể | Cách khắc phục |
| :--- | :--- |
| File PDF bị hỏng (corrupted) | Tải lại file từ nguồn gốc, thử mở bằng trình đọc PDF trước |
| Hệ thống AI Worker quá tải | Đợi vài phút rồi thử tải lên lại. Nếu vẫn lỗi, liên hệ quản trị viên hệ thống |
| File PDF không chứa ảnh (chỉ có text) | AI Scanner cần ảnh bàn cờ trong PDF. File PDF chỉ chứa text thuần không có ảnh sẽ không tìm thấy bàn cờ |

---

## Tóm tắt quy trình sử dụng

```
                         ┌─────────────┐
                         │ Tải lên PDF │
                         └──────┬──────┘
                                │
                         ┌──────▼──────┐
                         │  AI Quét &  │
                         │  Bóc tách   │
                         └──────┬──────┘
                                │
                    ┌───────────┼───────────┐
                    │           │           │
             ┌──────▼──────┐   │    ┌──────▼──────┐
             │ Tin cậy cao │   │    │ Tin cậy thấp│
             │ auto_approve│   │    │ Cần kiểm tra│
             └──────┬──────┘   │    └──────┬──────┘
                    │          │           │
                    │   ┌──────▼──────┐    │
                    │   │  Sửa FEN?   │◄───┘
                    │   └──────┬──────┘
                    │          │
                    │   ┌──────▼──────┐
                    │   │ Phê duyệt / │
                    │   │  Từ chối    │
                    │   └──────┬──────┘
                    │          │
                    └────┬─────┘
                         │
                  ┌──────▼──────┐
                  │ Kho bài tập │
                  │ cờ (/puzzles)│
                  └─────────────┘
```

---

> *Tài liệu này là một phần của bộ Hướng dẫn sử dụng CAMS. Xem thêm:*
> - [Hướng dẫn dành cho Quản trị viên & Giáo viên](./01_huong-dan-quan-tri-giao-vien.md)
> - [Hướng dẫn dành cho Học sinh & Phụ huynh](./02_huong-dan-hoc-sinh-phu-huynh.md)
