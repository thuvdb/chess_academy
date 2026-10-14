# CAMS – Phase 0: Chuẩn bị triển khai thử nghiệm lên Oracle Cloud Free Tier

> Tài liệu dành cho AI Agent (Antigravity IDE). Đọc toàn bộ trước khi sửa bất cứ thứ gì.
> Dự án: `C:\ProjectAI\chess_academy` – backend FastAPI + PostgreSQL + Celery/Redis, frontend React/Vite/TypeScript.
> Mục tiêu: đưa hệ thống lên một máy chủ Oracle (Ubuntu 24.04, kiến trúc **Arm aarch64**, 2 OCPU / 12 GB RAM) để đồng nghiệp test chức năng.
> Phân quyền đa trung tâm (`CAMS_SPEC_multi_center_rbac_v1.1.md`) **chưa làm** và **không thuộc phạm vi** tài liệu này.

---

## 0. Quy tắc làm việc (bắt buộc)

1. **Tuyệt đối không dò, đoán, bẻ khóa mật khẩu** của bất kỳ tài khoản nào. **Không in hash mật khẩu, mật khẩu, JWT secret hay giá trị trong `.env`** ra log, báo cáo hoặc commit.
2. Không đọc hay sửa dữ liệu người dùng thật trong DB ngoài những gì task yêu cầu. Không tạo tác vụ định kỳ (schedule) hay file ngoài phạm vi.
3. Trước khi sửa, đọc code thực tế. Nếu spec này mâu thuẫn với code, **dừng và báo cáo** điểm mâu thuẫn.
4. Mỗi nhóm việc ở mục 3 là một commit riêng, theo quy ước `CAMS-xxxx: <mô tả>`.
5. Không commit: `.env`, file trong `backend/storage/scans`, bản dump DB, `node_modules`.
6. Chưa chạy trên Arm được thì **không khẳng định đã kiểm tra Arm**; ghi rõ "chưa kiểm tra trên Arm".
7. Cấu hình (cờ bật/tắt, địa chỉ, giới hạn) đọc từ biến môi trường hoặc bảng cài đặt, không viết cứng trong code.

---

## 1. Hiện trạng đã xác nhận (không cần điều tra lại)

- `POST /api/auth/register` nhận `role` (và `center_id`) từ client, **không có kiểm tra quyền**. Gọi trực tiếp API với `role: "super_admin"` là tạo được tài khoản quản trị tối cao. Giao diện `Register.tsx` chỉ gửi `role: "student"` cứng.
- `POST /api/auth/google` và `POST /api/auth/facebook` tự tạo user mới với `role=student`, `center_id=NULL`.
- Không có API hay giao diện để admin tạo giáo viên, học viên, phụ huynh. Trang Members chỉ đọc; nút Enroll chỉ gán người đã có tài khoản vào lớp.
- Không có file `seed.py`. Database mới (trống) sẽ **không có tài khoản nào**.
- Mật khẩu của các tài khoản mẫu hiện có là yếu hoặc dùng chung; **không được đưa bản sao DB local lên server**.
- Mọi API nằm dưới tiền tố `/api` (frontend: `baseURL = import.meta.env.VITE_API_URL || 'http://localhost:8000/api'`).
- Stockfish cài bằng `apt install stockfish` trong `backend/Dockerfile` (nền `python:3.11-slim`); đường dẫn mặc định `STOCKFISH_PATH = "/usr/games/stockfish"` trong `app/core/config.py`; dịch vụ `stockfish_service.py` dùng gói Python `stockfish` và tạo một tiến trình Stockfish mới cho mỗi lần gọi.
- `docker-compose.yml` hiện là bản **phát triển**: frontend chạy `npm run dev` (Vite dev server, không có `npm install`), backend chạy `--reload` với `./backend:/app` mount, cổng 8000 và 3000 mở công khai.
- `backend/requirements.txt` khai báo `stockfish` hai lần (`3.28.*` và `3.28.0`), và không ghim `bcrypt` (kéo theo `passlib[bcrypt]==1.7.*`).
- `.env.example` trong repo **không chứa** dòng `STOCKFISH`; bản `_env.example` đã gửi khác với file trong repo. Đọc file thật trong repo.

---

## 2. Kiến trúc triển khai thử nghiệm

- Một tên miền duy nhất (`SITE_ADDRESS`), Caddy làm cổng duy nhất mở ra Internet (80/443, HTTPS tự động):
  - `/api/*` → `backend:8000`
  - đường dẫn WebSocket của giải đấu → `backend:8000` (Agent xác định đường dẫn thật, mục 3.4)
  - mọi đường dẫn khác → file tĩnh của frontend (`try_files {path} /index.html` cho SPA)
- PostgreSQL và Redis **không mở cổng**, chỉ nằm trong mạng Docker.
- Swagger (`/docs`, `/redoc`) nằm ngoài `/api` nên **không được proxy** ra Internet; chỉ truy cập được qua SSH tunnel khi cần.
- **Không dùng `basicauth` của Caddy** để bảo vệ cả site: nó dùng header `Authorization`, trùng với `Bearer` token của ứng dụng và sẽ làm hỏng đăng nhập. Nếu cần giới hạn người truy cập thì dùng danh sách IP (`remote_ip`).

---

## 3. Công việc

### 3.1 Vá bảo mật `/register` (ưu tiên cao nhất)

1. `POST /api/auth/register`: Backend **bỏ qua `role` và `center_id` do client gửi**; luôn tạo `role=student`, `center_id=NULL`. Chỉ nhận họ tên, email, mật khẩu.
2. Thêm cấu hình `ALLOW_PUBLIC_REGISTER` (biến môi trường, đọc qua `settings`, mặc định `false` khi `DEBUG=false`, `true` khi chạy local `DEBUG=true`).
   - Khi `false`: `POST /api/auth/register` trả 403 với thông báo rõ; đăng nhập Google/Facebook **không tạo user mới** (chỉ cho người dùng đã tồn tại đăng nhập).
   - Có endpoint công khai chỉ đọc (ví dụ `GET /api/auth/config`) trả `{ "allow_public_register": bool }`. Frontend ẩn liên kết/trang "Đăng ký" khi giá trị là `false`.
3. Mật khẩu: kiểm tra độ dài tối thiểu (cấu hình được, mặc định 8) ở Backend.
4. **Khởi động có kiểm tra:** khi `DEBUG=false`, nếu `JWT_SECRET_KEY` rỗng, ngắn hơn 32 ký tự, hoặc bằng giá trị mẫu (`change-me...`) thì ứng dụng từ chối khởi động với thông báo rõ.
5. `CORS_ORIGINS` khi `DEBUG=false` không được chứa `*`.
6. Test (pytest): gửi `role=super_admin` và `center_id` tùy ý → user tạo ra là `student`, `center_id=NULL`; cờ tắt → 403; cờ tắt → social login với email mới không tạo user.

### 3.2 Script tạo trung tâm và người dùng (thay cho giao diện, chạy trên server)

Tạo `backend/scripts/create_center.py` và `backend/scripts/create_user.py`, chạy trong container: `docker compose -f docker-compose.prod.yml exec backend python scripts/create_user.py ...`

- `create_center.py`: tham số `--name`, `--code`. Báo lỗi rõ nếu `code` đã tồn tại. In ra `id` và `code` đã tạo.
- `create_user.py`: tham số `--email`, `--full-name`, `--role` (`super_admin|admin|teacher|student|parent`, đúng tập giá trị enum hiện có trong `app/models/base.py`), `--center-code` (tùy chọn; `super_admin` không được có), `--password-env TEN_BIEN` (đọc mật khẩu từ biến môi trường) hoặc nhập qua `getpass` lúc chạy. Nếu không cung cấp thì **tự sinh mật khẩu ngẫu nhiên** (`secrets`), **in một lần duy nhất** ra terminal và không ghi vào bất cứ file hay log nào.
- Dùng đúng hàm băm mật khẩu và model hiện có của ứng dụng (`app/core/security.py`, `app/models/user.py`); không tự viết cách băm khác.
- Từ chối nếu email đã tồn tại. Không in hash, không ghi mật khẩu vào lịch sử shell (không nhận mật khẩu qua tham số dòng lệnh).
- Chế độ `--dry-run`: kiểm tra và in những gì sẽ tạo, không ghi DB.
- Test: tạo user bằng script, rồi đăng nhập thành công qua API; mật khẩu sai bị từ chối; chạy lần hai với cùng email báo lỗi.

> Chức năng "admin tạo người dùng qua giao diện" thuộc bước 3 của spec phân quyền, chưa làm ở Phase 0.

### 3.3 Phụ thuộc Python

1. Xóa dòng trùng `stockfish==3.28.0`, giữ một khai báo duy nhất.
2. Chạy `docker compose exec backend pip show bcrypt passlib` trong container local đang chạy tốt, rồi **ghim chính xác phiên bản `bcrypt`** đó vào `requirements.txt` (passlib 1.7 có báo cáo lỗi với một số phiên bản bcrypt mới). Không dùng `pip freeze` nguyên bản để làm file khóa, vì trên x86 nó chứa các gói `nvidia-*` không có bản Arm.
3. Rà các gói còn lại có bản wheel `aarch64` cho Python 3.11 (`asyncpg`, `pymupdf`, `opencv-python-headless`, `ultralytics`/`torch`, `uvloop`, `httptools`, `cryptography`, `bcrypt`). Báo cáo gói nào **không** có wheel Arm hoặc phải biên dịch từ mã nguồn. Nếu có thể chạy `docker buildx build --platform linux/arm64 ./backend` thì chạy; nếu không, ghi "chưa kiểm tra trên Arm".
4. Kiểm tra file trọng số YOLO (`*.pt`/`*.onnx`) nằm ở đâu: trong repo (kích thước bao nhiêu, có bị `.gitignore` không) hay tải lúc chạy từ Internet. Báo lại để biết server cần gì.

### 3.4 Frontend: build bản chạy thật

1. Tìm trong `frontend/src` mọi chỗ viết cứng địa chỉ: `localhost:8000`, `127.0.0.1`, `ws://`, `wss://`, `http://` và mọi chỗ dùng `import.meta.env.VITE_*`. Liệt kê và thay bằng cách tính địa chỉ từ `VITE_API_URL` (hoặc từ `window.location` cho WebSocket: `wss://` khi trang chạy HTTPS).
2. Ghi lại **đường dẫn WebSocket** của backend và mọi đường dẫn backend không nằm dưới `/api` (static, storage, health…). Dùng để hoàn thiện `deploy/Caddyfile`.
3. Bản chạy thật dùng `VITE_API_URL=/api` (cùng nguồn gốc, không cần CORS). Xác nhận `axios` hoạt động với `baseURL` tương đối.
4. Xác nhận `npm run build` chạy sạch (kể cả kiểm tra kiểu TypeScript) và xử lý lỗi nếu có. Xác nhận có `package-lock.json`; nếu không thì dùng `npm install` trong Dockerfile và báo lại.
5. SPA: tải lại trang ở đường dẫn sâu (ví dụ `/assignments/<id>`) phải vào đúng giao diện nhờ `try_files`.

### 3.5 File triển khai

Tạo (dựa trên bản nháp ở mục 4, chỉnh cho đúng dự án):
- `docker-compose.prod.yml` (độc lập, **không** dùng làm file ghi đè, vì Compose gộp danh sách `ports` thay vì thay thế).
- `frontend/Dockerfile.prod` (build tĩnh + Caddy).
- `deploy/Caddyfile`.
- `.dockerignore` (gốc repo) và `backend/.dockerignore`.
- `.gitattributes`: `*.sh text eol=lf` (máy phát triển là Windows; script có CRLF sẽ lỗi trên Linux).
- `.env.example` mới khớp đúng với biến mà compose dùng (mục 4.5), không chứa giá trị bí mật thật.
- Giữ nguyên `docker-compose.yml` cho môi trường phát triển.

Kiểm tra thêm:
- Dữ liệu `storage/scans` dùng **named volume**, dùng chung cho `backend` và `worker`; xác nhận đường dẫn lưu thật của ứng dụng (grep) và gắn volume đúng chỗ.
- `worker` chạy `--concurrency=1`.
- Backend chạy không có `--reload`, thêm `--proxy-headers --forwarded-allow-ips="*"`.
- `API_PUBLIC_URL`: xác nhận ứng dụng dùng nó để làm gì (tạo đường dẫn ảnh/file?) và đặt giá trị cho đúng với việc Caddy chỉ proxy `/api/*`.

### 3.6 Sao lưu và vận hành

- `deploy/backup.sh`: `pg_dump` qua `docker compose exec -T db`, nén gzip, đặt tên theo ngày, giữ 7 bản gần nhất, ghi ra thư mục `backups/` (đã nằm trong `.gitignore`). Dùng được với `cron`.
- `deploy/README_DEPLOY.md` ngắn: lệnh build, khởi động, `alembic upgrade head`, tạo trung tâm và người dùng, cập nhật, xem log, sao lưu, khôi phục. Không chứa giá trị bí mật.

### 3.7 Kiểm tra Stockfish trong container (làm được ở local)

1. `docker compose exec backend sh -c 'echo quit | /usr/games/stockfish'` in dòng đầu (tên và phiên bản). Báo phiên bản (README ghi 16).
2. Đếm tiến trình Stockfish còn sót sau khi chạy luồng chấm bài (nộp bài có nước ngoài đáp án): `ps aux | grep -c stockfish`. Nếu tiến trình sót lại sau mỗi lần gọi, sửa để giải phóng đúng (ví dụ đóng tiến trình sau khi dùng) và báo lại.
3. Đo thời gian trung bình của `evaluate_alternate_solution` (độ sâu 15) và `mate_solver` (độ sâu 13/14) trên máy local để làm mốc so sánh với server Arm.

---

## 4. Bản nháp file triển khai (Agent chỉnh cho khớp dự án, không áp dụng máy móc)

### 4.1 `docker-compose.prod.yml`

```yaml
x-backend-env: &backend-env
  DATABASE_URL: postgresql+asyncpg://${POSTGRES_USER:?}:${POSTGRES_PASSWORD:?}@db:5432/${POSTGRES_DB:?}
  REDIS_URL: redis://:${REDIS_PASSWORD:?}@redis:6379/0
  CELERY_BROKER_URL: redis://:${REDIS_PASSWORD}@redis:6379/1
  CELERY_RESULT_BACKEND: redis://:${REDIS_PASSWORD}@redis:6379/1
  JWT_SECRET_KEY: ${JWT_SECRET_KEY:?set JWT_SECRET_KEY in .env}
  DEBUG: "false"
  CORS_ORIGINS: ${CORS_ORIGINS:?set CORS_ORIGINS in .env}
  API_PUBLIC_URL: ${API_PUBLIC_URL:?set API_PUBLIC_URL in .env}
  STOCKFISH_PATH: /usr/games/stockfish
  ALLOW_PUBLIC_REGISTER: ${ALLOW_PUBLIC_REGISTER:-false}

services:
  db:
    image: postgres:16-alpine
    restart: unless-stopped
    environment:
      POSTGRES_USER: ${POSTGRES_USER:?}
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD:?}
      POSTGRES_DB: ${POSTGRES_DB:?}
    volumes:
      - postgres_data:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U $${POSTGRES_USER} -d $${POSTGRES_DB}"]
      interval: 10s
      timeout: 5s
      retries: 10

  redis:
    image: redis:7-alpine
    restart: unless-stopped
    command: ["redis-server", "--requirepass", "${REDIS_PASSWORD:?}"]
    volumes:
      - redis_data:/data
    healthcheck:
      test: ["CMD-SHELL", "redis-cli -a $${REDIS_PASSWORD} ping | grep PONG"]
      interval: 10s
      timeout: 5s
      retries: 10
    environment:
      REDIS_PASSWORD: ${REDIS_PASSWORD:?}

  backend:
    build:
      context: ./backend
      dockerfile: Dockerfile
    restart: unless-stopped
    environment: *backend-env
    expose: ["8000"]
    volumes:
      - scans_data:/app/storage/scans   # Agent xác nhận đường dẫn lưu thật
    depends_on:
      db: { condition: service_healthy }
      redis: { condition: service_healthy }
    command: ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000",
              "--proxy-headers", "--forwarded-allow-ips", "*"]

  worker:
    build:
      context: ./backend
      dockerfile: Dockerfile
    restart: unless-stopped
    environment: *backend-env
    volumes:
      - scans_data:/app/storage/scans
    depends_on:
      db: { condition: service_healthy }
      redis: { condition: service_healthy }
    command: ["celery", "-A", "app.core.celery_app", "worker", "--loglevel=info", "--concurrency=1"]

  beat:
    build:
      context: ./backend
      dockerfile: Dockerfile
    restart: unless-stopped
    environment: *backend-env
    depends_on:
      db: { condition: service_healthy }
      redis: { condition: service_healthy }
    command: ["celery", "-A", "app.core.celery_app", "beat", "--loglevel=info"]

  web:
    build:
      context: .
      dockerfile: frontend/Dockerfile.prod
      args:
        VITE_API_URL: /api
    restart: unless-stopped
    environment:
      SITE_ADDRESS: ${SITE_ADDRESS:?set SITE_ADDRESS in .env}
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - caddy_data:/data
      - caddy_config:/config
    depends_on:
      - backend

volumes:
  postgres_data:
  redis_data:
  scans_data:
  caddy_data:
  caddy_config:
```

### 4.2 `frontend/Dockerfile.prod` (ngữ cảnh build là thư mục gốc repo)

```dockerfile
FROM node:20-alpine AS build
WORKDIR /app
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci
COPY frontend/ ./
ARG VITE_API_URL=/api
ENV VITE_API_URL=$VITE_API_URL
RUN npm run build

FROM caddy:2-alpine
COPY --from=build /app/dist /srv
COPY deploy/Caddyfile /etc/caddy/Caddyfile
```

### 4.3 `deploy/Caddyfile`

```
{$SITE_ADDRESS} {
    encode gzip

    handle /api/* {
        reverse_proxy backend:8000
    }

    # TODO (Agent): thay bằng đường dẫn WebSocket thật của backend, ví dụ /ws/*
    handle /ws/* {
        reverse_proxy backend:8000
    }

    handle {
        root * /srv
        try_files {path} /index.html
        file_server
    }

    header {
        X-Content-Type-Options nosniff
        X-Frame-Options DENY
        Referrer-Policy strict-origin-when-cross-origin
    }
}
```

Lưu ý: nếu dùng địa chỉ IP thay vì tên miền, đặt `SITE_ADDRESS=:80` (chỉ HTTP, không có HTTPS tự động). Nếu cần giới hạn IP người truy cập, thêm khối `@blocked not remote_ip <danh sách>` và `respond @blocked 403`.

### 4.4 `.dockerignore`

Gốc repo:
```
.git
**/node_modules
**/dist
.env
backend/storage
backups
```
`backend/.dockerignore`:
```
storage
__pycache__
*.pyc
.env
```

### 4.5 `.env.example` (mẫu mới, giá trị bí mật để trống)

```
# --- Bắt buộc, không có mặc định (chỉ dùng ký tự chữ-số/hex cho mật khẩu để không phá chuỗi kết nối) ---
POSTGRES_USER=cams_user
POSTGRES_PASSWORD=
POSTGRES_DB=cams_db
REDIS_PASSWORD=
JWT_SECRET_KEY=

# --- Môi trường chạy thật ---
SITE_ADDRESS=cams.example.org
API_PUBLIC_URL=https://cams.example.org
CORS_ORIGINS=["https://cams.example.org"]
ALLOW_PUBLIC_REGISTER=false
DEBUG=false

# --- Tùy chọn (chỉ cần khi đưa vào environment của compose) ---
GOOGLE_CLIENT_ID=
GOOGLE_CLIENT_SECRET=
FACEBOOK_CLIENT_ID=
FACEBOOK_CLIENT_SECRET=
```

---

## 5. Tiêu chí nghiệm thu

**Bảo mật**
- [ ] Gọi trực tiếp `POST /api/auth/register` với `role=super_admin` và `center_id` tùy ý: tài khoản tạo ra luôn là `student`, `center_id=NULL`.
- [ ] `ALLOW_PUBLIC_REGISTER=false`: đăng ký trả 403, giao diện không còn liên kết đăng ký, đăng nhập Google/Facebook bằng email mới không tạo user.
- [ ] Khởi động với `DEBUG=false` và `JWT_SECRET_KEY` rỗng/mẫu bị từ chối.
- [ ] Không có chỗ nào trong log, báo cáo, commit chứa mật khẩu, hash hay giá trị `.env`.

**Tài khoản**
- [ ] `create_center.py` và `create_user.py` hoạt động, đăng nhập được bằng tài khoản vừa tạo; chạy lại với email đã có báo lỗi; mật khẩu tự sinh chỉ in một lần.

**Đóng gói**
- [ ] `docker compose -f docker-compose.prod.yml config` hợp lệ (có `.env` mẫu điền giá trị giả).
- [ ] `docker compose -f docker-compose.prod.yml up -d --build` chạy được ở local, truy cập qua `http://localhost` (đặt `SITE_ADDRESS=:80`): đăng nhập, tải trang sâu bằng F5, gọi API qua `/api`, WebSocket giải đấu hoạt động.
- [ ] Không có cổng nào của `db`, `redis`, `backend` được publish ra máy chủ; chỉ `web` mở 80/443.
- [ ] `/docs` và `/redoc` không truy cập được qua `web`.
- [ ] Dữ liệu quét/PDF nằm trong named volume và còn nguyên sau `docker compose down && up`.

**Stockfish và Arm**
- [ ] Báo phiên bản Stockfish trong container; không còn tiến trình Stockfish sót sau luồng chấm bài.
- [ ] Báo thời gian chấm làm mốc; báo danh sách gói Python không có wheel Arm (nếu có); ghi rõ nếu chưa kiểm tra trên Arm.

---

## 6. Báo cáo cuối mỗi nhóm việc

File đã tạo/sửa, test đã chạy (pass/fail), điểm mâu thuẫn với code hiện có, các giả định, và những việc **chưa** kiểm tra được ở local (đặc biệt là Arm). Không kèm bí mật.

---

## 7. Ngoài phạm vi (không làm ở Phase 0)

- Phân quyền đa trung tâm, quản lý người dùng bằng giao diện, phụ huynh, giới hạn dữ liệu theo trung tâm.
- Thay đổi quy trình bài tập hoặc chấm điểm (đã có spec riêng).
- Cấu hình máy chủ Oracle, DNS và chứng chỉ (làm thủ công ở bước sau, theo hướng dẫn riêng).
