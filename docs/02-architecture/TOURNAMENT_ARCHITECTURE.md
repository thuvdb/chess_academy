# Tournament Architecture

## 1. Overview
Hệ thống giải đấu (Tournaments) cho phép trung tâm tạo các giải cờ vua trực tuyến cho học sinh. Hệ thống hỗ trợ thể thức Swiss (Hệ Thụy Sĩ) và Round Robin (Vòng tròn), ghép cặp thi đấu, và thi đấu thời gian thực qua WebSocket.

## 2. API Contract (REST)

### 2.1 Quản lý Giải đấu
- **`GET /api/tournaments`**: Lấy danh sách giải đấu (có phân trang và filter theo trạng thái).
- **`POST /api/tournaments`**: (Teacher/Admin) Tạo giải đấu mới. Payload: `name`, `format`, `time_control`, `max_participants`, `rounds`, `start_time`.
- **`GET /api/tournaments/{id}`**: Lấy chi tiết giải đấu, bao gồm danh sách người đăng ký.
- **`POST /api/tournaments/{id}/register`**: Học sinh đăng ký tham gia.
- **`POST /api/tournaments/{id}/start`**: Bắt đầu giải (chốt danh sách, random seed, sinh vòng đấu đầu tiên).
- **`POST /api/tournaments/{id}/next-round`**: Tạo cặp đấu cho vòng tiếp theo (sau khi tất cả ván của vòng hiện tại kết thúc).

### 2.2 Xem bảng đấu và kết quả
- **`GET /api/tournaments/{id}/games`**: Danh sách ván đấu (lọc theo round).
- **`GET /api/tournaments/{id}/standings`**: Bảng xếp hạng cập nhật.

## 3. Real-time Game State (WebSocket + Redis)

### 3.1 Redis State Schema
Sử dụng Redis để duy trì trạng thái ván đấu (giúp giữ trạng thái không phụ thuộc vào memory của 1 instance FastAPI).
Key: `cams:game:{game_id}`
Data Structure: HASH
Fields:
- `fen`: FEN hiện tại của ván cờ.
- `pgn`: Lịch sử các nước đi.
- `white_time_left`: Thời gian còn lại của Trắng (ms).
- `black_time_left`: Thời gian còn lại của Đen (ms).
- `last_move_at`: Timestamp (Unix ms) của nước đi cuối.
- `status`: 'ongoing', 'white_wins', 'black_wins', 'draw'.
- `turn`: 'w' hoặc 'b'.

### 3.2 WebSocket Events (`/ws/game/{game_id}`)
Kết nối được bảo mật thông qua token JWT truyền qua query parameter `?token=...`.

**Client (Browser/Mobile) -> Server:**
- `{"type": "move", "san": "Nf3"}`: Gửi nước đi (SAN hoặc UCI).
- `{"type": "resign"}`: Xin thua.
- `{"type": "draw_offer"}`: Cầu hòa.
- `{"type": "draw_accept"}`: Đồng ý hòa.

**Server -> Client:**
- `{"type": "game_state", "fen": "...", "white_time": 300, "black_time": 295, "last_move": "Nf3"}`: Cập nhật state (gửi khi có nước đi hoặc định kỳ sync).
- `{"type": "game_over", "result": "white_wins", "reason": "checkmate"}`: Báo kết quả ván cờ.
- `{"type": "error", "message": "Invalid move"}`: Báo lỗi.

## 4. Bắt cặp (Pairing System)
- **Round Robin**: Dùng thuật toán vòng tròn chuẩn (vòng tròn đa giác).
- **Swiss System**:
  - Tích hợp thư viện như `dutch-swiss-pairing` (tự viết Python logic hoặc dùng thư viện có sẵn).
  - Bắt cặp dựa trên số điểm (Points). Nếu bằng điểm thì xét hệ số Buchholz.
  - Phân bổ màu quân (trắng/đen) sao cho người chơi không cầm 1 màu 3 lần liên tiếp.

## 5. Xử lý đồng hồ cờ
Do độ trễ mạng, server-side validation clock là *nguồn chân lý*.
- Khi Server nhận `move`, sẽ tính thời gian tiêu tốn = `now - last_move_at`. Trừ vào `time_left` của người đó, rồi cộng thêm `increment` (từ `time_control`).
- Có một Background Task (Celery Beat hoặc asyncio.sleep vòng lặp) chạy định kỳ mỗi 1s trên tất cả `ongoing` games để kiểm tra `time_out` (rụng cờ). Nếu `time_left` <= 0, báo `game_over` do hết giờ.
