Được ông chủ. Tôi đã đọc lại **toàn bộ 9 file** trong `docs/`, đối chiếu chéo giữa Requirements → System Design → Sprint → Testing → Deployment → Maintenance → AI Scanner → Payment → SDLC.

### Kết luận trước

**Bộ tài liệu hiện tại đã tốt hơn rất nhiều và đã đủ chi tiết để bước sang giai đoạn code, nhưng tôi chưa khuyên “đóng băng” để AI Agent triển khai ngay.**

Có khoảng **8 điểm cần sửa trước**, trong đó **5 điểm là P0 — nếu không sửa trước khi tạo migration/code thì rất dễ phải làm lại**.

Phần AI Scanner và Puzzle đã đi đúng hướng: requirements đã xác định 3 cách tạo bài `PGN/FEN/manual`, lưu source và cho phép nhiều solution; AI Scanner cũng đã tách Detector → Rectifier → Classifier → FEN → Validation → Human Review → Exercise Generator.  

---

# 1. P0 — Sửa timeline đang lệch nhau

Đây là lỗi rõ nhất giữa các file.

`03_sprint_plan.md` hiện ghi:

```text
Sprint 0       tuần 1–2
Sprint 1       tuần 3–4
Sprint 2       tuần 5–6
Sprint 3A-3D   tuần 7–10
Sprint 4       tuần 11–12
Sprint 5       tuần 13–14
Sprint 6       tuần 15–16
Sprint 7       tuần 17–18
Sprint 8       tuần 19–20
```

Cái này **rất hợp lý**.  

Nhưng `06_maintenance.md` lại ghi:

```text
v1.0 = Sprint 0–4, tuần 1–10
v1.5 = Sprint 5–6, tuần 11–16
v2.0 = Sprint 7–8, tuần 17–20
```

Trong khi Sprint 4 thực tế bắt đầu tuần 11. 

### Nên sửa thành:

```text
v1.0 MVP
Sprint 0–4
Tuần 1–12

v1.5
Sprint 5–6
Tuần 13–16

v2.0
Sprint 7–8
Tuần 17–20
```

Đây là việc đầu tiên cần sửa.

---

# 2. P0 — Database AI Scanner chưa khớp với chính kiến trúc AI

Đây là điểm tôi đặc biệt muốn ông chủ sửa.

AI Scanner định nghĩa một trang PDF có thể có:

```text
Page 05
 ├── Board 01
 └── Board 02
```

Service A cũng trả về **nhiều board trên một trang**. 

Nhưng DB hiện tại:

```sql
scan_results (
    job_id
    page_number
    board_image_url
    bounding_box
    ...
    puzzle_id
)
```

tức là đang ngầm hiểu:

```text
1 page = 1 board
```

Trong khi AI architecture lại cho phép:

```text
1 page = N boards
```

DB hiện tại nằm ở `scan_results` với đúng một `bounding_box` và một `puzzle_id`. 

### Tôi khuyên sửa tối thiểu thành:

```sql
scan_results (
    id UUID PRIMARY KEY,
    job_id UUID NOT NULL,
    page_number INT NOT NULL,
    board_index INT NOT NULL,

    page_image_url VARCHAR(500),
    board_image_url VARCHAR(500),

    bounding_box JSONB,
    confidence_board DECIMAL(4,2),

    fen_candidate TEXT,
    fen_final TEXT,
    cell_confidence JSONB,

    review_status ...,
    reviewed_by UUID,
    reviewed_at TIMESTAMP,

    puzzle_id UUID,

    UNIQUE(job_id, page_number, board_index)
)
```

Như vậy:

```text
scan_job #1

page 5
 ├── board 0
 ├── board 1
 └── board 2

page 6
 └── board 0
```

không còn vấn đề.

---

# 3. P0 — FEN hiện đang sai kiến trúc

Đây là lỗi kỹ thuật quan trọng nhất trong `AI_SCANNER_ARCHITECTURE.md`.

Service C hiện build:

```python
fen_board = board.board_fen()
return fen_board
```

tức chỉ trả:

```text
r1bqk...
```

Đây **chưa phải full FEN**.

Nhưng ngay sau đó Validation lại gọi:

```python
board = chess.Board(fen)
```

`python-chess` đang được sử dụng như thể `fen` đã là full FEN. Hai đoạn này chưa thống nhất.  

Một FEN đầy đủ cần có trạng thái như:

```text
board placement
side to move
castling rights
en passant
halfmove
fullmove
```

### Quan trọng hơn nữa

AI nhìn hình bàn cờ **không thể tự biết chắc**:

```text
w/b
KQkq
en passant
halfmove
fullmove
```

Đặc biệt:

> **side to move**

có thể nằm ở phần đề bài trong sách, chứ không nằm trong hình bàn cờ.

### Tôi đề xuất thiết kế:

```text
AI nhận diện
      ↓
board_fen
      +
side_to_move
      +
castling_rights
      +
en_passant
      +
metadata
      ↓
Full FEN
      ↓
python-chess
      ↓
Stockfish
```

Trong Human Review UI nên cho giáo viên xác nhận:

```text
Lượt đi:     ○ White  ○ Black

Castling:
☑ K
☑ Q
☑ k
☑ q

En passant: [ none ]

FEN:
[................................................]

[Validate]
```

Đây là chỗ tôi khuyên sửa **trước khi viết `fen_validator.py`**.

---

# 4. P0 — Teacher Review hiện vừa "bắt buộc" vừa "auto approve"

Trong nguyên tắc AI:

> Human-in-the-loop bắt buộc.



Nhưng validation lại có:

```text
Tất cả OK
   ↓
Auto-approve
```

và ghi:

> nếu GV bật tính năng.



Hai điều này phải thống nhất.

### Tôi đề xuất v1:

```text
AI → luôn REVIEW_PENDING
      ↓
Teacher approve/correct
      ↓
Puzzle
```

v2 mới cho phép:

```text
confidence rất cao
+
validation OK
+
nguồn sách đã trusted
+
Admin bật auto-approve
```

thì:

```text
AUTO_APPROVED
```

---

# 5. P0 — Payment Architecture chưa cập nhật theo hướng payOS

Đây là điểm quan trọng nhất sau cuộc trao đổi của chúng ta.

File hiện tại vẫn đang viết Level 2:

```text
Sepay
OpenBanking
hoặc dịch vụ tương tự
        ↓
/api/payments/webhook/vietqr
```



Trong khi phần provider lại chỉ có:

```text
vnpay
momo
zalopay
vietqr
```



Và `payments.payment_method` cũng chưa có `payos`; hiện là:

```text
vnpay
momo
zalopay
bank_transfer
cash
```



### Tôi khuyên sửa kiến trúc ngay thành:

```text
providers/
├── base.py
├── payos.py
├── vnpay.py
├── momo.py
├── zalopay.py
└── vietqr.py

webhook/
├── payos.py
├── vnpay.py
├── momo.py
└── zalopay.py
```

và:

```text
payment_method:

payos
vnpay
momo
zalopay
bank_transfer
cash
```

### API

Giữ abstraction:

```text
POST /api/payments/{provider}
```

hoặc explicit:

```text
POST /api/payments/payos
POST /api/payments/webhook/payos
```

Như vậy tài liệu sẽ phản ánh đúng kiến trúc mà ông chủ chuẩn bị triển khai.

---

# 6. P0 — Payment DB chưa đủ an toàn cho Level 2

Hiện `payments` mới có:

```text
transaction_id
status
payment_data
```



Trong khi chính Payment Architecture đã xác định cần:

```text
idempotency
duplicate callback
signature
reconciliation
```



Tôi khuyên thêm:

```sql
payments (
    ...

    provider
    provider_order_id
    provider_transaction_id
    payment_link_id
    reference

    idempotency_key

    signature_verified BOOLEAN DEFAULT false

    currency CHAR(3) DEFAULT 'VND'

    created_at
    updated_at
)
```

và quan trọng nhất:

```sql
UNIQUE(provider, provider_transaction_id)
```

### Không nên chỉ dựa vào Redis

Tài liệu hiện nói lưu transaction ID trong Redis TTL 24h. 

Redis chỉ nên là **lớp tối ưu**.

Database unique constraint mới là:

> **nguồn sự thật cuối cùng chống duplicate.**

---

# 7. P0 — Student Progress chưa lưu đủ dữ liệu để replay bài làm

Requirements nói giáo viên phải xem lại bài làm và chấm thủ công. 

E2E test cũng yêu cầu:

> click vào bài → xem replay nước đi. 

Nhưng `student_progress` hiện chỉ có:

```text
attempts
hints_used
time_spent_seconds
error_moves
points_earned
```

không có:

```text
student_moves
submitted_pgn
move_sequence
```



### Tôi khuyên tạo riêng:

```sql
student_attempts (
    id UUID PRIMARY KEY,
    progress_id UUID NOT NULL,

    attempt_no INT NOT NULL,

    moves_uci TEXT[],
    moves_san TEXT[],
    pgn TEXT,

    points_earned INT,
    result VARCHAR(30),

    started_at TIMESTAMP,
    completed_at TIMESTAMP
)
```

Sau này giáo viên mở:

```text
Attempt 1
1. e4?
2. Nf3?
3. ...

Attempt 2
1. Qxh7+
2. ...
```

là replay được đầy đủ.

---

# 8. P0 — Multi-branch đã yêu cầu nhưng Database chưa có Branch

Requirements ghi rõ:

> Hỗ trợ nhiều cơ sở (branch) trong một trung tâm. 

Nhưng DB hiện tại chỉ có:

```text
centers
users
classes
```

không có:

```text
branches
```



### Nên thêm:

```sql
branches (
    id UUID PRIMARY KEY,
    center_id UUID NOT NULL,
    name VARCHAR(200),
    address TEXT,
    phone VARCHAR(20),
    is_active BOOLEAN DEFAULT true
)
```

và:

```text
classes.branch_id
```

Có thể thêm `users.branch_id` sau nếu cần.

Đây là việc nên sửa trước Alembic migration đầu tiên.

---

# 9. P1 — PGN/FEN/UCI đã có ở Requirements nhưng thiếu service thực thi

Requirements đã rất rõ:

```text
PGN
FEN
bàn cờ thủ công
```

và giáo viên có thể nhập lời giải PGN/UCI. 

Sprint 4 cũng đã thiết kế UI:

```text
PGN → engine → Generate → Preview → Approve
FEN → Analyze → Generate
Manual → Save
```



Nhưng trong architecture/service tree chưa thấy rõ:

```text
pgn_service.py
exercise_generator.py
```

### Tôi khuyên thêm:

```text
services/chess/
├── pgn_service.py
├── fen_service.py
├── uci_service.py
├── stockfish_service.py
└── exercise_generator.py
```

Luồng chuẩn:

```text
PGN
 ↓
Replay từng ply
 ↓
FEN tại từng position
 ↓
Stockfish
 ↓
Candidate positions
 ↓
Exercise Generator
 ↓
Puzzle + Solutions
```

Đây chính là phần chúng ta vừa phân tích ở tin nhắn trước.

---

# 10. P1 — ELO chưa định nghĩa rõ ELO dùng cho cái gì

Hiện tài liệu có:

```text
Puzzle points
+
ELO
```

và Sprint 4 có logic K-factor. 

Trong Tournament lại có:

```text
Update standings + ELO
```



Tôi khuyên chốt:

```text
Puzzle
  → points / accuracy / streak
  → KHÔNG đổi ELO

Tournament rated game
  → ELO
```

Như vậy sẽ dễ hiểu hơn rất nhiều.

---

# 11. P1 — AI test target hiện chưa thống nhất

Sprint 3A:

```text
>= 10 ảnh
confidence >= 0.90
```



Testing lại yêu cầu:

```text
Board detection >= 99%
```



AI architecture lại yêu cầu:

```text
200 pages
5000 cells
200 ground-truth FEN
```

và full pipeline `<30s/page`. 

### Nên chia thành:

**Sprint development test**

```text
10–20 images
```

**Acceptance test**

```text
200 pages
>= 5 loại sách
```

**Production target**

```text
Board detection
Recall >= X
Precision >= X
IoU >= X

Piece classifier
>= 95% per-cell

Full pipeline
P95 < 30s/page
```

Đặc biệt với Board Detection, tôi khuyên dùng **Precision/Recall/IoU**, không chỉ gọi chung là "accuracy".

---

# 12. P1 — `Stockfish sanity check` trong tài liệu và code chưa giống nhau

Architecture ghi:

```text
Stockfish Sanity Check
engine.analyse(board)
```

nhưng code bên dưới thực tế chỉ:

```python
if board.is_game_over():
...
if not list(board.legal_moves):
...
```



Tức hiện tại đó là:

```text
python-chess legality check
```

chứ chưa phải Stockfish analysis.

Nên sửa một trong hai:

```text
Step 3 = Chess legality validation
```

hoặc thật sự gọi:

```text
Stockfish
```

để sanity-check/evaluate.

Tôi nghiêng về tách:

```text
FEN Validation
     ↓
python-chess is_valid()
     ↓
Stockfish Analysis
```

rõ ràng hơn.

---

# 13. P1 — Docker worker đang thiếu một số thứ cần thiết

`docker-compose` đã có:

```text
worker
celery
```



nhưng danh sách dependencies trong Sprint 0 hiện chưa thể hiện rõ `celery`.

Đồng thời các module có:

```text
Cron:
- overdue invoice
- reconciliation
- notification
```

nhưng Compose chưa có worker scheduler/beat tương ứng.

Tôi khuyên:

```text
backend
worker
beat
postgres
redis
minio
frontend
```

và dependencies:

```text
celery[redis]
```

Thêm:

```env
CELERY_BROKER_URL=redis://redis:6379/0
CELERY_RESULT_BACKEND=redis://redis:6379/1
```

---

# 14. P1 — Backup đang mâu thuẫn retention

Requirements:

```text
Backup daily
retention 1 year
```



Deployment/Maintenance:

```text
retention 30 days
```

 

Nên chốt:

```text
Daily backup       30 days
Weekly backup      12 weeks
Monthly backup     12 months
```

Như vậy vừa hợp lý vừa đáp ứng retention 1 năm.

Ngoài ra:

```text
pg_restore
```

thường nên đi cùng backup format phù hợp, ví dụ:

```bash
pg_dump -Fc ...
```

rồi:

```bash
pg_restore ...
```

---

# 15. P1 — CI/CD chưa xử lý model AI

Maintenance nói model được version bằng Git LFS. 

Nhưng CI AI test lại chạy:

```text
models/chess_yolov8.pt
```

mà chưa thấy bước pull Git LFS/model artifact.

Với model lớn, tôi khuyên:

```text
Git
 ├── source code
 └── model version metadata

Model Storage
 └── chess_yolov8_v1.pt
```

CI lấy model artifact tương ứng.

Không nên để pipeline production phụ thuộc vào một file model local mà CI không chắc có.

---

# 16. Một điểm rất đáng sửa: `SDLC(1).md`

Ông chủ đang có:

```text
SDLC(1).md
```

và:

```text
SDLC.md
```

`SDLC.md` hiện là bản 2.0, còn `SDLC(1).md` là tài liệu cũ/tóm tắt. Bản cũ vẫn có kiến trúc và roadmap khác. 

Đây là **rủi ro lớn khi dùng Antigravity/AI Agent**.

Agent có thể đọc nhầm:

```text
SDLC(1).md
```

rồi triển khai theo tài liệu cũ.

### Tôi khuyên:

```text
docs/
├── SDLC.md                ← SOURCE OF TRUTH
├── 01_requirements.md
├── 02_system_design.md
├── 03_sprint_plan.md
├── 04_testing.md
├── 05_deployment.md
├── 06_maintenance.md
├── AI_SCANNER_ARCHITECTURE.md
└── PAYMENT_ARCHITECTURE.md
```

và:

```text
archive/
└── SDLC_legacy_20260917.md
```

Hoặc xóa hẳn nếu không cần giữ.

---

# Kiến trúc sau khi sửa tôi muốn CAMS đạt được

```text
                         CAMS
                          │
              ┌───────────┴───────────┐
              │                       │
          Management               Chess Core
              │                       │
       ┌──────┼──────┐        ┌───────┼────────┐
       │      │      │        │       │        │
     Class  Payment  User    PGN     FEN    UCI
       │      │               │       │        │
       │    PayOS             └───────┼────────┘
       │      │                       │
       │   Webhook                Stockfish
       │      │                       │
       │      ▼                       ▼
       │    Invoice                Exercise
       │      │                  Generator
       │      │                       │
       └──────┴───────────────────────┘
                          │
                          ▼
                     PostgreSQL
```

AI Scanner:

```text
PDF
 │
 ▼
PDF Extractor
 │
 ▼
Board Detector
 │
 ├── Page 01 / Board 01
 ├── Page 01 / Board 02
 └── Page 02 / Board 01
 │
 ▼
Rectifier
 │
 ▼
Piece Classifier
 │
 ▼
Board FEN
 │
 + side_to_move
 + castling
 + en_passant
 │
 ▼
Full FEN
 │
 ▼
python-chess validation
 │
 ▼
Stockfish
 │
 ▼
Human Review
 │
 ▼
Exercise Generator
 │
 ▼
Puzzle + Solutions
```

Payment:

```text
Invoice
   │
   ▼
Payment Service
   │
   ├── Level 1 → VietQR → Admin confirm
   │
   └── Level 2 → PayOS
                    │
                    ▼
                   QR
                    │
                 Parent
                    │
                  Bank
                    │
                    ▼
                  PayOS
                    │
                 Webhook
                    │
                    ▼
              Verify signature
                    │
              Idempotency
                    │
              Match invoice
                    │
              Validate amount
                    │
                    ▼
                 PAID
```

---

# Thứ tự tôi khuyên ông chủ làm ngay

**Bước 1 — Chỉnh tài liệu, chưa code business logic**

Sửa 8 điểm P0 ở trên, đặc biệt:

```text
① Timeline
② Branch
③ scan_results multiple boards
④ Full FEN
⑤ student_attempts
⑥ Payment PayOS
⑦ payment idempotency fields
⑧ Backup retention
```

**Bước 2 — Chốt `02_system_design.md` làm nguồn sự thật cho DB**

Sau đó mới:

```text
Alembic migration
        ↓
PostgreSQL schema
        ↓
SQLAlchemy models
```

**Bước 3 — Chốt API contract**

Đặc biệt:

```text
/api/scan/*
/api/puzzles/*
/api/assignments/*
/api/progress/*
/api/payments/*
```

**Bước 4 — mới cho Antigravity Agent triển khai Sprint 0.**

---

## Tôi đánh giá trạng thái hiện tại

**Requirements:** khá đầy đủ.
**AI Scanner:** kiến trúc tốt, nhưng FEN + multi-board cần sửa trước code.
**Puzzle:** đã có nền tảng đúng cho PGN/FEN/UCI và multi-solution.
**Payment:** tư duy Level 1/2/3 tốt, nhưng tài liệu **chưa được cập nhật sang PayOS** và DB Level 2 còn thiếu trường quan trọng.
**Testing:** khá đầy đủ nhưng phải thống nhất metrics/dataset.
**DevOps:** tốt về khung, nhưng worker/beat/model artifact/backup cần hoàn thiện.
**Documentation:** vấn đề lớn nhất là **timeline và `SDLC(1).md` cũ**.

**Vì vậy: chưa nên để Agent chạy toàn bộ dự án ngay. Nhưng chỉ cần xử lý nhóm P0 trên là CAMS có thể bước sang giai đoạn “Design Freeze → Migration → Sprint 0” khá chắc chắn.**

Đặc biệt, tôi khuyên **chốt `02_system_design.md` + `AI_SCANNER_ARCHITECTURE.md` + `PAYMENT_ARCHITECTURE.md` trước**, vì đây là ba file quyết định phần code khó và nếu sai sẽ tốn công sửa nhất.


Tôi sẽ sửa chiến lược thành:
                 PAYMENT

                    │
            ┌───────┴────────┐
            │                │
        Level 1            Level 2/3
         MVP               Optional
            │                │
      Làm trước          Làm sau nếu
                         thực sự cần

Sprint 5

Chỉ cần hoàn thành:
Fee Plan
    ↓
Invoice
    ↓
VietQR
    ↓
Parent chuyển khoản
    ↓
Admin xác nhận
    ↓
Payment SUCCESS
    ↓
Invoice PAID
    ↓
Receipt/notification
Sau đó đóng Payment lại. và chuyển qua Sprint 6

Vì vậy, nếu là tôi triển khai CAMS theo tài liệu của ông chủ, tôi sẽ đi:
                    CAMS v1
                      │
        ┌─────────────┼──────────────┐
        │             │              │
    AI Scanner     Practice      Management
        │             │              │
        └─────────────┼──────────────┘
                      │
                 Payment L1
                      │
                      ▼
                 Tournament
                      │
                      ▼
                  Mobile
                      │
                      ▼
                 Production
                      │
              ┌───────┴────────┐
              │                │
        Có nhu cầu?        Không cần?
              │                │
             Có               Giữ L1
              │
       Level 2 / Level 3
Tóm lại: Ông chủ cứ làm Level 1 → Sprint 6 hoàn toàn OK. Sau đó nếu không bao giờ làm Level 2/3 thì CAMS vẫn chạy bình thường và có thể dùng thực tế.