# PROJECT_CONTEXT.md — Chess Academy Management System (CAMS)

> **Phiên bản tài liệu:** 1.0  
> **Ngày tạo:** 2026-10-15  
> **Trạng thái dự án:** Đang phát triển (v1.5 active)  
> **Mô tả:** Tài liệu kỹ thuật tổng hợp toàn bộ thông số dự án CAMS — sinh ra từ việc quét tự động toàn bộ codebase.

---

## 1. Tổng quan dự án

**CAMS** (Chess Academy Management System) là nền tảng quản lý học viện cờ vua trực tuyến, số hoá toàn bộ hoạt động của trung tâm dạy cờ: quản lý lớp học, AI quét bài tập từ PDF, luyện tập puzzle tương tác, chấm điểm tự động, thanh toán học phí, và tổ chức giải đấu online.

### 1.1 Lộ trình phiên bản

| Phiên bản | Timeline | Tính năng chính |
|-----------|----------|-----------------|
| **v1.0 MVP** | Sprint 0–4 (tuần 1–12) | Auth (email + Google + Facebook), Lớp học, AI Scanner, Luyện tập, Chấm điểm AI & thủ công, ELO |
| **v1.5** | Sprint 5–6 (tuần 13–16) | Thanh toán Level 1 (VietQR + Admin confirm), Giải đấu online |
| **v2.0** | Sprint 7–8 (tuần 17–20) | Mobile App iOS/Android, Push Notifications, Offline cache |
| **v2.5** | Q1 2027 | Multi-center SaaS, Super Admin, Thanh toán Level 2 (Webhook) |
| **v3.0** | Q2 2027 | AI Coach, Lichess/Chess.com sync, Thanh toán Level 3 (VNPay/MoMo đầy đủ) |
| **v3.5** | Q3 2027 | Video lesson management, Live streaming giải đấu |

---

## 2. Cấu trúc thư mục dự án

```
chess_academy/
├── .agents/                    # CAMS Orchestration System config
│   ├── agents/                 # Specialist agent definitions
│   ├── context/                # Agent context packages
│   ├── handoff/                # Session handoff checkpoints
│   ├── rules/                  # Orchestration policy rules
│   ├── skills/                 # Agent skill modules
│   └── state/                  # Task Ledger JSON files
├── backend/                    # FastAPI Python backend
│   ├── app/
│   │   ├── api/
│   │   │   ├── access.py       # Resource access guards
│   │   │   ├── api.py          # APIRouter assembly
│   │   │   ├── deps.py         # FastAPI dependencies (auth, db)
│   │   │   └── endpoints/      # 15 endpoint modules
│   │   ├── core/
│   │   │   ├── celery_app.py   # Celery factory
│   │   │   ├── config.py       # Pydantic Settings
│   │   │   ├── database.py     # SQLAlchemy async engine
│   │   │   ├── permissions.py  # RBAC helpers
│   │   │   └── security.py     # JWT, hashing
│   │   ├── models/             # 13 SQLAlchemy ORM models
│   │   ├── schemas/            # Pydantic request/response schemas
│   │   ├── services/           # Business logic layer (18 services)
│   │   ├── websocket/
│   │   │   └── game_handler.py # WebSocket live chess game
│   │   ├── main.py             # FastAPI app entry point
│   │   ├── tasks.py            # Celery periodic tasks
│   │   └── tasks_scan.py       # AI Scanner async tasks
│   ├── alembic/                # Database migrations
│   │   └── versions/           # 12 migration files
│   ├── models/                 # YOLO model files (AI)
│   ├── storage/                # Scan result storage
│   ├── uploads/                # User uploads (avatars)
│   ├── Dockerfile
│   └── requirements.txt
├── frontend/                   # React + Vite + TypeScript web admin
│   └── src/
│       ├── components/         # 6 reusable components
│       ├── pages/              # 20 page components
│       ├── services/           # API client services
│       ├── store/              # Zustand state stores
│       └── lib/                # Utilities
├── mobile/                     # React Native (Expo) mobile app
│   ├── app/                    # Expo Router screens
│   ├── lib/                    # Shared utilities
│   └── store/                  # Zustand mobile stores
├── docs/
│   ├── 01-sdlc/                # Requirements, Sprint Plan, Testing
│   ├── 02-architecture/        # System Design, AI Scanner, Payment, Tournament
│   └── 03-operations/          # Deployment, Maintenance
├── docker-compose.yml          # 6-service container orchestration
├── .env.example                # Environment template
└── README.md
```

---

## 3. Tech Stack

| Layer | Công nghệ | Phiên bản |
|-------|-----------|-----------|
| **Backend API** | Python / FastAPI | 0.115.x |
| **ASGI Server** | Uvicorn | 0.32.x |
| **Frontend Web** | React + Vite + TypeScript | React 19, Vite 8, TS 6 |
| **Mobile** | React Native + Expo Router | RN 0.86.3, Expo 57 |
| **Database** | PostgreSQL | 16 (Alpine) |
| **ORM** | SQLAlchemy (async) | 2.0.x |
| **Migrations** | Alembic | 1.14.x |
| **Cache & Queue** | Redis | 7 (Alpine) |
| **Task Queue** | Celery | 5.4.x |
| **Auth** | python-jose (JWT) + passlib (bcrypt) | HS256 |
| **OAuth** | Authlib (Google, Facebook) | 1.4.x |
| **Chess Engine** | Stockfish + python-chess | 1.999.x |
| **AI / Computer Vision** | YOLOv8 (Ultralytics) + OpenCV | 8.3.x / 4.10.x |
| **PDF Processing** | PyMuPDF | 1.25.x |
| **Payment** | VietQR / PayOS / VNPay / MoMo | — |
| **Push Notify** | Firebase FCM | @react-native-firebase 26.x |
| **Container** | Docker + Docker Compose | — |
| **State (Frontend)** | Zustand | 5.0.x |
| **HTTP Client (FE)** | Axios + TanStack Query | 1.20.x / 5.104.x |
| **Routing (FE)** | react-router-dom | 7.x |
| **Chess UI (FE)** | react-chessboard + chess.js | 5.12.x / 1.4.x |
| **Charts (FE)** | Recharts | 3.10.x |
| **Real-time (FE)** | socket.io-client | 4.8.x |

---

## 4. Infrastructure & Cấu hình

### 4.1 Docker Compose Services

| Service | Image/Build | Port | Mô tả |
|---------|------------|------|-------|
| `db` | postgres:16-alpine | — (internal) | PostgreSQL database |
| `redis` | redis:7-alpine | — (internal) | Cache & broker, requires password |
| `backend` | ./backend Dockerfile | 8000:8000 | FastAPI + Uvicorn (--reload) |
| `worker` | ./backend Dockerfile | — | Celery worker |
| `beat` | ./backend Dockerfile | — | Celery beat scheduler |
| `frontend` | node:20-alpine | 3000:3000 | Vite dev server |

> ⚠️ PostgreSQL và Redis KHÔNG expose port ra ngoài — chỉ truy cập nội bộ trong Docker network.

### 4.2 Environment Variables

| Biến | Mô tả | Default |
|------|-------|---------|
| `POSTGRES_USER` | DB username | `cams_user` |
| `POSTGRES_PASSWORD` | DB password | *(bắt buộc điền)* |
| `POSTGRES_DB` | DB name | `cams_db` |
| `REDIS_PASSWORD` | Redis password (hex-only) | *(bắt buộc điền)* |
| `JWT_SECRET_KEY` | JWT signing key (≥32 chars) | *(bắt buộc điền)* |
| `JWT_ALGORITHM` | JWT algorithm | `HS256` |
| `JWT_ACCESS_TOKEN_EXPIRE_MINUTES` | Access token TTL | `30` |
| `JWT_REFRESH_TOKEN_EXPIRE_DAYS` | Refresh token TTL | `7` |
| `CORS_ORIGINS` | Allowed origins (JSON array) | `["http://localhost:3000","http://localhost:5173"]` |
| `API_PUBLIC_URL` | Public API URL | `http://localhost:8000` |
| `DEBUG` | Debug mode | `false` |
| `ALLOW_PUBLIC_REGISTER` | Public self-registration | `false` |
| `GOOGLE_CLIENT_ID` | Google OAuth Client ID | *(optional)* |
| `GOOGLE_CLIENT_SECRET` | Google OAuth Secret | *(optional)* |
| `FACEBOOK_CLIENT_ID` | Facebook OAuth Client ID | *(optional)* |
| `FACEBOOK_CLIENT_SECRET` | Facebook OAuth Secret | *(optional)* |
| `STOCKFISH_PATH` | Stockfish binary path | `/usr/games/stockfish` |
| `PAYOS_CLIENT_ID` | PayOS Client ID | *(optional)* |
| `PAYOS_API_KEY` | PayOS API Key | *(optional)* |
| `PAYOS_CHECKSUM_KEY` | PayOS Checksum Key | *(optional)* |
| `VIETQR_BANK_ID` | VietQR Bank ID | `MB` |
| `VIETQR_ACCOUNT_NO` | VietQR Account Number | `1234567890` |
| `VIETQR_ACCOUNT_NAME` | VietQR Account Name | `CAMS CHESS ACADEMY` |
| `DATABASE_URL` | Full DB connection string | `postgresql+asyncpg://...` |
| `REDIS_URL` | Redis URL (DB 0) | `redis://:pass@redis:6379/0` |
| `CELERY_BROKER_URL` | Celery broker (DB 1) | `redis://:pass@redis:6379/1` |
| `CELERY_RESULT_BACKEND` | Celery result backend | `redis://:pass@redis:6379/1` |

> **Security Guard:** Ở production (DEBUG=false), app từ chối khởi động nếu JWT_SECRET_KEY < 32 chars, CORS chứa `"*"`, hoặc DATABASE_URL chứa default password.

---

## 5. Database Schema

### 5.1 Danh sách bảng (25 bảng)

| Bảng | Model File | Mô tả |
|------|-----------|-------|
| `centers` | center.py | Trung tâm dạy cờ (SaaS tenant root) |
| `branches` | center.py | Chi nhánh của trung tâm |
| `users` | user.py | Người dùng (mọi role) |
| `parent_student` | user.py | Association: phụ huynh ↔ học sinh |
| `classes` | class_.py | Lớp học |
| `class_enrollments` | class_.py | Đăng ký lớp học |
| `puzzles` | puzzle.py | Bài tập cờ vua |
| `puzzle_solutions` | puzzle.py | Lời giải puzzle (cây biến thể phẳng) |
| `assignments` | assignment.py | Bài tập được giao cho lớp |
| `assignment_submissions` | assignment.py | Nộp bài của học sinh |
| `student_progress` | progress.py | Tiến trình giải puzzle |
| `student_attempts` | progress.py | Chi tiết từng lần làm bài |
| `scan_jobs` | scan.py | Công việc quét PDF |
| `scan_results` | scan.py | Kết quả quét từng bàn cờ |
| `fee_plans` | payment.py | Gói học phí |
| `invoices` | payment.py | Hóa đơn học phí |
| `payments` | payment.py | Giao dịch thanh toán |
| `payment_webhook_logs` | payment.py | Audit log webhook |
| `tournaments` | tournament.py | Giải đấu cờ vua |
| `tournament_participants` | tournament.py | Người tham gia giải đấu |
| `tournament_games` | tournament.py | Ván đấu trong giải |
| `tournament_standings` | tournament.py | Bảng xếp hạng giải đấu |
| `notifications` | notification.py | Thông báo in-app |
| `catalog_items` | settings.py | Danh mục động (lookup tables) |
| `settings` | settings.py | Cấu hình hệ thống theo center |

### 5.2 Chi tiết schema chính

#### `centers`
```
id UUID PK, name VARCHAR(200) NOT NULL, address TEXT,
logo_url VARCHAR(500), phone VARCHAR(20), email VARCHAR(200),
facebook_page_url VARCHAR(500),
subscription_plan VARCHAR(20) CHECK(free|basic|premium),
created_at TIMESTAMPTZ, updated_at TIMESTAMPTZ
```

#### `users`
```
id UUID PK, center_id UUID→centers, primary_branch_id UUID→branches,
email VARCHAR(200) UNIQUE NOT NULL, password_hash VARCHAR(255),
full_name VARCHAR(200) NOT NULL, avatar_url VARCHAR(500),
role VARCHAR(20) NOT NULL CHECK(super_admin|center_admin|admin|teacher|student|parent),
date_of_birth DATE, phone VARCHAR(20), elo_rating INT default=800,
is_active BOOL default=true, google_id VARCHAR(200), facebook_id VARCHAR(200),
username VARCHAR(100) UNIQUE, bio VARCHAR(500),
location VARCHAR(200), country VARCHAR(100), language VARCHAR(50), timezone VARCHAR(100),
last_login TIMESTAMPTZ, created_at TIMESTAMPTZ, updated_at TIMESTAMPTZ
```

#### `classes`
```
id UUID PK, center_id UUID→centers, branch_id UUID→branches,
teacher_id UUID→users, name VARCHAR(200) NOT NULL,
level VARCHAR(20) CHECK(beginner|intermediate|advanced|expert),
max_students INT default=30, schedule_json JSONB, is_active BOOL
```

#### `puzzles`
```
id UUID PK, center_id UUID→centers, created_by UUID→users,
title VARCHAR(300) NOT NULL, description TEXT, fen VARCHAR(200) NOT NULL, pgn TEXT,
difficulty VARCHAR(20) CHECK(easy|medium|hard|expert),
puzzle_type VARCHAR(20) CHECK(tactic|endgame|opening|strategy|custom|mate_in_1..4),
source VARCHAR(20) CHECK(manual_fen|manual_pgn|ai_scanned|imported),
tags VARCHAR[], rating INT default=1200, play_count INT, success_rate INT,
solution_tree JSONB, mate_in INT, solution_verified BOOL,
solution_verified_at TIMESTAMPTZ, verification_error TEXT, board_image_url VARCHAR(500)
```

#### `scan_jobs`
```
id UUID PK, center_id UUID→centers NOT NULL, uploaded_by UUID→users NOT NULL,
file_name VARCHAR(500), file_url VARCHAR(500), file_size INT, total_pages INT,
boards_found INT default=0, boards_approved INT,
status VARCHAR(20) CHECK(pending|processing|completed|failed),
error_message TEXT, processing_time_ms INT
```

#### `scan_results`
```
id UUID PK, job_id UUID→scan_jobs NOT NULL,
page_number INT NOT NULL, board_index INT NOT NULL,
board_image_url VARCHAR(500), bounding_box JSONB, confidence_board NUMERIC(4,2),
fen_candidate VARCHAR(200), fen_final VARCHAR(200),
side_to_move VARCHAR(1) default='w', castling_rights VARCHAR(4) default='-',
en_passant VARCHAR(2) default='-', cell_confidence JSONB,
review_status VARCHAR(20) CHECK(pending|approved|corrected|rejected|auto_approved),
reviewed_by UUID→users, reviewed_at TIMESTAMPTZ, puzzle_id UUID→puzzles
UNIQUE(job_id, page_number, board_index)
```

#### `payments`
```
id UUID PK, invoice_id UUID→invoices, payer_id UUID→users,
amount NUMERIC(12,2) NOT NULL, currency VARCHAR(3) default='VND',
payment_method VARCHAR(20) CHECK(bank_transfer|cash|card|ewallet),
payment_provider VARCHAR(20) CHECK(vietqr|payos|vnpay|momo|zalopay),
payment_level VARCHAR(20) CHECK(level1_manual|level2_webhook|level3_gateway),
status VARCHAR(20) CHECK(pending|success|failed|refunded),
transaction_id VARCHAR(200), provider_order_id VARCHAR(200),
provider_transaction_id VARCHAR(200), payment_link_id VARCHAR(200),
idempotency_key VARCHAR(200) UNIQUE, signature_verified BOOL,
payment_data JSONB, paid_at TIMESTAMPTZ, confirmed_by UUID→users
UNIQUE(payment_provider, provider_transaction_id)
```

#### `tournaments`
```
id UUID PK, center_id UUID→centers (nullable), created_by UUID→users NOT NULL,
name VARCHAR(300) NOT NULL, description TEXT,
format VARCHAR(20) CHECK(swiss|round_robin|elimination) default='swiss',
max_rounds INT default=5, time_control VARCHAR(50),
status VARCHAR(20) CHECK(draft|registration|in_progress|completed|cancelled),
start_date TIMESTAMPTZ, end_date TIMESTAMPTZ
```

### 5.3 Enum Catalog (22 enums)

| Enum | Values |
|------|--------|
| `UserRole` | super_admin, center_admin, admin, teacher, student, parent |
| `SubscriptionPlan` | free, basic, premium |
| `ClassLevel` | beginner, intermediate, advanced, expert |
| `EnrollmentStatus` | active, inactive, graduated |
| `PuzzleDifficulty` | easy, medium, hard, expert |
| `PuzzleType` | tactic, endgame, opening, strategy, custom, mate_in_1, mate_in_2, mate_in_3, mate_in_4 |
| `PuzzleSource` | manual_fen, manual_pgn, ai_scanned, imported |
| `ProgressStatus` | not_started, in_progress, solved, failed |
| `GradingMethod` | auto_ai, manual_teacher |
| `SubmissionStatus` | not_started, in_progress, submitted, graded, returned, reopened |
| `PaymentMethod` | bank_transfer, cash, card, ewallet |
| `PaymentProvider` | vietqr, payos, vnpay, momo, zalopay |
| `PaymentLevel` | level1_manual, level2_webhook, level3_gateway |
| `PaymentStatus` | pending, success, failed, refunded |
| `InvoiceStatus` | draft, sent, paid, overdue, cancelled |
| `ScanStatus` | pending, processing, completed, failed |
| `ReviewStatus` | pending, approved, corrected, rejected, auto_approved |
| `TournamentStatus` | draft, registration, in_progress, completed, cancelled |
| `TournamentFormat` | swiss, round_robin, elimination |
| `GameResult` | white_wins, black_wins, draw, not_played |
| `NotificationType` | assignment, grade, payment, tournament, system |
| `BillingCycle` | monthly, quarterly, semester, yearly |

> **Enum strategy:** VARCHAR + CheckConstraint (không dùng native PostgreSQL ENUM vì khó ALTER sau này).

### 5.4 Database Migrations (Alembic — 12 files)

| Migration ID | Mô tả |
|-------------|-------|
| `5f6672803b73` | init_tables — toàn bộ schema ban đầu |
| `c3a7f1b9d204` | add_solution_tree — JSONB cho puzzle |
| `8ffac1c45756` | add_payment_models |
| `949b33e5949a` | add_tournament_models |
| `70eeb8de89e6` | make_tournament_center_id_nullable |
| `4b2c1d9e8f7a` | add_center_admin_role |
| `d726207be4a1` | add_profile_fields_to_user |
| `f920da3e1b23` | add_assignment_submissions |
| `3a1f8b7c4d2e` | add_submission_attempt_and_version |
| `e819fa2c4d11` | add_unique_index_student_progress |
| `28f9f6aa55d2` | add_grading_fields_to_submissions |
| `5c3d2e1f0a9b` | add_settings_and_catalogs |

---

## 6. Backend API Routes

**Base URL:** `http://localhost:8000`  
**API Prefix:** `/api`  
**Swagger UI:** `http://localhost:8000/docs`

### 6.1 Router Registry

| Prefix | Tags | File |
|--------|------|------|
| `/api/auth` | auth | `endpoints/auth.py` |
| `/api/users` | users | `endpoints/users.py` |
| `/api/classes` | classes | `endpoints/classes.py` |
| `/api/scan` | scan | `endpoints/scan.py` |
| `/api/puzzles` | puzzles | `endpoints/puzzles.py` |
| `/api/assignments` | assignments | `endpoints/assignments.py` |
| `/api/progress` | progress | `endpoints/progress.py` |
| `/api/leaderboard` | leaderboard | `endpoints/leaderboard.py` |
| `/api/fee-plans` | fee-plans | `endpoints/fee_plans.py` |
| `/api/invoices` | invoices | `endpoints/invoices.py` |
| `/api/payments` | payments | `endpoints/payments.py` |
| `/api/tournaments` | tournaments | `endpoints/tournaments.py` |
| `/api/files` | files | `endpoints/files.py` |
| `/api/settings` | settings | `endpoints/settings.py` |
| `/api/catalogs` | catalogs | `endpoints/settings.py` |

### 6.2 Auth (`/api/auth`)

| Method | Path | Auth | Mô tả |
|--------|------|------|-------|
| GET | `/config` | No | Trả về auth capabilities |
| POST | `/register` | No | Public self-registration (nếu bật) |
| POST | `/login` | No | Email+password → JWT |
| POST | `/refresh` | Refresh token | Refresh access token |
| POST | `/google` | Google ID token | Google OAuth |
| POST | `/facebook` | Facebook access token | Facebook OAuth |
| GET | `/me` | Bearer JWT | Get current user |

### 6.3 Users (`/api/users`)

| Method | Path | Role | Mô tả |
|--------|------|------|-------|
| PUT | `/me` | Any | Update own profile |
| POST | `/me/avatar` | Any | Upload avatar |
| GET | `/` | Admin+ | List users |
| POST | `/` | center_admin+ | Create user |
| GET | `/{user_id}` | Admin / Self | User detail |
| PUT | `/{user_id}` | center_admin+ | Update user |
| DELETE | `/{user_id}` | center_admin+ | Delete user |
| POST | `/{user_id}/link-parent` | center_admin+ | Link parent ↔ student |
| DELETE | `/{user_id}/unlink-parent/{parent_id}` | center_admin+ | Unlink parent |

### 6.4 Classes (`/api/classes`)

| Method | Path | Mô tả |
|--------|------|-------|
| GET | `/` | List classes |
| POST | `/` | Create class |
| GET | `/{class_id}` | Class detail |
| PUT | `/{class_id}` | Update class |
| DELETE | `/{class_id}` | Delete class |
| POST | `/{class_id}/enroll` | Enroll student |
| DELETE | `/{class_id}/enrollments/{student_id}` | Unenroll student |
| GET | `/{class_id}/students` | List enrolled students |

### 6.5 Scan (`/api/scan`)

| Method | Path | Mô tả |
|--------|------|-------|
| POST | `/upload` | Upload PDF → queue Celery job |
| GET | `/jobs` | List scan jobs |
| GET | `/jobs/{job_id}` | Job detail + results |
| GET | `/jobs/{job_id}/results` | Results only |
| PUT | `/results/{result_id}/review` | Teacher corrects FEN |
| POST | `/results/{result_id}/approve` | Approve → create puzzle |
| DELETE | `/jobs/{job_id}` | Delete scan job |

**Upload constraints:** Max 50MB, MIME = `application/pdf`, magic bytes `%PDF-` verified.

### 6.6 Puzzles (`/api/puzzles`)

| Method | Path | Mô tả |
|--------|------|-------|
| GET | `/` | List puzzles (filter: type, difficulty, source) |
| POST | `/` | Create puzzle manually |
| GET | `/{puzzle_id}` | Puzzle detail |
| PUT | `/{puzzle_id}` | Update puzzle |
| DELETE | `/{puzzle_id}` | Delete puzzle |
| POST | `/{puzzle_id}/solve` | Submit solution attempt |
| GET | `/{puzzle_id}/solution` | Get solution |
| POST | `/{puzzle_id}/verify-solution` | Trigger Stockfish verification |

### 6.7 Assignments (`/api/assignments`)

| Method | Path | Mô tả |
|--------|------|-------|
| GET | `/` | List assignments |
| POST | `/` | Create assignment |
| GET | `/{assignment_id}` | Assignment detail |
| PUT | `/{assignment_id}` | Update assignment |
| DELETE | `/{assignment_id}` | Delete assignment |
| GET | `/{assignment_id}/submissions` | List all submissions |
| GET | `/{assignment_id}/my-submission` | Student's own submission |
| POST | `/{assignment_id}/submit` | Submit assignment |
| POST | `/{assignment_id}/reopen/{student_id}` | Teacher reopens |
| POST | `/{assignment_id}/grade/{student_id}` | Grade submission |

### 6.8 Payment Flow

#### Fee Plans (`/api/fee-plans`)
| Method | Path | Mô tả |
|--------|------|-------|
| GET | `/` | List fee plans |
| POST | `/` | Create fee plan |
| PUT | `/{id}` | Update fee plan |
| DELETE | `/{id}` | Delete fee plan |

#### Invoices (`/api/invoices`)
| Method | Path | Mô tả |
|--------|------|-------|
| GET | `/` | List invoices |
| POST | `/` | Create invoice |
| GET | `/{id}` | Invoice detail |
| PUT | `/{id}/status` | Update invoice status |
| POST | `/{id}/generate-qr` | Generate VietQR QR code |

#### Payments (`/api/payments`)
| Method | Path | Mô tả |
|--------|------|-------|
| POST | `/confirm/{invoice_id}` | Admin manual confirm payment |
| POST | `/webhook` | Receive payment provider webhook |

### 6.9 Tournaments (`/api/tournaments`)

| Method | Path | Mô tả |
|--------|------|-------|
| GET | `/` | List tournaments |
| POST | `/` | Create tournament |
| GET | `/{id}` | Tournament detail |
| PUT | `/{id}` | Update tournament |
| POST | `/{id}/register` | Student registers |
| POST | `/{id}/start` | Start (generate pairings) |
| GET | `/{id}/pairings` | Current round pairings |
| PUT | `/{id}/games/{game_id}` | Record game result |
| GET | `/{id}/standings` | Tournament standings |

### 6.10 Utility Endpoints

| Method | Path | Mô tả |
|--------|------|-------|
| GET | `/api/progress` | Student progress history |
| POST | `/api/progress` | Update progress |
| GET | `/api/leaderboard` | ELO leaderboard |
| GET | `/api/files/{path}` | Serve file (HMAC-signed URL) |
| GET | `/api/settings` | Get system settings |
| PUT | `/api/settings/{key}` | Update setting |
| GET | `/api/catalogs/{type}` | Get catalog items |
| POST | `/api/catalogs` | Create catalog item |
| GET | `/` | Welcome message |
| GET | `/health` | Health check `{"status":"ok"}` |

### 6.11 WebSocket

| Path | Mô tả |
|------|-------|
| `WS /ws/game/{game_id}` | Live chess game (tournament) |

**Protocol:**
- Auth: `?token=<JWT>` query param
- Server→Client: `{"type":"game_state","fen":"...","history":[...]}`
- Client→Server: `{"type":"move","move":"e2e4"}`
- Server broadcast: `{"type":"move","move":"e2e4","fen":"...","san":"e4"}`

---

## 7. RBAC & Security

### 7.1 Role Hierarchy

```
super_admin          → Global access, tất cả centers
  └── center_admin   → Own center only (alias: "admin" backward compat)
        ├── teacher  → Own center, own classes
        ├── student  → Own data only
        └── parent   → Children's data only
```

### 7.2 Tenant Isolation Rules

1. `super_admin` có quyền truy cập toàn bộ centers
2. Mọi role khác bị giới hạn chặt trong `center_id` của họ
3. **Cross-center access → 404 NOT FOUND** (không phải 403) — tránh tenant enumeration
4. `scope_query_to_center()` bắt buộc áp WHERE clause cho mọi query

### 7.3 JWT Configuration

| Thông số | Giá trị |
|---------|---------|
| Algorithm | HS256 |
| Access token TTL | 30 phút |
| Refresh token TTL | 7 ngày |
| Header | `Authorization: Bearer <token>` |
| Payload | `{"sub": "<uuid>", "type": "access"\|"refresh"}` |

### 7.4 File Security

- Scan files **không** mount qua public static
- Serve qua `/api/files/...` với **HMAC-signed URL** (short-lived)
- Avatar serve qua `/static/avatars/` (public mount)

---

## 8. Background Tasks (Celery)

### 8.1 Registered Tasks

| Task | Trigger | Mô tả |
|------|---------|-------|
| `auto_submit_overdue_assignments` | Beat: mỗi 10 phút | Tự động nộp bài quá hạn |
| `process_scan_job` | Async sau upload PDF | Chạy AI pipeline |
| `health_check` | Manual | Test worker |

### 8.2 Celery Config

| Setting | Value |
|---------|-------|
| Timezone | Asia/Ho_Chi_Minh |
| Serializer | JSON |
| Prefetch multiplier | 1 |
| Acks late | True |
| Task tracking | Enabled |
| Broker DB | Redis DB 1 |
| Result DB | Redis DB 1 |

---

## 9. AI Scanner Pipeline

### Pipeline: PDF → FEN

```
1. PDF Upload (POST /api/scan/upload)
        ↓
2. pdf_service.py        — PyMuPDF: Extract pages → render PNG
        ↓
3. board_detector.py     — YOLOv8: Detect chess board bounding boxes
        ↓
4. board_rectifier.py    — OpenCV: Perspective correction, deskew
        ↓
5. piece_classifier.py   — YOLOv8: Classify pieces (64 cells/board)
        ↓
6. turn_detector.py      — Infer side to move (w/b)
        ↓
7. fen_builder.py        — Assemble + validate FEN string
        ↓
8. ScanResult (DB)       — Store fen_candidate + cell_confidence
        ↓
9. Human Review          — Teacher reviews/corrects via PUT /review
        ↓
10. Approve              — POST /approve → create Puzzle record
```

### Services summary

| Service | File | Size |
|---------|------|------|
| AI orchestrator | scan_service.py | 6KB |
| PDF extraction | pdf_service.py | 3.3KB |
| Board detection | board_detector.py | 6.8KB |
| Perspective fix | board_rectifier.py | 7.6KB |
| Piece classification | piece_classifier.py | 12KB |
| Turn detection | turn_detector.py | 3.6KB |
| FEN assembly | fen_builder.py | 6.6KB |
| Mate solver | mate_solver.py | **27.6KB** |
| File storage | storage_service.py | 3.5KB |

---

## 10. Frontend (Web Admin)

### 10.1 Stack

| | |
|-|-|
| Framework | React 19 + TypeScript 6 |
| Bundler | Vite 8 |
| Styling | TailwindCSS 4 |
| State | Zustand 5 |
| Server state | TanStack Query 5 |
| HTTP | Axios |
| Router | react-router-dom 7 |
| Chess UI | react-chessboard 5 + chess.js 1.4 |
| Real-time | socket.io-client 4.8 |
| Charts | Recharts 3.10 |
| Notifications | react-hot-toast 2.6 |

### 10.2 Frontend Routes (20 pages)

| Path | Component | Mô tả |
|------|-----------|-------|
| `/login` | Login.tsx | Đăng nhập |
| `/register` | Register.tsx | Đăng ký (nếu bật) |
| `/` | Dashboard.tsx | Trang chủ & thống kê |
| `/classes` | Classes.tsx | Danh sách lớp học |
| `/classes/:classId` | StudentList.tsx | Học sinh trong lớp |
| `/schedule` | Schedule.tsx | Lịch học |
| `/scanner` | Scanner.tsx | AI PDF Scanner |
| `/puzzles` | Puzzles.tsx | Quản lý puzzle |
| `/practice` | Practice.tsx | Luyện tập puzzle |
| `/assignments` | Assignments.tsx | Danh sách bài tập |
| `/assignments/:assignmentId` | AssignmentDetail.tsx | Chi tiết bài tập |
| `/leaderboard` | Leaderboard.tsx | Bảng xếp hạng ELO |
| `/fee-plans` | FeePlans.tsx | Gói học phí |
| `/invoices` | Invoices.tsx | Hóa đơn |
| `/tournaments` | Tournaments.tsx | Danh sách giải đấu |
| `/tournaments/:id` | TournamentDetail.tsx | Chi tiết giải đấu |
| `/tournaments/:id/game/:gameId` | LiveGame.tsx | Ván đấu trực tiếp |
| `/profile` | Profile.tsx | Hồ sơ cá nhân |
| `/members` | Members.tsx | Quản lý thành viên |
| `/settings` | Settings.tsx | Cấu hình hệ thống |

### 10.3 Components

| Component | Mô tả |
|-----------|-------|
| Sidebar.tsx | Navigation sidebar |
| AppLayout.tsx | Layout wrapper |
| PrivateRoute.tsx | Auth guard |
| ClassForm.tsx | Form tạo/sửa lớp |
| CreateTournamentModal.tsx | Modal tạo giải đấu |
| GenerateInvoiceModal.tsx | Modal tạo hóa đơn |

---

## 11. Mobile App (React Native + Expo)

### 11.1 Stack

| | |
|-|-|
| Framework | React Native 0.86.3 |
| Routing | Expo Router 57 (file-based) |
| Language | TypeScript 6 |
| State | Zustand 5 |
| HTTP | Axios |
| Chess | chess.js + react-native-chessboard |
| Real-time | socket.io-client |
| Push | expo-notifications + Firebase FCM |
| Storage | AsyncStorage |

### 11.2 Mobile Screens

| Screen | File | Mô tả |
|--------|------|-------|
| Root Layout | `app/_layout.tsx` | Navigation root |
| Home | `app/index.tsx` | Trang chủ |
| Login | `app/login.tsx` | Đăng nhập |
| Register | `app/register.tsx` | Đăng ký |

> Mobile ở giai đoạn v2.0 (Sprint 7-8), nhiều màn hình đang phát triển.

---

## 12. Services Layer (Backend)

| Service | File | Size | Mô tả |
|---------|------|------|-------|
| assignment_service | assignment_service.py | 19KB | Bài tập & nộp bài |
| board_detector | board_detector.py | 6.8KB | YOLO board detection |
| board_rectifier | board_rectifier.py | 7.6KB | OpenCV rectification |
| class_service | class_service.py | 11KB | Quản lý lớp học |
| fee_plan_service | fee_plan_service.py | 1.7KB | Gói học phí |
| fen_builder | fen_builder.py | 6.6KB | FEN assembly |
| invoice_service | invoice_service.py | 4.2KB | Hóa đơn |
| mate_solver | mate_solver.py | **27.6KB** | Giải chiếu hết (Stockfish) |
| payment/ | payment/ dir | — | Payment gateway integrations |
| pdf_service | pdf_service.py | 3.3KB | PDF extraction |
| piece_classifier | piece_classifier.py | 12KB | YOLO piece classification |
| progress_service | progress_service.py | 13KB | Tiến trình học sinh |
| puzzle_service | puzzle_service.py | **26KB** | Logic puzzle (lớn nhất) |
| scan_service | scan_service.py | 6KB | AI scan orchestrator |
| settings_service | settings_service.py | 10KB | System settings |
| stockfish_service | stockfish_service.py | 5.2KB | Stockfish wrapper |
| storage_service | storage_service.py | 3.5KB | File I/O + HMAC URL |
| tournament_service | tournament_service.py | 8.4KB | Pairing, standings |
| turn_detector | turn_detector.py | 3.6KB | Side-to-move |

---

## 13. Agent Orchestration System

### 13.1 Specialist Agents (12)

| Agent | Domain | Boundary |
|-------|--------|----------|
| cams-architect | System design, API contracts | Trước khi có thay đổi cross-domain |
| cams-backend | FastAPI endpoints, services | API/service logic |
| cams-database | Schema, migrations | DB changes |
| cams-ai-cv | AI Scanner: pixel → board-state thô | Không validate luật cờ |
| cams-chess | FEN/PGN validation, Stockfish, puzzle | Nhận từ AI-CV, validate luật cờ |
| cams-frontend | React, admin dashboard | Web UI |
| cams-mobile | React Native screens | Mobile UI |
| cams-qa | QA verification, integration tests | Release gate |
| cams-devops | Docker, deployment | Infra |
| cams-security | Auth, payment, data security | Security gate |
| cams-payment | Invoice, VietQR, payment state | Payment domain |
| cams-tournament | Tournament logic | Tournament domain |

### 13.2 Orchestration Pipeline

```
PHASE 0  INTAKE        → Làm rõ goal / scope / constraints
PHASE 1  CLASSIFY      → Gán loại task: RESEARCH/BUGFIX/FEATURE/REFACTOR/INFRA/REVIEW
PHASE 2  PLAN          → Routing matrix + dependency graph
PHASE 3  DELEGATE      → Invoke specialist với Context Packet
PHASE 4  VERIFY        → QA Gate, Security Gate
PHASE 5  INTEGRATE     → Merge kết quả, update Task Ledger
```

---

## 14. System Architecture Diagram

```
┌─────────────────────────────────────────────────────┐
│                     Clients                          │
│  [Browser]  ──── HTTP/HTTPS ────► [:3000 Frontend]  │
│  [Mobile]   ──── HTTP/HTTPS ────►                   │
│             ──── WebSocket ────► [:8000 Backend]    │
└─────────────────────────────────────────────────────┘
                          │
              ┌───────────┼───────────┐
              │           │           │
         PostgreSQL     Redis     Celery Workers
         (:5432)       (:6379)
         cams_db      DB0: app    - worker (AI scan)
                      DB1: celery - beat (periodic)
                      
Backend Internal Architecture:
  HTTP Request
    → FastAPI Router
    → Pydantic Schema (validation)
    → Service Layer (business logic)
    → SQLAlchemy ORM (async)
    → PostgreSQL

  POST /scan/upload
    → Celery Task Queue (Redis)
    → Worker picks up
    → pdf_service → board_detector → board_rectifier
    → piece_classifier → turn_detector → fen_builder
    → ScanResult saved to DB

  WebSocket /ws/game/{id}
    → ConnectionManager (in-memory)
    → chess.py (move validation)
    → Broadcast to all connections in game room
```

---

## 15. Development Quick Reference

### Khởi động local

```bash
# 1. Cấu hình môi trường
cp .env.example .env
# Điền POSTGRES_PASSWORD, REDIS_PASSWORD, JWT_SECRET_KEY

# 2. Khởi động stack
docker-compose up -d

# 3. Chạy migrations
docker exec cams_backend alembic upgrade head

# 4. Xem logs
docker-compose logs -f backend worker beat
```

### Endpoints quan trọng

| URL | Mô tả |
|-----|-------|
| http://localhost:8000/docs | Swagger UI (auto-generated) |
| http://localhost:8000/health | Health check |
| http://localhost:3000 | Frontend web |
| http://localhost:8000/api/auth/config | Auth config (public) |
| http://localhost:8000/api/auth/login | Login → JWT |

### Các lệnh hữu ích

```bash
# Tạo migration mới
docker exec cams_backend alembic revision --autogenerate -m "mô tả"

# Rollback migration
docker exec cams_backend alembic downgrade -1

# Xem trạng thái migrations
docker exec cams_backend alembic current

# Restart một service
docker-compose restart backend

# Chạy Celery task thủ công
docker exec cams_worker celery -A app.core.celery_app call app.tasks.health_check
```

---

## 16. Tài liệu tham khảo

| Tài liệu | Đường dẫn |
|----------|-----------|
| SDLC Overview | `docs/01-sdlc/SDLC.md` |
| Requirements | `docs/01-sdlc/01_requirements.md` |
| Sprint Plan | `docs/01-sdlc/03_sprint_plan.md` |
| Testing Strategy | `docs/01-sdlc/04_testing.md` |
| System Design | `docs/02-architecture/02_system_design.md` |
| AI Scanner Architecture | `docs/02-architecture/AI_SCANNER_ARCHITECTURE.md` |
| Payment Architecture | `docs/02-architecture/PAYMENT_ARCHITECTURE.md` |
| Tournament Architecture | `docs/02-architecture/TOURNAMENT_ARCHITECTURE.md` |

---

*Tài liệu này được sinh ra tự động bằng cách quét toàn bộ codebase vào ngày 2026-10-15.*  
*Cập nhật lại khi có thay đổi kiến trúc lớn (schema, API contract, tech stack).*
