# CAMS — Chess Academy Management System

**CAMS (Chess Academy Management System)** là hệ thống quản lý học viện cờ vua toàn diện kết hợp Trí tuệ Nhân tạo (AI). Hệ thống hỗ trợ tự động số hóa bài tập từ sách PDF bằng Computer Vision, quản lý đào tạo (lớp học, học viên, lịch học, điểm danh), cổng thanh toán học phí VietQR, ngân hàng bài tập tương tác (Puzzle Bank) và tổ chức giải đấu cờ vua trực tuyến.

---

## 🌟 Tính năng chính

- **AI Scanner & Computer Vision**: Tự động nhận diện bàn cờ từ sách/tài liệu PDF, cắt ảnh, phân loại quân cờ, trích xuất chuỗi FEN, phân tích nước đi với Stockfish và tự động đồng bộ sang ngân hàng bài tập.
- **Puzzle Bank & Luyện tập tương tác**: Thư viện bài tập chiến thuật phân loại theo chủ đề và độ khó, bàn cờ tương tác thông minh (chấm tròn nước đi, cảnh báo đỏ khi chiếu Vua), tính điểm và cập nhật Puzzle Rating.
- **Quản lý Đào tạo & Học viện**: Quản lý đa trung tâm (Multi-tenant), phân quyền người dùng (Super Admin, Admin, Giáo viên, Học sinh, Phụ huynh), quản lý lớp học, điểm danh và lịch học (Schedule).
- **Giải đấu Cờ vua (Tournaments)**: Tổ chức giải đấu cờ vua nội bộ theo hệ Thụy Sĩ (Swiss System) hoặc Vòng tròn (Round Robin), thi đấu cờ trực tiếp thời gian thực qua WebSocket.
- **Học phí & Tài chính**: Cấu hình gói học phí (Fee Plans), quản lý hóa đơn (Invoices) và tích hợp mã thanh toán VietQR tự động.
- **Ứng dụng Di động**: Ứng dụng mobile đa nền tảng (React Native / Expo) dành cho học sinh và phụ huynh.

---

## 🏗️ Cấu trúc dự án & Công nghệ

| Thành phần | Thư mục | Công nghệ sử dụng |
| :--- | :--- | :--- |
| **Backend API** | `backend/` | FastAPI (Python 3.11), SQLAlchemy 2 (Async), PostgreSQL 16, Stockfish 16 Engine |
| **Worker & Beat** | `backend/` | Celery, Redis 7 (Xử lý tác vụ nền cho AI Scan và giải đấu) |
| **AI / Computer Vision** | `backend/app/services/` | OpenCV, YOLO (Ultralytics), PyMuPDF (fitz), Python-Chess |
| **Frontend Web** | `frontend/` | React 19, Vite, TypeScript, Tailwind CSS, react-chessboard, chess.js |
| **Mobile App** | `mobile/` | React Native, Expo |
| **Tài liệu Kỹ thuật** | `docs/` | Đặc tả yêu cầu, thiết kế hệ thống, kiến trúc AI & Payment |
| **Điều phối Dịch vụ** | `docker-compose.yml` | Quản lý 6 container (`backend`, `worker`, `beat`, `frontend`, `db`, `redis`) |

---

## 📋 Yêu cầu môi trường

- **Docker Desktop** (hỗ trợ `docker compose` v2 trở lên)
- **Git**
- **Node.js** v20+ (chỉ cần nếu phát triển hoặc chạy riêng ứng dụng `mobile`)

---

## 🚀 Hướng dẫn Cài đặt & Khởi động

### 1. Tải mã nguồn

```bash
git clone https://github.com/thuvdb/chess_academy.git
cd chess_academy
```

### 2. Thiết lập biến môi trường (`.env`)

Tạo file `.env` từ file mẫu `.env.example`:

```bash
# Windows (CMD)
copy .env.example .env

# Windows (PowerShell) hoặc Linux / macOS
cp .env.example .env
```

Mở file `.env` và điền đầy đủ các giá trị bảo mật bắt buộc:

```env
POSTGRES_USER=cams_user
POSTGRES_PASSWORD=your_strong_postgres_password
POSTGRES_DB=cams_db

# Lưu ý: REDIS_PASSWORD chỉ dùng ký tự hex/chữ số, không chứa ký tự đặc biệt
REDIS_PASSWORD=your_hex_redis_password

# Khóa bí mật ký JWT Token (bắt buộc)
JWT_SECRET_KEY=your_jwt_secret_key_32_bytes_hex
```

> **Mẹo:** Bạn có thể tạo chuỗi bí mật an toàn ngẫu nhiên bằng lệnh:
> - Trên Linux / macOS: `openssl rand -hex 32`
> - Trên PowerShell (Windows): `[Convert]::ToHexString((1..32 | ForEach-Object { Get-Random -Maximum 256 }))`

### 3. Chuẩn bị thư mục dữ liệu

Thư mục lưu trữ file PDF sách cờ vua và ảnh quét được cấu hình trong `backend/storage/scans/`. Thư mục này nằm trong danh sách loại trừ của `.gitignore`. Khi cài mới, hệ thống sẽ tự động tạo thư mục khi người dùng tải file lên.

### 4. Khởi động toàn bộ hệ thống bằng Docker

```bash
docker compose up -d --build
```

Kiểm tra trạng thái các container:

```bash
docker compose ps
```

### 5. Khởi tạo Cơ sở Dữ liệu (Migrations) — *Bắt buộc khi chạy lần đầu*

Sau khi các container khởi động, chạy lệnh migration của Alembic để tự động khởi tạo toàn bộ bảng dữ liệu trong PostgreSQL:

```bash
docker compose exec backend alembic upgrade head
```

---

## 🌐 Địa chỉ truy cập dịch vụ

Sau khi khởi động thành công:

| Dịch vụ | Địa chỉ truy cập | Ghi chú |
| :--- | :--- | :--- |
| **Giao diện Web (Frontend)** | [http://localhost:3000](http://localhost:3000) | Giao diện quản trị, học tập và giải đấu |
| **Backend API** | [http://localhost:8000](http://localhost:8000) | REST API & WebSocket |
| **Tài liệu API (Swagger UI)** | [http://localhost:8000/docs](http://localhost:8000/docs) | Tra cứu và thử nghiệm API trực tiếp |
| **Tài liệu API (ReDoc)** | [http://localhost:8000/redoc](http://localhost:8000/redoc) | Giao diện tài liệu API chi tiết |

> **Bắt đầu sử dụng:** Truy cập [http://localhost:3000/register](http://localhost:3000/register) để đăng ký tài khoản quản trị viên đầu tiên cho trung tâm.

---

## 📱 Chạy ứng dụng Mobile (Tùy chọn)

Để chạy ứng dụng di động dành cho học sinh/phụ huynh:

```bash
cd mobile
npm install
npx expo start
```

Dùng ứng dụng **Expo Go** trên điện thoại (iOS / Android) để quét mã QR và trải nghiệm.

---

## 🛠️ Quản lý & Vận hành

Xem log của hệ thống theo thời gian thực:

```bash
# Xem log toàn bộ hệ thống
docker compose logs -f

# Hoặc xem log riêng từng dịch vụ
docker compose logs -f backend
docker compose logs -f worker
docker compose logs -f frontend
```

Dừng toàn bộ hệ thống:

```bash
docker compose down
```

Nếu muốn xóa toàn bộ dữ liệu database để cài đặt lại từ đầu:

```bash
docker compose down -v
```

---

## 🔒 Lưu ý bảo mật

- **Không commit file `.env`** hoặc bất kỳ file chứa API key, mật khẩu, JWT secret lên kho lưu trữ Git.
- Cấu hình tường lửa: Các cổng nội bộ của PostgreSQL (`5432`) và Redis (`6379`) mặc định không mở ra ngoài Internet, chỉ giao tiếp nội bộ trong mạng Docker network.
- Trước khi triển khai môi trường Production thực tế, hãy đổi toàn bộ mật khẩu mặc định sang mật khẩu có độ phức tạp cao và cấu hình domain thật tại biến `CORS_ORIGINS`.

---

## 📖 Tài liệu kỹ thuật chi tiết

Các tài liệu thiết kế và kiến trúc chuyên sâu được lưu trữ tại thư mục `docs/`:

- [docs/01-sdlc/01_requirements.md](docs/01-sdlc/01_requirements.md) — Đặc tả yêu cầu chức năng & phi chức năng.
- [docs/02-architecture/02_system_design.md](docs/02-architecture/02_system_design.md) — Thiết kế kiến trúc tổng thể, luồng dữ liệu & ERD cơ sở dữ liệu.
- [docs/02-architecture/AI_SCANNER_ARCHITECTURE.md](docs/02-architecture/AI_SCANNER_ARCHITECTURE.md) — Quy trình Computer Vision xử lý sách PDF và nhận diện bàn cờ.
- [docs/02-architecture/PAYMENT_ARCHITECTURE.md](docs/02-architecture/PAYMENT_ARCHITECTURE.md) — Thiết kế luồng học phí, hóa đơn và tích hợp VietQR.
- [docs/02-architecture/TOURNAMENT_ARCHITECTURE.md](docs/02-architecture/TOURNAMENT_ARCHITECTURE.md) — Thuật toán bốc thăm (Swiss/Round Robin) và xử lý giải đấu.
- [docs/03-operations/HANDOFF_SOP.md](docs/03-operations/HANDOFF_SOP.md) — Quy trình bàn giao và checkpoint kỹ thuật.

---

## 📄 Bản quyền & Tác giả

Dự án được phát triển cho Hệ thống Quản lý Học viện Cờ vua CAMS.
Mọi quyền được bảo lưu © 2026.
