# Giai đoạn 2: Thiết kế Hệ thống (System Design)

> **CAMS — Chess Academy Management System**
> Tài liệu con của [SDLC.md](./SDLC.md)

---

## 2.1 Kiến trúc Tổng thể

```
+----------------------------------------------------------+
|                      CLIENT LAYER                        |
|   [Web App: React/Vite]    [Mobile: React Native/Expo]   |
+---------------------------+------------------------------+
                            | HTTPS / WebSocket
+---------------------------v------------------------------+
|              API GATEWAY (Nginx / Traefik)               |
+----------+------------------+--------------------------+
           |                  |                 |
    +------v-----+   +--------v------+  +-------v-------+
    | REST API   |   | WebSocket     |  |  AI Service   |
    | (FastAPI)  |   | (Game Server) |  | (CV Pipeline) |
    +------+-----+   +--------+------+  +-------+-------+
           |                  |                 |
+----------v------------------v-----------------v--------+
|                    DATABASE LAYER                       |
|  [PostgreSQL 16]    [Redis 7]    [Local Storage]         |
+----------------------------------------------------------+
```

---

## 2.2 Database Schema (PostgreSQL)

### Nhóm 1: Hệ thống & Người dùng

```sql
centers (
  id                  UUID PRIMARY KEY,
  name                VARCHAR(200) NOT NULL,
  address             TEXT,
  logo_url            VARCHAR(500),
  phone               VARCHAR(20),
  email               VARCHAR(200),
  facebook_page_url   VARCHAR(500),            -- MỚI: Facebook Page trung tâm
  subscription_plan   ENUM('free','basic','premium') DEFAULT 'free',
  created_at          TIMESTAMP DEFAULT NOW()
)

branches (
  id              UUID PRIMARY KEY,
  center_id       UUID NOT NULL REFERENCES centers(id),
  name            VARCHAR(200) NOT NULL,
  address         TEXT,
  phone           VARCHAR(20),
  is_active       BOOLEAN DEFAULT true,
  created_at      TIMESTAMP DEFAULT NOW()
)

users (
  id              UUID PRIMARY KEY,
  center_id       UUID REFERENCES centers(id),
  primary_branch_id UUID REFERENCES branches(id),  -- Cơ sở chính (nullable)
  email           VARCHAR(200) UNIQUE NOT NULL,
  password_hash   VARCHAR(255),
  full_name       VARCHAR(200) NOT NULL,
  avatar_url      VARCHAR(500),
  role            ENUM('super_admin','admin','teacher','student','parent'),
  date_of_birth   DATE,
  phone           VARCHAR(20),
  elo_rating      INT DEFAULT 800,
  is_active       BOOLEAN DEFAULT true,
  google_id       VARCHAR(200),
  facebook_id     VARCHAR(200),                -- MỚI: Facebook OAuth
  created_at      TIMESTAMP DEFAULT NOW(),
  last_login      TIMESTAMP
)

parent_student (
  parent_id   UUID REFERENCES users(id),
  student_id  UUID REFERENCES users(id),
  PRIMARY KEY (parent_id, student_id)
)
```

### Nhóm 2: Lớp học

```sql
classes (
  id           UUID PRIMARY KEY,
  center_id    UUID REFERENCES centers(id),
  branch_id    UUID REFERENCES branches(id),   -- Cơ sở (nullable nếu trung tâm chỉ có 1 cơ sở)
  teacher_id   UUID REFERENCES users(id),
  name         VARCHAR(200) NOT NULL,
  level        ENUM('beginner','intermediate','advanced','expert'),
  max_students INT DEFAULT 30,
  schedule_json JSONB,                          -- {"mon": "18:00-19:30", "wed": "18:00-19:30"}
  is_active    BOOLEAN DEFAULT true,
  created_at   TIMESTAMP DEFAULT NOW()
)

class_enrollments (
  id          UUID PRIMARY KEY,
  class_id    UUID REFERENCES classes(id),
  student_id  UUID REFERENCES users(id),
  enrolled_at TIMESTAMP DEFAULT NOW(),
  status      ENUM('active','inactive','graduated') DEFAULT 'active'
)
```

### Nhóm 3: Bài Toán Cờ (Puzzle Library)

```sql
puzzles (
  id               UUID PRIMARY KEY,
  center_id        UUID REFERENCES centers(id),
  created_by       UUID REFERENCES users(id),
  title            VARCHAR(500),
  fen_position     VARCHAR(200) NOT NULL,
  side_to_move     CHAR(1) NOT NULL,            -- 'w' hoặc 'b'
  exercise_type    ENUM('tactical','endgame','opening','best_move','mate'),
  difficulty       ENUM('beginner','intermediate','advanced','expert'),
  tags             TEXT[],                       -- ['Checkmate','Tactic','Endgame']

  -- Nguồn gốc bài tập (MỚI)
  source_type      ENUM('pdf','pgn','fen','manual') NOT NULL,
  source_id        VARCHAR(200),                 -- ID của PGN game hoặc PDF file
  source_ply       INT,                          -- Nước thứ bao nhiêu trong game PGN

  -- Phân tích engine (MỚI)
  engine           VARCHAR(50) DEFAULT 'stockfish',
  engine_depth     INT DEFAULT 20,
  evaluation_before DECIMAL(6,2),               -- Đánh giá trước nước đi tốt nhất (centipawns)
  evaluation_after  DECIMAL(6,2),               -- Đánh giá sau nước đi tốt nhất

  is_public        BOOLEAN DEFAULT false,
  created_at       TIMESTAMP DEFAULT NOW(),
  updated_at       TIMESTAMP DEFAULT NOW()
)

-- Bảng lời giải (1 bài tập có thể có nhiều nước đi đúng) (MỚI)
puzzle_solutions (
  id          UUID PRIMARY KEY,
  puzzle_id   UUID REFERENCES puzzles(id) ON DELETE CASCADE,
  move_uci    VARCHAR(10) NOT NULL,             -- Ví dụ: "e2e4"
  move_san    VARCHAR(10) NOT NULL,             -- Ví dụ: "e4"
  rank        INT DEFAULT 1,                    -- 1 = best, 2 = second best, ...
  evaluation  DECIMAL(6,2),                     -- Centipawn evaluation sau nước đi này
  pv          TEXT                              -- Principal variation (chuỗi nước đi tiếp theo)
)

assignments (
  id           UUID PRIMARY KEY,
  class_id     UUID REFERENCES classes(id),
  student_id   UUID REFERENCES users(id),       -- NULL = cả lớp
  puzzle_id    UUID REFERENCES puzzles(id),
  assigned_by  UUID REFERENCES users(id),
  due_date     DATE,
  hint_allowed INT DEFAULT 3,
  created_at   TIMESTAMP DEFAULT NOW()
)

student_progress (
  id                 UUID PRIMARY KEY,
  student_id         UUID REFERENCES users(id),
  puzzle_id          UUID REFERENCES puzzles(id),
  assignment_id      UUID REFERENCES assignments(id),
  status             ENUM('not_started','in_progress','solved','failed') DEFAULT 'not_started',
  attempts           INT DEFAULT 0,
  hints_used         INT DEFAULT 0,
  time_spent_seconds INT DEFAULT 0,
  error_moves        TEXT[],

  -- Chấm điểm (MỚI)
  points_earned      INT DEFAULT 0,
  grading_method     ENUM('auto_ai','manual_teacher'),
  graded_by          UUID REFERENCES users(id), -- NULL nếu auto AI
  teacher_feedback   TEXT,                       -- Nhận xét của giáo viên
  graded_at          TIMESTAMP,

  solved_at          TIMESTAMP,
  created_at         TIMESTAMP DEFAULT NOW()
)

-- Chi tiết từng lần làm bài (replay nước đi)
student_attempts (
  id             UUID PRIMARY KEY,
  progress_id    UUID NOT NULL REFERENCES student_progress(id),
  attempt_no     INT NOT NULL,
  moves_uci      TEXT[],                        -- ['e2e4', 'g8f6', ...]
  moves_san      TEXT[],                        -- ['e4', 'Nf6', ...]
  pgn            TEXT,                          -- Full PGN notation
  is_correct     BOOLEAN,
  hint_used      BOOLEAN DEFAULT false,
  points_earned  INT DEFAULT 0,
  result         VARCHAR(30),                   -- 'correct','incorrect','timeout','abandoned'
  started_at     TIMESTAMP,
  completed_at   TIMESTAMP,
  UNIQUE(progress_id, attempt_no)
)
```

### Nhóm 4: Học phí & Thanh toán

```sql
fee_plans (
  id             UUID PRIMARY KEY,
  center_id      UUID REFERENCES centers(id),
  class_id       UUID REFERENCES classes(id),
  name           VARCHAR(200) NOT NULL,
  amount         DECIMAL(12,2) NOT NULL,
  currency       VARCHAR(3) DEFAULT 'VND',
  billing_cycle  ENUM('monthly','semester','course'),
  is_active      BOOLEAN DEFAULT true
)

invoices (
  id              UUID PRIMARY KEY,
  center_id       UUID REFERENCES centers(id),
  student_id      UUID REFERENCES users(id),
  fee_plan_id     UUID REFERENCES fee_plans(id),
  invoice_number  VARCHAR(50) UNIQUE NOT NULL,   -- Mã hóa đơn: INV-2026-001
  amount          DECIMAL(12,2) NOT NULL,
  due_date        DATE NOT NULL,
  status          ENUM('pending','paid','overdue','cancelled') DEFAULT 'pending',
  qr_code_url     VARCHAR(500),                  -- QR VietQR tĩnh
  issued_at       TIMESTAMP DEFAULT NOW(),
  paid_at         TIMESTAMP
)

payments (
  id                       UUID PRIMARY KEY,
  invoice_id               UUID REFERENCES invoices(id),
  payer_id                 UUID REFERENCES users(id),
  amount                   DECIMAL(12,2) NOT NULL,
  currency                 CHAR(3) DEFAULT 'VND',
  payment_method           ENUM('bank_transfer','cash','card','ewallet'),
  payment_provider         ENUM('vietqr','payos','vnpay','momo','zalopay'),
  payment_level            ENUM('level1_manual','level2_webhook','level3_gateway') DEFAULT 'level1_manual',
  transaction_id           VARCHAR(200),           -- ID giao dịch nội bộ CAMS
  provider_order_id        VARCHAR(200),           -- Order ID từ provider (PayOS, VNPay...)
  provider_transaction_id  VARCHAR(200),           -- Transaction ID từ provider
  payment_link_id          VARCHAR(200),           -- Payment link ID (PayOS)
  reference                VARCHAR(200),           -- Nội dung chuyển khoản
  idempotency_key          VARCHAR(200) UNIQUE,
  signature_verified       BOOLEAN DEFAULT false,
  status                   ENUM('pending','success','failed','refunded') DEFAULT 'pending',
  confirmed_by             UUID REFERENCES users(id),   -- Admin xác nhận (Level 1)
  payment_data             JSONB,                  -- Raw data từ cổng thanh toán
  paid_at                  TIMESTAMP,
  created_at               TIMESTAMP DEFAULT NOW(),
  updated_at               TIMESTAMP DEFAULT NOW(),
  UNIQUE(payment_provider, provider_transaction_id)
)

-- Audit trail: log tất cả webhook calls (kể cả duplicates, failures)
payment_webhook_logs (
  id                  UUID PRIMARY KEY,
  provider            VARCHAR(50) NOT NULL,
  raw_payload         JSONB NOT NULL,
  signature_verified  BOOLEAN,
  processing_result   VARCHAR(50),               -- 'success','duplicate','signature_failed','amount_mismatch'
  payment_id          UUID REFERENCES payments(id),
  created_at          TIMESTAMP DEFAULT NOW()
)
```

### Nhóm 5: Giải đấu

```sql
tournaments (
  id                      UUID PRIMARY KEY,
  center_id               UUID REFERENCES centers(id),
  created_by              UUID REFERENCES users(id),
  name                    VARCHAR(200) NOT NULL,
  format                  ENUM('swiss','round_robin','knockout'),
  time_control            VARCHAR(50),            -- "blitz_5+3", "rapid_15+10"
  max_participants        INT,
  rounds                  INT,
  registration_deadline   TIMESTAMP,
  start_time              TIMESTAMP,
  end_time                TIMESTAMP,
  status                  ENUM('draft','registration','ongoing','completed','cancelled') DEFAULT 'draft'
)

tournament_participants (
  id              UUID PRIMARY KEY,
  tournament_id   UUID REFERENCES tournaments(id),
  player_id       UUID REFERENCES users(id),
  seed_rating     INT,
  registered_at   TIMESTAMP DEFAULT NOW(),
  status          ENUM('registered','approved','withdrawn') DEFAULT 'registered'
)

tournament_games (
  id               UUID PRIMARY KEY,
  tournament_id    UUID REFERENCES tournaments(id),
  round            INT NOT NULL,
  white_player_id  UUID REFERENCES users(id),
  black_player_id  UUID REFERENCES users(id),
  result           ENUM('white_wins','black_wins','draw','not_played') DEFAULT 'not_played',
  pgn              TEXT,
  time_control     VARCHAR(50),
  scheduled_at     TIMESTAMP,
  played_at        TIMESTAMP
)

tournament_standings (
  id             UUID PRIMARY KEY,
  tournament_id  UUID REFERENCES tournaments(id),
  player_id      UUID REFERENCES users(id),
  rank           INT,
  points         DECIMAL(4,1) DEFAULT 0,
  wins           INT DEFAULT 0,
  draws          INT DEFAULT 0,
  losses         INT DEFAULT 0,
  elo_change     INT DEFAULT 0
)
```

### Nhóm 6: AI Scanner

```sql
scan_jobs (
  id              UUID PRIMARY KEY,
  uploaded_by     UUID REFERENCES users(id),
  center_id       UUID REFERENCES centers(id),
  pdf_url         VARCHAR(500) NOT NULL,
  total_pages     INT,
  processed_pages INT DEFAULT 0,
  status          ENUM('queued','processing','review_pending','completed','failed') DEFAULT 'queued',
  created_at      TIMESTAMP DEFAULT NOW(),
  completed_at    TIMESTAMP
)

scan_results (
  id               UUID PRIMARY KEY,
  job_id           UUID REFERENCES scan_jobs(id),
  page_number      INT NOT NULL,
  board_index      INT NOT NULL,
  board_image_url  VARCHAR(500),
  bounding_box     JSONB,                         -- {"x":125,"y":340,"width":820,"height":820}
  confidence_board DECIMAL(4,2),                  -- Confidence score nhận diện bàn cờ
  fen_candidate    VARCHAR(200),                  -- Board FEN do AI đề xuất (chỉ board placement)
  fen_final        VARCHAR(200),                  -- Full FEN sau khi giáo viên duyệt
  side_to_move     CHAR(1) DEFAULT 'w',           -- 'w' hoặc 'b' (từ context/teacher input)
  castling_rights  VARCHAR(4) DEFAULT '-',        -- 'KQkq', '-', 'Kq', etc.
  en_passant       VARCHAR(2) DEFAULT '-',        -- 'e3', '-', etc.
  cell_confidence  JSONB,                         -- {"a8":0.99,"b8":0.97,"d8":0.63,...}
  review_status    ENUM('pending','approved','corrected','rejected','auto_approved') DEFAULT 'pending',
  reviewed_by      UUID REFERENCES users(id),
  reviewed_at      TIMESTAMP,
  puzzle_id        UUID REFERENCES puzzles(id),    -- NULL cho đến khi được approve → save
  UNIQUE(job_id, page_number, board_index)
)
```

### Nhóm 7: Thông báo

```sql
notifications (
  id          UUID PRIMARY KEY,
  user_id     UUID REFERENCES users(id),
  type        ENUM('assignment','payment','tournament','system','achievement','grading'),
  title       VARCHAR(200) NOT NULL,
  body        TEXT,
  data        JSONB,
  is_read     BOOLEAN DEFAULT false,
  created_at  TIMESTAMP DEFAULT NOW()
)
```

---

## 2.3 API Endpoints

### Auth
| Method | Endpoint | Mô tả | Quyền |
|---|---|---|---|
| POST | `/api/auth/login` | Đăng nhập email/password | Public |
| POST | `/api/auth/register` | Đăng ký | Public |
| POST | `/api/auth/google` | Google OAuth callback | Public |
| POST | `/api/auth/facebook` | Facebook OAuth callback | Public |
| POST | `/api/auth/refresh` | Refresh token | Auth |
| POST | `/api/auth/forgot-password` | Gửi email reset | Public |
| POST | `/api/auth/reset-password` | Đặt mật khẩu mới | Public |

### Classes & Enrollment
| Method | Endpoint | Mô tả | Quyền |
|---|---|---|---|
| GET | `/api/classes` | Danh sách lớp | Auth |
| POST | `/api/classes` | Tạo lớp | Teacher/Admin |
| PUT | `/api/classes/{id}` | Sửa thông tin lớp | Teacher/Admin |
| POST | `/api/classes/{id}/students` | Thêm học sinh | Teacher |
| DELETE | `/api/classes/{id}/students/{sid}` | Xóa học sinh | Teacher |

### AI Scanner
| Method | Endpoint | Mô tả | Quyền |
|---|---|---|---|
| POST | `/api/scan/upload` | Upload PDF → tạo scan job | Teacher |
| GET | `/api/scan/jobs/{id}` | Trạng thái scan job | Teacher |
| GET | `/api/scan/jobs/{id}/results` | Danh sách kết quả từng trang | Teacher |
| PUT | `/api/scan/results/{id}/review` | Giáo viên duyệt/sửa FEN | Teacher |
| POST | `/api/scan/results/{id}/approve` | Approve → tạo puzzle | Teacher |

### Puzzles
| Method | Endpoint | Mô tả | Quyền |
|---|---|---|---|
| GET | `/api/puzzles` | Danh sách bài toán (filter/search) | Auth |
| POST | `/api/puzzles` | Tạo bài toán mới | Teacher |
| PUT | `/api/puzzles/{id}` | Sửa bài toán | Teacher |
| GET | `/api/puzzles/{id}/solutions` | Danh sách lời giải | Auth |
| POST | `/api/puzzles/{id}/solutions` | Thêm lời giải | Teacher |

### Assignments & Progress
| Method | Endpoint | Mô tả | Quyền |
|---|---|---|---|
| POST | `/api/assignments` | Giao bài | Teacher |
| GET | `/api/assignments/me` | Bài tập của tôi | Student |
| POST | `/api/progress` | Nộp kết quả làm bài | Student |
| PUT | `/api/progress/{id}/grade` | Giáo viên chấm điểm thủ công | Teacher |
| GET | `/api/leaderboard/{class_id}` | Bảng xếp hạng lớp | Auth |
| GET | `/api/analytics/teacher` | Dashboard giáo viên | Teacher |
| GET | `/api/analytics/student` | Dashboard học sinh | Student |

### Payment
| Method | Endpoint | Mô tả | Quyền |
|---|---|---|---|
| GET | `/api/fee-plans` | Danh sách gói học phí | Admin |
| POST | `/api/invoices/generate` | Tạo hóa đơn hàng loạt | Admin |
| GET | `/api/invoices` | Danh sách hóa đơn | Admin/Parent |
| GET | `/api/invoices/{id}/pdf` | Xuất hóa đơn PDF | Auth |
| POST | `/api/payments/confirm` | Admin xác nhận chuyển khoản | Admin |
| POST | `/api/payments/vnpay` | Tạo link VNPay | Auth |
| POST | `/api/payments/momo` | Tạo link MoMo | Auth |
| POST | `/api/payments/webhook/{provider}` | Webhook callback | System |

### Tournaments
| Method | Endpoint | Mô tả | Quyền |
|---|---|---|---|
| GET | `/api/tournaments` | Danh sách giải đấu | Auth |
| POST | `/api/tournaments` | Tạo giải đấu | Teacher |
| POST | `/api/tournaments/{id}/register` | Đăng ký tham gia | Student |
| GET | `/api/tournaments/{id}/standings` | Bảng xếp hạng | Auth |
| WS | `/ws/game/{game_id}` | Kết nối ván cờ realtime | Auth |

---

## 2.4 Screen Map

```
WEB APP
├── Auth
│   ├── /login          (email + Google + Facebook)
│   └── /register
├── Teacher Portal
│   ├── /dashboard      Thống kê tổng quan lớp
│   ├── /classes        Quản lý lớp học
│   ├── /puzzles        Kho bài toán (tạo từ PGN/FEN/bàn cờ)
│   ├── /scanner        Upload & scan PDF (3A→3B→3C→3D pipeline)
│   ├── /assignments    Giao bài + chấm điểm
│   ├── /analytics      Báo cáo chi tiết học viên
│   ├── /tournaments    Quản lý giải đấu
│   └── /finance        Báo cáo tài chính
├── Student Portal
│   ├── /dashboard      ELO, streak, bài tập hôm nay
│   ├── /practice       Luyện bài toán (xem điểm AI + feedback GV)
│   ├── /leaderboard    Bảng xếp hạng lớp
│   └── /tournaments    Giải đấu & thi đấu online
├── Admin Portal
│   ├── /finance        Thu chi, hóa đơn, xác nhận chuyển khoản
│   └── /reports        Báo cáo tổng
└── Parent Portal
    ├── /child-progress Tiến độ con
    └── /invoices       Học phí & thanh toán

MOBILE APP (React Native / Expo)
├── Student: Home | Practice | Tournament | Profile
└── Parent:  Dashboard (tiến độ con) | Payment (học phí)
```

---

## 2.5 Cấu trúc Thư mục Dự án

```
chess-academy/
├── backend/
│   ├── app/
│   │   ├── api/         auth.py, classes.py, puzzles.py, scan.py,
│   │   │                assignments.py, progress.py, payments.py,
│   │   │                tournaments.py, notifications.py, analytics.py
│   │   ├── models/      user.py, class_.py, puzzle.py, scan.py,
│   │   │                payment.py, tournament.py, notification.py
│   │   ├── services/    pdf_service.py, cv_service.py,
│   │   │                board_detector.py, board_rectifier.py,
│   │   │                piece_classifier.py, fen_assembler.py,
│   │   │                fen_validator.py, stockfish_service.py,
│   │   │                chess/
│   │   │                  ├── pgn_parser.py
│   │   │                  ├── fen_service.py
│   │   │                  └── exercise_generator.py
│   │   │                payment/
│   │   │                  ├── payment_service.py
│   │   │                  ├── providers/ (base.py, payos.py, vnpay.py, momo.py, zalopay.py, vietqr.py)
│   │   │                  ├── webhook/   (payos.py, vnpay.py, momo.py, zalopay.py)
│   │   │                  ├── signature/ (payos.py, vnpay.py, momo.py)
│   │   │                  └── reconciliation.py
│   │   │                tournament_service.py, notification_service.py
│   │   ├── schemas/     (Pydantic request/response schemas)
│   │   ├── core/        config.py, security.py, database.py
│   │   ├── websocket/   game_handler.py
│   │   └── main.py
│   ├── models/          chess_yolov8.pt  (AI model file)
│   ├── tests/           unit/, integration/, load/
│   ├── alembic/         (DB migrations)
│   └── requirements.txt
├── frontend/
│   └── src/
│       ├── pages/       teacher/, student/, admin/, parent/
│       ├── components/  (shared UI components)
│       ├── store/       authStore.ts, uiStore.ts  (Zustand)
│       └── api/         (Axios service classes)
├── mobile/
│   ├── app/             (student)/, (parent)/  (Expo Router)
│   ├── components/
│   └── services/
├── docs/                (tài liệu SDLC)
├── docker-compose.yml
├── .env.example
└── .github/workflows/ci.yml
```

---

> **Migration Note:** Trước khi chạy Alembic migration đầu tiên, đảm bảo schema đã bao gồm:
> `branches`, `student_attempts`, `payment_webhook_logs`, và tất cả fields mới trong `payments` / `scan_results`.
> Thứ tự migration: `centers` → `branches` → `users` (có `primary_branch_id`) → `classes` (có `branch_id`) → còn lại.
