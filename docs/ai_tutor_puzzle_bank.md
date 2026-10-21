# CAMS-AI-03: Chess AI Tutor — Giai đoạn 3 (Puzzle Bank Integration)

## 1. Tổng quan
Tính năng "AI lấy bài tập thật từ Puzzle Bank" cho phép Trợ lý Huấn luyện viên Cờ vua AI gợi ý các bài tập cờ thế thực tế, đã qua kiểm duyệt và chứng minh lời giải từ kho bài tập trong cơ sở dữ liệu PostgreSQL của Học viện CAMS, thay vì để mô hình ngôn ngữ lớn (LLM) tự bịa ra thế cờ FEN ảo.

## 2. Kiến trúc & Nguyên tắc bảo mật

### 2.1. Anti-Hallucination & Function Calling
- Khi học viên yêu cầu bài tập (ví dụ: *"cho em bài tập đòn ghim"*, *"cho thế cờ mate in 2"*):
  - LLM gọi tool `search_puzzles(theme, level?, limit?)`.
  - Giới hạn: `limit` tối đa 3 bài, do backend cưỡng chế (`min(max(1, limit), 3)`), không phụ thuộc vào tham số từ LLM.
  - Số vòng gọi tool tối đa mỗi câu hỏi: 2 vòng, ngăn chặn vòng lặp vô tận.
- Chỉ truy vấn các thế cờ đã kiểm duyệt (`solution_verified == True`).
- Loại trừ các bài tập học viên vừa giải gần đây (dựa trên bảng `ai_puzzle_attempts`).
- Lấy ngẫu nhiên (`func.random()`) trong tập bài khớp để đa dạng hóa trải nghiệm.
- Kiểm tra tính hợp lệ của thế cờ FEN bằng thư viện `python-chess` trước khi gửi cho học viên.

### 2.2. Bảo mật đáp án (Solution Withholding)
- Lời giải tuyệt đối **KHÔNG** gửi xuống client cùng với thế cờ trong luồng SSE (`event: puzzles`).
- Dữ liệu thế cờ gửi xuống chỉ bao gồm: `id`, `fen`, `side_to_move`, `theme`, `title`, `difficulty`.
- Học viên đi thử trực tiếp trên bàn cờ tương tác và gửi nước đi lên server qua endpoint:
  `POST /api/ai-tutor/puzzles/{id}/check`
- Lời giải chỉ được hiển thị khi học viên giải đúng toàn bộ hoặc chủ động bấm nút **"Xem đáp án"**.
- AI chỉ nhận lời giải chính thức từ DB để giải thích chiến thuật sau khi học viên đã giải xong hoặc bấm xem đáp án.

### 2.3. Bảng cơ sở dữ liệu mới (`ai_puzzle_attempts`)
- `id`: UUID (Primary Key)
- `user_id`: UUID (Foreign Key `users.id`, ondelete `CASCADE`)
- `puzzle_id`: UUID (Foreign Key `puzzles.id`, ondelete `CASCADE`)
- `session_id`: UUID (Foreign Key `chat_sessions.id`, ondelete `SET NULL`)
- `is_correct`: Boolean (đánh dấu giải thành công hay thất bại)
- `attempts_count`: Integer (số lần đi thử của học viên)
- `hints_used`: Integer (số lần bấm gợi ý chủ đề)
- `created_at`: Timestamp with time zone
- Cột bổ sung trong `chat_messages`: `puzzle_data` (`JSONB`, nullable) để lưu trữ danh sách bài tập phục vụ việc tải lại lịch sử đoạn chat.

## 3. Danh sách Endpoints API

| Phương thức | Đường dẫn | Chức năng |
| :--- | :--- | :--- |
| `POST` | `/api/ai-tutor/chat` | Luồng SSE hỗ trợ thêm event `puzzles` khi AI gọi tool `search_puzzles` |
| `POST` | `/api/ai-tutor/puzzles/{id}/check` | Kiểm tra nước đi học viên, trả về đúng/sai và nước đi đáp trả của đối thủ |
| `GET` | `/api/ai-tutor/puzzles/{id}/hint` | Lấy gợi ý chủ đề đòn chiến thuật và ghi nhận số lượt xem gợi ý |
| `POST` | `/api/ai-tutor/puzzles/{id}/solution` | Lấy chuỗi nước đi đáp án chính thức khi học viên yêu cầu |
| `POST` | `/api/ai-tutor/puzzles/{id}/explain` | Yêu cầu AI phân tích ý đồ chiến thuật dựa trên đáp án thực tế |

## 4. Giao diện Frontend (`PuzzleCard.tsx`)
- Thẻ bài tập tương tác nhúng trực tiếp trong bong bóng chat AI Tutor.
- Bàn cờ trực quan dùng `react-chessboard` và `chess.js`, hỗ trợ kéo thả hoặc click chọn ô.
- Tự động xoay bàn cờ theo bên đi (`white` nếu Trắng đi trước, `black` nếu Đen đi trước).
- Tự động đi nước đáp trả của đối thủ khi học viên đi đúng nước đầu tiên trong thế cờ nhiều nước.
- Nút **Làm lại** (reset thế cờ ban đầu), **Gợi ý** (hiện chủ đề bài tập), **Xem đáp án** (hiện chuỗi nước đi chi tiết) và **Nhờ AI giải thích** (phân tích chuyên sâu từ Huấn luyện viên AI).
