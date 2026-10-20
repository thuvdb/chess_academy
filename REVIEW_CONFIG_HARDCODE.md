# BÁO CÁO RÀ SOÁT & TÁCH CẤU HÌNH MÔI TRƯỜNG (CAMS - CHESS ACADEMY)

> **Mã công việc:** CAMS-0033, CAMS-0034, CAMS-0035  
> **Thời gian thực hiện:** 20/10/2026  
> **Phạm vi:** Backend (FastAPI), Background Worker (Celery), Frontend (React/Vite), Docker Compose, Quản trị biến môi trường  

---

## 1. TỔNG QUAN HIỆN TRẠNG TRƯỚC KHI RÀ SOÁT (BƯỚC 0)

Trước khi thực hiện tách cấu hình, hệ thống tồn tại nhiều giá trị hard-code rải rác:
- **Địa chỉ IP VPS:** `129.153.55.144` xuất hiện trong cấu hình CORS của `docker-compose.yml` và chú thích test của `playwright.config.ts`.
- **Localhost & Cổng:** `http://localhost:8000` bị gán cứng trong `api.ts`, `LiveGame.tsx`, `users.py` (upload avatar), `storage_service.py`.
- **CORS:** Danh sách CORS dạng JSON array cứng, không tự co giãn linh hoạt theo biến môi trường.
- **Stockfish & AI:**
  - Đường dẫn `/usr/games/stockfish` và độ sâu `depth=15` bị gán cứng trong code.
  - Đường dẫn mô hình YOLOv8 `chess_yolov8s.pt` bị gán cứng trong `piece_classifier.py`.
- **Thư mục Upload & Giới hạn dung lượng:**
  - Chuỗi `"uploads"` và giới hạn `50 * 1024 * 1024` (50MB) nằm rải rác trong `main.py`, `scan.py`, `users.py`.
- **Dữ liệu mẫu (Seed):**
  - Mật khẩu các tài khoản UAT (`Super@2026!`, `Admin@2026!`, ...) và tên chi nhánh `Cơ sở Chính - Quận 1` gán cứng trong `seed_uat.py`. Chưa có cơ chế ngăn chặn script seed chạy nhầm trên môi trường Production.
- **Kiểm tra Git History:**
  - Đã chạy kiểm tra `git log --all --full-history -- ".env" "backend/.env" "frontend/.env"`.
  - **Kết luận:** Chưa từng có file `.env` chứa bí mật thật nào bị commit vào git history. Chỉ có `.env.example` với các giá trị mẫu.

---

## 2. DANH SÁCH BIẾN MÔI TRƯỜNG ĐÃ TÁCH TẬP TRUNG

Toàn bộ các giá trị cấu hình đã được quy chuẩn hóa trong file mẫu [`.env.example`](./.env.example):

| Tên biến | File cấu hình nguồn | Mặc định / Fallback | Mục đích & Mô tả |
| :--- | :--- | :--- | :--- |
| `APP_ENV` | `backend/app/core/config.py` | `local` | Môi trường triển khai: `local`, `uat`, `production`. |
| `DEBUG` | `backend/app/core/config.py` | `false` | Bật/tắt debug mode (tự động khóa `false` khi `APP_ENV=production`). |
| `LOG_LEVEL` | `backend/app/core/config.py` | `INFO` | Mức log của hệ thống: `DEBUG`, `INFO`, `WARNING`, `ERROR`. |
| `BACKEND_PORT` | `docker-compose.yml` | `8000` | Cổng máy chủ nhận request cho Backend API. |
| `FRONTEND_PORT` | `docker-compose.yml` | `3000` | Cổng máy chủ nhận request cho Frontend Web. |
| `POSTGRES_USER` | `docker-compose.yml` | `cams_user` | Tên user PostgreSQL (khai báo tập trung 1 chỗ). |
| `POSTGRES_PASSWORD` | `docker-compose.yml` | *(Bắt buộc)* | Mật khẩu cơ sở dữ liệu PostgreSQL. |
| `POSTGRES_DB` | `docker-compose.yml` | `cams_db` | Tên cơ sở dữ liệu chính. |
| `DATABASE_URL` | `backend/app/core/config.py` | Tự động ghép | Chuỗi kết nối asyncpg đến PostgreSQL. |
| `REDIS_PASSWORD` | `docker-compose.yml` | *(Bắt buộc)* | Mật khẩu bảo vệ cụm Redis / Celery. |
| `REDIS_URL` | `backend/app/core/config.py` | Tự động ghép | URL kết nối Redis cache. |
| `CELERY_BROKER_URL` | `backend/app/core/config.py` | Tự động ghép | URL broker của Celery background queue. |
| `CELERY_RESULT_BACKEND` | `backend/app/core/config.py` | Tự động ghép | URL lưu trữ kết quả task Celery. |
| `JWT_SECRET_KEY` | `backend/app/core/config.py` | *(Bắt buộc)* | Khóa bí mật ký JWT (tối thiểu 32 ký tự trên prod). |
| `JWT_ALGORITHM` | `backend/app/core/config.py` | `HS256` | Thuật toán ký JWT. |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | `backend/app/core/config.py` | `1440` | Thời hạn hiệu lực của Access Token (phút). |
| `REFRESH_TOKEN_EXPIRE_DAYS` | `backend/app/core/config.py` | `7` | Thời hạn hiệu lực của Refresh Token (ngày). |
| `BACKEND_CORS_ORIGINS` | `backend/app/core/config.py` | `http://localhost:3000,http://localhost:5173` | Danh sách domain Frontend được phép gọi API (dấu phẩy). |
| `API_PUBLIC_URL` | `backend/app/core/config.py` | `http://localhost:8000` | URL công khai của Backend API (dùng sinh link chữ ký số HMAC). |
| `UPLOAD_DIR` | `backend/app/core/config.py` | `uploads` | Thư mục lưu file tĩnh và avatar người dùng. |
| `MAX_UPLOAD_SIZE_MB` | `backend/app/core/config.py` | `50` | Giới hạn dung lượng tải PDF scan tối đa (MB). |
| `STOCKFISH_PATH` | `backend/app/core/config.py` | `/usr/games/stockfish` | Đường dẫn file thực thi Stockfish engine. |
| `STOCKFISH_DEPTH` | `backend/app/core/config.py` | `15` | Độ sâu tìm kiếm nước đi tối ưu của Stockfish. |
| `YOLO_MODEL_PATH` | `backend/app/core/config.py` | `models/chess_yolov8s.pt` | Đường dẫn mô hình YOLOv8 nhận diện quân cờ. |
| `SEED_DEFAULT_PASSWORD` | `backend/app/core/config.py` | `Cams@2026!` | Mật khẩu mặc định gán cho các tài khoản seed UAT. |
| `DEFAULT_BRANCH_NAME` | `backend/app/core/config.py` | `Cơ sở Chính - Quận 1` | Tên cơ sở / chi nhánh mặc định khi seed. |
| `VITE_API_BASE_URL` | `frontend/src/config.ts` | `/api` | Base URL gọi API từ Frontend (cùng Origin). |
| `VITE_WS_BASE_URL` | `frontend/src/config.ts` | `(auto wss/ws)` | Base URL WebSocket cho trận đấu trực tiếp. |
| `VITE_DEFAULT_TIMEZONE` | `frontend/src/config.ts` | `Asia/Ho_Chi_Minh` | Múi giờ mặc định trên giao diện người dùng. |
| `VITE_PAGE_SIZE` | `frontend/src/config.ts` | `20` | Phân trang mặc định cho danh sách thế cờ AI Scanner. |

---

## 3. CÁC THAY ĐỔI THEO TỪNG BƯỚC & LỊCH SỬ COMMIT

### Bước 1: Backend & Worker (`CAMS-0033`) — Commit `b4d11f3`
- Xây dựng lại `backend/app/core/config.py` dựa trên `pydantic-settings` với `SettingsConfigDict(populate_by_name=True)`.
- **Cơ chế bảo vệ Production:**
  - Nếu `APP_ENV=production`: Backend từ chối khởi động nếu `JWT_SECRET_KEY` là giá trị mặc định hoặc ngắn hơn 32 ký tự, hoặc `DATABASE_URL` dùng mật khẩu mặc định.
  - Tắt hoàn toàn Swagger docs (`/docs`, `/redoc`, `/openapi.json`) và tắt `debug` khi chạy trên production.
  - `seed_uat.py` tự động hủy bỏ và báo lỗi `RuntimeError` nếu người dùng cố tình chạy trên `APP_ENV=production`.
- Tách triệt để giá trị hard-code trong `main.py`, `scan.py`, `users.py`, `stockfish_service.py`, `piece_classifier.py`, `storage_service.py`.
- **Kiểm thử:** 69 unit tests chạy thành công 100%.

### Bước 2: Frontend (`CAMS-0034`) — Commit `becb375`
- Tạo file cấu hình trung tâm `frontend/src/config.ts`.
- Không hard-code cổng hay URL trong code Frontend:
  - Mặc định gọi qua `/api` và `/ws` cùng Origin.
  - Khi dev local: `vite.config.ts` tự động proxy `/api`, `/ws`, `/static` sang `http://localhost:8000`.
  - Khi chạy Docker/Production: `frontend/nginx.conf` tự động reverse proxy `/api/`, `/ws`, `/static/` sang backend container.
- Rà soát và xóa sạch các chuỗi `http://localhost:8000`, IP VPS trong `api.ts`, `LiveGame.tsx`, `Profile.tsx`, `Scanner.tsx`, `Sidebar.tsx`, `Members.tsx`, `Leaderboard.tsx`.
- **Kiểm thử:** `npm run build` (`tsc -b && vite build`) hoàn thành sạch sẽ không lỗi.

### Bước 3: Docker & Mẫu Cấu Hình (`CAMS-0035`) — Commit `ac850bb`
- Chuẩn hóa `docker-compose.yml`:
  - Khai báo thông tin Postgres 1 chỗ, biến môi trường kế thừa từ `.env`.
  - Cổng publish `8000` và `3000` cho phép ghi đè qua `BACKEND_PORT` và `FRONTEND_PORT`.
  - Cung cấp build args cho frontend (`VITE_API_BASE_URL`, `VITE_WS_BASE_URL`, v.v.).
- Thêm `.dockerignore` tại thư mục gốc và `backend/.dockerignore` nhằm ngăn chặn rò rỉ file `.env` vào Docker image.
- Soạn thảo `.env.example` và `backend/.env.example` với hướng dẫn tiếng Việt chi tiết từng biến, không chứa secret thật.

---

## 4. KẾT QUẢ KIỂM THỬ XÁC MINH TOÀN DỰ ÁN (BƯỚC 4)

1. **Quét tìm kiếm chuỗi:**
   - IP `129.153.55.144`: **0 kết quả** (Đã loại bỏ triệt để).
   - `localhost`: Chỉ còn ở `.env.example`, fallback mặc định cho local dev khi không có `.env`, và cấu hình `server_name localhost` chuẩn Nginx.
2. **Khởi chạy cả 6 container Docker trên máy:**
   - `cams_frontend`: **Up (healthy)** - Cổng 3000
   - `cams_backend`: **Up** - Cổng 8000
   - `cams_worker`: **Up** (Celery worker sẵn sàng)
   - `cams_beat`: **Up** (Celery beat chạy lịch định kỳ)
   - `cams_postgres`: **Up** (PostgreSQL 16)
   - `cams_redis`: **Up** (Redis 7)
3. **Kiểm tra thông tuyến mạng:**
   - `curl http://localhost:8000/health` -> `{"status":"ok"}`
   - `curl http://localhost:3000/` -> Phục vụ SPA `CAMS - Học Viện Cờ Vua`
   - `curl http://localhost:3000/api/settings` -> Nginx proxy thành công tới Backend API (trả về JSON 401 do chưa truyền Bearer Token).

---

## 5. HƯỚNG DẪN THIẾT LẬP KHI DEPLOY LÊN VPS

Khi triển khai code mới lên máy chủ VPS (UAT hoặc Production):

1. **Tạo file cấu hình `.env`:**
   ```bash
   cp .env.example .env
   nano .env
   ```
2. **Cập nhật các biến quan trọng:**
   ```env
   APP_ENV=production
   DEBUG=false
   JWT_SECRET_KEY=<tạo bằng: openssl rand -hex 32>
   POSTGRES_PASSWORD=<tạo mật khẩu ngẫu nhiên mạnh>
   REDIS_PASSWORD=<tạo mật khẩu hex ngẫu nhiên>
   BACKEND_CORS_ORIGINS=https://cams-app.duckdns.org,http://cams-app.duckdns.org
   API_PUBLIC_URL=https://cams-api.duckdns.org
   ```
3. **Build và khởi động lại dịch vụ:**
   ```bash
   docker compose down
   docker compose up -d --build
   ```
