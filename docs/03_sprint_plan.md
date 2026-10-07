# Giai đoạn 3: Lập trình — Sprint Plan

> **CAMS — Chess Academy Management System**
> Tài liệu con của [SDLC.md](./SDLC.md)
> **Quy ước:** Mỗi Sprint = 2 tuần. Tổng: 8 Sprints + 4 sub-sprints = ~20 tuần (~5 tháng).

---

## Sprint 0 — Infrastructure Setup (Tuần 1–2)

### Backend (Python/FastAPI)
- Cấu trúc thư mục: `backend/app/{api,models,services,schemas,core,websocket}/`
- `requirements.txt`: `fastapi uvicorn sqlalchemy alembic asyncpg redis celery[redis] python-chess ultralytics opencv-python pymupdf pydantic python-jose passlib httpx stockfish authlib`
- Thiết lập FastAPI instance, CORS, logging, environment config (`.env`)
- Cấu hình Alembic database migrations — chạy migration tạo toàn bộ tables
- Docker Compose: `backend + worker (Celery) + beat (Celery Beat) + postgres:16 + redis:7 + frontend`
- Environment variables:
  ```env
  CELERY_BROKER_URL=redis://redis:6379/0
  CELERY_RESULT_BACKEND=redis://redis:6379/1
  ```

### Frontend (React/Vite)
- `npm create vite@latest frontend -- --template react-ts`
- Cài packages: `react-router-dom axios react-chessboard chess.js recharts react-query zustand socket.io-client lucide-react react-hot-toast`
- Cấu hình Tailwind CSS, design tokens, React Router v6, Axios interceptors

### Mobile (React Native/Expo)
- `npx create-expo-app mobile --template`
- Cài packages: `expo-router react-native-chessboard @react-native-firebase/messaging axios zustand expo-notifications`
- Cấu hình Firebase FCM, deep linking, Expo Router

---

## Sprint 1 — Auth & User Management (Tuần 3–4)

### Backend
- Models: `users`, `centers`, `parent_student`
- API `/api/auth`: `login`, `register`, `refresh`, `forgot-password`, `reset-password`
- Google OAuth: `POST /api/auth/google` (authlib)
- **Facebook OAuth: `POST /api/auth/facebook`** *(mới)*
- JWT + Refresh Token; bcrypt password hash
- Dependency `get_current_user(role_required)`

### Frontend
- `pages/Login.tsx` — email/password + nút Google + nút Facebook
- `pages/Register.tsx`
- `components/PrivateRoute.tsx` — phân 4 role: Admin / Teacher / Student / Parent
- `store/authStore.ts` (Zustand) — lưu JWT, user info
- Axios interceptor: tự động gắn `Authorization: Bearer <token>` vào mỗi request

---

## Sprint 2 — Classes & Enrollment (Tuần 5–6)

### Backend
- Models: `classes`, `class_enrollments`
- CRUD API `/api/classes`
- API thêm/xóa học sinh vào lớp
- API lấy lịch học theo lớp

### Frontend (Teacher)
- `Classes.tsx` — danh sách lớp + filter theo level/tên
- `ClassForm.tsx` — modal tạo/sửa lớp (tên, level, max_students, lịch học)
- `StudentList.tsx` — danh sách học sinh trong lớp + nút thêm/xóa
- `Schedule.tsx` — xem lịch học dạng calendar

---

## Sprint 3A — Board Detection (Tuần 7)

> **Nguyên tắc:** Test từng bước trước khi chuyển sang bước tiếp theo.

### Nhiệm vụ
1. `services/pdf_service.py`: Upload PDF → render từng trang thành PNG 300 DPI (PyMuPDF) → lưu vào local storage
2. `services/board_detector.py`:
   - Input: page image URL
   - Dùng OpenCV tìm contour bàn cờ (phát hiện hình vuông lớn nhất)
   - Output: `{"x": 125, "y": 340, "width": 820, "height": 820, "confidence": 0.97}`
3. API `POST /api/scan/upload` → tạo `scan_job` → queue xử lý background

### Test criteria Sprint 3A
- Nhận diện đúng bounding box trên ảnh bàn cờ từ sách thật (test >= 10 ảnh khác nhau)
- Xử lý được: bàn cờ nghiêng, ảnh mờ, nhiều bàn cờ trên 1 trang
- Board Detection metrics: Precision >= 0.95, Recall >= 0.95, IoU >= 0.75
- Confidence score >= 0.90 trên ảnh chuẩn

---

## Sprint 3B — Board Rectifier (Tuần 8)

### Nhiệm vụ
1. `services/board_rectifier.py`:
   - Input: board image (crop từ bounding box)
   - Corner Detection (tìm 4 góc chính xác)
   - Perspective Transform (warp perspective)
   - Output: ảnh bàn cờ chuẩn hóa 640×640 px
2. Cắt lưới 8×8 = 64 ô, mỗi ô 80×80 px
3. Lưu ảnh các ô vào local storage (dùng khi cần debug)

### Test criteria Sprint 3B
- Ảnh bàn cờ sau transform phải vuông, không méo
- 64 ô cắt ra phải đúng vị trí tương ứng với a8→h8 (hàng trên) → a1→h1 (hàng dưới)
- Test với ảnh chụp nghiêng 15°, 30°

---

## Sprint 3C — Piece Classifier → FEN (Tuần 9)

### Nhiệm vụ
1. `services/piece_classifier.py`:
   - Input: 64 cell images (80×80 px)
   - Load YOLOv8 model (`models/chess_yolov8.pt`)
   - Classify từng ô → 13 nhãn: `K, Q, R, B, N, P` (trắng), `k, q, r, b, n, p` (đen), `empty`
   - Output confidence score cho từng ô
2. `services/fen_builder.py`:
   - Dịch ma trận 8×8 kết quả → chuỗi FEN hợp lệ (python-chess)
3. Pipeline Validation:
   ```
   FEN Candidate
        ↓
   FEN Validator (python-chess parse check)
        ↓
   Chess Position Validator (số quân hợp lệ: 1 vua mỗi bên, max 8 chốt...)
        ↓
   Stockfish sanity check (position có legal moves không?)
        ↓
   Human Review (nếu có ô confidence < 70%)
   ```
4. Lưu kết quả vào `scan_results`: `fen_candidate`, `cell_confidence` (JSONB)

### Output ví dụ
```json
{
  "fen_candidate": "r1bqkb1r/pppp1ppp/2n2n2/4p3/2B1P3/5N2/PPPP1PPP/RNBQK2R w KQkq - 4 4",
  "validation": "valid",
  "low_confidence_cells": [
    {"square": "d8", "piece": "q", "confidence": 0.63},
    {"square": "f5", "piece": "P", "confidence": 0.58}
  ]
}
```

### Test criteria Sprint 3C
- Piece classification accuracy >= 95% per cell (test trên dataset 1000+ ô)
- FEN generated phải parse được bởi python-chess không exception
- Flag đúng các ô có confidence < 70%

---

## Sprint 3D — Teacher Review UI (Tuần 10) [DONE]

### Backend
- API `GET /api/scan/jobs/{id}/results` — trả danh sách scan_results với cell_confidence
- API `PUT /api/scan/results/{id}/review` — giáo viên sửa FEN
- API `POST /api/scan/results/{id}/approve` — approve → tạo puzzle

### Frontend Scanner UI (`pages/teacher/Scanner.tsx`)
- Drop zone upload PDF + progress bar (polling API)
- Grid các bàn cờ phát hiện được:
  - Hiển thị ảnh bàn cờ + FEN đề xuất
  - Highlight ô có confidence thấp (màu vàng/đỏ)
  - Cảnh báo:
    ```
    ┌──────────────────────────────┐
    │ ⚠ Có 3 ô cần kiểm tra        │
    │ d8  Queen     63%            │
    │ f5  Pawn      58%            │
    │ g2  Empty     61%            │
    │ [Sửa bàn cờ]   [Chấp nhận]  │
    └──────────────────────────────┘
    ```
  - FEN editor inline (chỉnh tay nếu cần)
  - Nút "Chấp nhận" → approve, nút "Từ chối" → reject
- Sau khi duyệt xong → "Lưu tất cả puzzle đã chấp nhận"

---

## Sprint 4 — Puzzle Library & Practice (Tuần 11–12)

### Backend
- CRUD `/api/puzzles` (filter theo difficulty/tags/source_type/search)
- API `puzzle_solutions` (CRUD lời giải 1:N)
- `/api/assignments` — giao bài cho lớp hoặc cá nhân
- `/api/progress` — nộp kết quả, logic chấm điểm auto AI:
  - So khớp nước đi với `puzzle_solutions` → nếu đúng: `grading_method='auto_ai'`, cập nhật `points_earned`
- `/api/leaderboard` — bảng xếp hạng
- Logic Puzzle Rating: K-factor theo rating band (K=32 nếu rating < 1200, K=24 nếu < 2000, K=16 nếu >= 2000)
  > **Lưu ý:** Puzzle Rating KHÔNG phải ELO. ELO chỉ thay đổi qua Tournament rated games (Sprint 6).

### Frontend — UI tạo bài tập (3 cách)

```
Teacher → Tạo bài tập
   ○ Từ PGN:   upload PGN → chọn loại tactic → engine depth → Generate → Preview → Approve → Publish
   ○ Từ FEN:   paste FEN → Load Board → chọn type → Analyze → Generate
   ○ Thủ công: drag & drop quân lên bàn cờ → chọn type → Save
```

### Frontend — Practice (Student)
- `pages/student/Practice.tsx`
- react-chessboard render FEN; chess.js validate legal moves
- Đúng → confetti animation + cộng điểm + gọi API progress
- Sai → shake animation + gợi ý hint (nếu còn lượt)
- Xem lại lời giải sau khi hoàn thành
- Hiển thị kết quả chấm:
  - `grading_method = 'auto_ai'` → icon Robot + "Hệ thống tự động chấm: X điểm"
  - `grading_method = 'manual_teacher'` → tên giáo viên + điểm + `teacher_feedback`

### Frontend — Teacher Dashboard
- `Assignments.tsx` — danh sách bài giao + filter chưa nộp/đã nộp
- `GradingBoard.tsx` — danh sách bài học sinh đã nộp → click vào xem lại nước đi trên bàn cờ → nhập điểm + nhận xét → "Lưu điểm"
- `Analytics.tsx` — biểu đồ Recharts (tỉ lệ hoàn thành, top students, lỗi phổ biến)

---

## Sprint 5 — Thanh toán Học phí (Tuần 13–14)

> Xem chi tiết: [PAYMENT_ARCHITECTURE.md](./PAYMENT_ARCHITECTURE.md)

### Level 1 — MVP (Sprint 5)
- Models: `fee_plans`, `invoices`, `payments`
- API CRUD `/api/fee-plans`
- `POST /api/invoices/generate` — tạo hóa đơn hàng loạt cho toàn lớp
- Hóa đơn có mã nội dung chuyển khoản (`INV-2026-001`) + QR VietQR tĩnh
- `POST /api/payments/confirm` — Admin xác nhận chuyển khoản → `pending → success`
- Cron job: check hóa đơn quá hạn → update `overdue` → gửi notification
- Export `/api/invoices/{id}/pdf` (WeasyPrint hoặc ReportLab)
- Frontend Admin: `Finance.tsx` (bảng hóa đơn, filter, nút "Xác nhận đã thu")
- Frontend Parent: `Invoices.tsx` (xem QR chuyển khoản, trạng thái)

### Level 2 — Webhook Auto (Sprint 5.5, sau MVP ổn định)
- Tích hợp webhook ngân hàng → tự động update `pending → success`

### Level 3 — Payment Gateway (Sprint 6+)
- VNPay, MoMo, ZaloPay integration
- `POST /api/payments/vnpay`, `POST /api/payments/momo`
- Webhook callback `POST /api/payments/webhook/{provider}`

---

## Sprint 6 — Giải đấu Online (Tuần 15–16)

### Backend
- Models: `tournaments`, `tournament_participants`, `tournament_games`, `tournament_standings`
- API CRUD `/api/tournaments`; đăng ký; lấy standings
- `services/tournament_service.py`:
  - Bắt cặp Swiss System (Monrad pairing)
  - Round Robin schedule
  - Update standings + ELO sau mỗi ván
- WebSocket `/ws/game/{game_id}`:
  - Sync nước đi realtime
  - Đồng hồ cờ (time control)
  - Kết thúc ván → lưu PGN → gọi `update_standings`
- Redis: lưu game state (FEN, clock, moves) → scale horizontal

### Frontend
- `Tournament/List.tsx` — danh sách + nút đăng ký
- `Tournament/Bracket.tsx` — sơ đồ thi đấu knockout
- `Tournament/Standings.tsx` — bảng điểm realtime qua WebSocket
- `Tournament/Game.tsx` — bàn cờ + đồng hồ countdown + mini chat

---

## Sprint 7 — Mobile App (Tuần 17–18)

### Cấu trúc Expo Router
- `mobile/app/(student)/` — Home, Practice, Tournament, Profile
- `mobile/app/(parent)/` — Dashboard, Payment

### Student screens
- Home: ELO widget, streak, danh sách bài mới hôm nay
- Practice: react-native-chessboard, hiển thị điểm + feedback sau khi làm xong
- Tournament: danh sách + thi đấu realtime

### Parent screens
- Dashboard: tiến độ con, biểu đồ ELO theo tuần
- Payment: xem hóa đơn, QR chuyển khoản, WebView VNPay/MoMo

### Features chung
- Push notification FCM (expo-notifications)
- Offline cache bài tập (AsyncStorage)
- Deep link: notification → mở thẳng bài tập / giải đấu / hóa đơn

---

## Sprint 8 — Notifications & Polish (Tuần 19–20)

### Notification Service
- Email (SendGrid): bài tập mới, hóa đơn sắp hạn, giải đấu sắp diễn ra, kết quả chấm điểm
- FCM Push: các trigger tương tự
- In-app notification center: real-time badge count qua WebSocket

### Polish
- Error Boundary toàn app + Toast notifications (react-hot-toast)
- PostgreSQL composite indexes tối ưu query thường dùng
- Redis cache leaderboard (TTL 5 phút)
- Responsive design audit tất cả màn hình
- Accessibility audit (WCAG 2.1 AA)
- Load test (Locust): 500 users đồng thời, P95 < 500ms
