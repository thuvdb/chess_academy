# HƯỚNG DẪN TÍNH NĂNG CHESS AI TUTOR — GIAI ĐOẠN 1 (CAMS-AI-01)

> **Mã công việc:** CAMS-AI-01 (Commits CAMS-0040 đến CAMS-0044)  
> **Phiên bản:** CAMS 1.0.0  
> **Chức năng:** Trợ lý Huấn luyện viên Cờ vua AI (Hỏi đáp lý thuyết, khai cuộc, chiến thuật, luật FIDE và bàn cờ minh họa tương tác).

---

## 1. TỔNG QUAN KIẾN TRÚC

Tính năng **Chess AI Tutor** được thiết kế phục vụ học viên cờ vua CAMS với nguyên tắc:
1. **Không chạy model AI cục bộ trên VPS:** Tối ưu tài nguyên VPS (Oracle Cloud Free Tier), toàn bộ cuộc gọi LLM được thực hiện qua API Google Gemini với SDK hiện đại `google-genai`.
2. **Bàn cờ minh họa FIDE hợp lệ 100%:**
   - LLM không tự viết chuỗi FEN (tránh sai sót).
   - LLM chỉ sinh mảng nước đi SAN chuẩn trong thẻ `<board>{"moves":["e4","e5",...],"caption":"..."}</board>`.
   - Backend dùng thư viện `python-chess` mô phỏng từng nước đi. Nếu có nước sai luật, backend tự động loại bỏ thẻ bàn cờ (không làm sập hệ thống và không hiển thị bàn cờ sai). Nếu hợp lệ, sinh đầy đủ danh sách FEN cho từng bước đi.
3. **Stream Server-Sent Events (SSE):** Text được stream theo thời gian thực về giao diện người dùng kèm sự kiện `board` riêng biệt.
4. **Bảo mật & Giới hạn:**
   - Rate limiting qua Redis (số câu hỏi/phút và số câu hỏi/ngày).
   - Cache câu hỏi lặp lại trên Redis (chuẩn hóa câu hỏi, giảm chi phí token LLM).
   - Prompt bảo vệ nghiêm ngặt: đóng vai Huấn luyện viên CAMS, từ chối câu hỏi ngoài cờ vua, chống rò rỉ prompt hay jailbreak.

---

## 2. DANH SÁCH BIẾN MÔI TRƯỜNG MỚI

Các biến sau đã được bổ sung vào hệ thống cấu hình `Settings` (`backend/app/core/config.py`) và file mẫu [`.env.example`](../.env.example):

| Tên biến | Kiểu dữ liệu | Mặc định | Ý nghĩa & Mô tả |
| :--- | :--- | :--- | :--- |
| `GEMINI_API_KEY` | `string` | `""` | Khóa API Google Gemini. Không hard-code, chỉ lấy từ biến môi trường. |
| `GEMINI_MODEL` | `string` | `gemini-2.5-flash` | Tên model Gemini sử dụng cho trợ lý AI. |
| `AI_TUTOR_PROVIDER` | `string` | `gemini` | Nhà cung cấp AI: `gemini` (mặc định) hoặc `mock` (dùng khi test offline/cục bộ). |
| `AI_TUTOR_RATE_LIMIT_PER_MINUTE` | `integer` | `10` | Giới hạn số câu hỏi tối đa của một user trong 1 phút. |
| `AI_TUTOR_RATE_LIMIT_PER_DAY` | `integer` | `100` | Giới hạn số câu hỏi tối đa của một user trong 1 ngày. |
| `AI_TUTOR_CACHE_TTL` | `integer` | `3600` | Thời gian lưu cache câu hỏi lặp lại trên Redis (giây). |
| `AI_TUTOR_HISTORY_LIMIT` | `integer` | `10` | Số lượng tin nhắn gần nhất được gửi kèm ngữ cảnh cho AI. |
| `AI_TUTOR_MAX_TOKENS` | `integer` | `1500` | Số lượng token tối đa cho mỗi phản hồi từ AI. |

---

## 3. CƠ SỞ DỮ LIỆU & BẢNG MỚI (ALEMBIC)

Migration: `backend/alembic/versions/250e12494669_add_ai_tutor_chat_sessions_and_messages.py`

### 3.1. Bảng `chat_sessions`
Lưu trữ các phiên hội thoại của người dùng:
- `id` (UUID, Primary Key)
- `user_id` (UUID, Foreign Key referencing `users.id`, ON DELETE CASCADE)
- `title` (VARCHAR(255), Tiêu đề cuộc trò chuyện)
- `created_at` (TIMESTAMP WITH TIME ZONE, NOW())

### 3.2. Bảng `chat_messages`
Lưu trữ chi tiết từng tin nhắn trong phiên:
- `id` (UUID, Primary Key)
- `session_id` (UUID, Foreign Key referencing `chat_sessions.id`, ON DELETE CASCADE)
- `role` (VARCHAR(20), `user` hoặc `assistant`)
- `content` (TEXT, Nội dung văn bản markdown)
- `board_data` (JSONB nullable, Chứa chuỗi FEN và các nước đi đã validate)
- `created_at` (TIMESTAMP WITH TIME ZONE, NOW())

---

## 4. DANH SÁCH API ENDPOINTS

Tất cả các endpoint đều yêu cầu xác thực Bearer Token (`get_current_user`):

| Phương thức | Đường dẫn | Chức năng | Định dạng phản hồi |
| :--- | :--- | :--- | :--- |
| `GET` | `/api/ai-tutor/sessions` | Lấy danh sách phiên chat của user | JSON array |
| `GET` | `/api/ai-tutor/sessions/{id}/messages` | Lấy toàn bộ tin nhắn của 1 phiên | JSON array |
| `DELETE` | `/api/ai-tutor/sessions/{id}` | Xóa 1 phiên chat | JSON message |
| `POST` | `/api/ai-tutor/chat` | Gửi câu hỏi và nhận stream phản hồi | `text/event-stream` (SSE) |

### Cấu trúc sự kiện SSE (`POST /api/ai-tutor/chat`):
- `event: message` $\rightarrow$ `data: {"chunk": "Văn bản..."}`: Từng đoạn chữ trả về theo luồng.
- `event: board` $\rightarrow$ `data: {"board_data": {...}}`: Dữ liệu bàn cờ minh họa FIDE đã được validate.
- `event: done` $\rightarrow$ `data: {"session_id": "...", "message_id": "..."}`: Hoàn thành tin nhắn.
- `event: error` $\rightarrow$ `data: {"error": "..."}`: Báo lỗi thân thiện bằng tiếng Việt.

---

## 5. HƯỚNG DẪN CHẠY THỬ & KIỂM THỬ CỤC BỘ

### 5.1. Chạy Unit Test Backend
Chạy toàn bộ 61 unit tests (bao gồm 14 test mới cho bàn cờ và an toàn AI):
```powershell
cd backend
$env:PYTHONPATH="."
python -m pytest tests/test_ai_board_validator.py tests/test_ai_tutor_security.py
```

### 5.2. Chạy thử qua Docker
1. Khởi động các container:
   ```bash
   docker compose up -d
   ```
2. Truy cập giao diện Frontend:
   - Mở trình duyệt tại `http://localhost:3000`
   - Đăng nhập tài khoản học viên hoặc giáo viên.
   - Nhấn vào mục **"Hỏi đáp AI"** trên menu Sidebar (biểu tượng Bot).
3. Thử nghiệm các câu hỏi mẫu:
   - *"Khai cuộc Ý đi như thế nào?"* $\rightarrow$ AI trả lời lý thuyết và hiển thị bàn cờ ảo minh họa tương tác. Bạn có thể nhấn nút **Phát**, **Bước tới/lui**, hoặc bấm trực tiếp vào nước cờ để xem thế cờ FEN tương ứng.
   - *"Thời tiết hôm nay thế nào?"* $\rightarrow$ AI từ chối lịch sự và hướng dẫn quay lại chủ đề cờ vua.
   - *"Giải thích đòn chiếu mở"* $\rightarrow$ AI giải thích nguyên lý chiến thuật cờ vua.
