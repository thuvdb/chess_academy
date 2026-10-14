# Giai đoạn 4: Chiến lược Kiểm thử (Testing Strategy)

> **CAMS — Chess Academy Management System**
> Tài liệu con của [SDLC.md](./SDLC.md)

---

## 4.1 Unit Tests (Backend)

```bash
# Framework: pytest + pytest-asyncio
pytest backend/tests/unit/ -v --cov=app --cov-report=html

# Modules:
# test_auth.py           : hash/verify password, JWT encode/decode, token expiry
# test_fen_builder.py    : mapping 8x8 matrix -> FEN string (edge cases)
# test_elo.py            : ELO calculation K-factor (win/draw/loss theo rating band)
# test_swiss.py          : Swiss Monrad pairing algorithm correctness
# test_payment.py        : invoice generation, VNPay/MoMo signature verification, idempotency
# test_grading.py        : auto AI grading (move matching), manual grading API
# test_confidence.py     : FEN candidate validation pipeline
```

---

## 4.2 Integration Tests (API)

```bash
# Framework: pytest + httpx (AsyncClient)
pytest backend/tests/integration/ -v

# Scenarios:
# test_auth_flow.py         : register -> login -> access protected -> refresh -> logout
# test_facebook_auth.py     : mock Facebook OAuth -> login -> tạo user mới với facebook_id
# test_scan_pipeline.py     : upload PDF -> process -> review FEN -> approve -> save puzzle
# test_grading_flow.py      : nộp bài -> auto AI grade -> teacher manual grade -> student xem kết quả
# test_payment_level1.py    : create invoice -> xem QR -> admin confirm -> verify paid
# test_payment_webhook.py   : mock VNPay webhook -> verify signature -> auto update paid
# test_tournament_flow.py   : create -> register players -> generate pairings -> play game -> standings
# test_puzzle_solutions.py  : tạo puzzle -> thêm nhiều solutions -> student match -> check grading
```

---

## 4.3 AI Model Accuracy Tests

### 4.3.1 Board Detection Test (Sprint 3A)
```bash
python backend/tests/test_board_detection.py \
  --dataset ./test_data/page_images/ \
  --ground-truth ./test_data/board_bboxes.json

# Target:
# Board detection accuracy >= 99%
# Xử lý được ảnh scan nghiêng ±15°, ảnh mờ, nhiều bàn cờ/trang
# Confidence score calibrated (confidence cao = accuracy cao thực tế)
```

### 4.3.2 Perspective Transform Test (Sprint 3B)
```bash
python backend/tests/test_board_rectifier.py \
  --dataset ./test_data/board_crops/

# Target:
# Cell alignment error < 2px
# 64 ô được cắt đúng vị trí a8-h1
```

### 4.3.3 Piece Classification Test (Sprint 3C)
```bash
python backend/tests/test_piece_classifier.py \
  --dataset ./test_data/cells/ \
  --ground-truth ./test_data/cell_labels.json

# Output: Accuracy (correct_cells/total_cells), per-piece Precision/Recall/F1
# Target: >= 95% accuracy per cell
# Output per class:
# Class     Precision  Recall  F1
# K (white)  0.99      0.98    0.985
# Q (white)  0.97      0.96    0.965
# ...
# empty      0.99      0.99    0.99
```

### 4.3.4 Full Pipeline Test (End-to-end AI)
```bash
python backend/tests/test_full_pipeline.py \
  --pdf ./test_data/chess_books/

# Test các loại sách:
# - Sách đen trắng scan
# - Sách màu chụp ảnh
# - Sách cổ điển (quân cờ kiểu classic)
# - Sách hiện đại (quân cờ kiểu modern/minimalist)
# - Trang có nhiều bàn cờ
# - Trang có bàn cờ kích thước nhỏ
```

---

## 4.4 E2E Tests (Playwright)

```bash
npx playwright test --reporter=html

# Specs:
# teacher_scan_pdf.spec.ts    : Upload PDF -> wait AI -> xem bounding box -> review FEN
#                               -> sửa ô confidence thấp -> approve -> save puzzle
# teacher_grade.spec.ts       : Xem danh sách bài nộp -> click vào bài -> xem replay nước đi
#                               -> nhập điểm + nhận xét -> lưu -> student thấy feedback
# student_practice.spec.ts    : Login -> open assignment -> play correct move
#                               -> thấy "Hệ thống tự động chấm: X điểm" (auto AI)
# student_manual_grade.spec.ts: Login -> xem bài đã chấm tay -> thấy tên GV + điểm + feedback
# payment_level1.spec.ts      : Admin tạo hóa đơn -> Parent xem QR -> Admin xác nhận -> status = paid
# payment_vnpay.spec.ts       : Parent click pay -> redirect to VNPay sandbox -> return URL -> verify paid
# tournament_game.spec.ts     : 2 browsers -> join game -> play moves -> verify PGN recorded -> ELO updated
# facebook_login.spec.ts      : Click "Đăng nhập Facebook" -> mock OAuth -> redirect -> logged in
```

---

## 4.5 Load Test (Locust)

```bash
locust -f backend/tests/load/locustfile.py \
  --host http://localhost:8000 \
  --users 500 --spawn-rate 50 --run-time 5m

# Targets:
# P95 latency < 500ms cho tất cả REST API
# Error rate < 1%
# WebSocket game sync < 100ms per move
# AI scan job: queue và xử lý background, không block API response
```

```python
# locustfile.py — Các task chính
class TeacherUser(HttpUser):
    tasks = [upload_pdf, view_analytics, grade_assignment]
    wait_time = between(1, 3)

class StudentUser(HttpUser):
    tasks = [get_assignments, submit_progress, view_leaderboard]
    wait_time = between(0.5, 2)

class TournamentPlayer(HttpUser):
    tasks = [register_tournament, play_game_ws]
    wait_time = between(0.1, 0.5)
```

---

## 4.6 UAT (User Acceptance Testing)

| # | Người dùng | Kịch bản kiểm thử | Tiêu chí đạt |
|---|---|---|---|
| 1 | Giáo viên | Upload sách cờ 50 trang PDF | AI nhận diện >= 90% bàn cờ đúng; hiển thị đúng ô confidence thấp |
| 2 | Giáo viên | Chấm điểm 10 bài học sinh | Điểm và feedback lưu đúng; học sinh thấy ngay sau khi giáo viên lưu |
| 3 | Học sinh | Giải 10 bài toán liên tiếp | Không crash, ELO cập nhật đúng, AI chấm đúng |
| 4 | Học sinh | Xem kết quả bài được GV chấm tay | Thấy tên GV, điểm, feedback rõ ràng |
| 5 | Phụ huynh | Thanh toán học phí (Level 1: QR) | QR hiển thị đúng mã hóa đơn; Admin xác nhận → status = paid |
| 6 | Phụ huynh | Thanh toán học phí qua MoMo | Giao dịch thành công, nhận hóa đơn PDF |
| 7 | Admin | Xem báo cáo doanh thu tháng 9 | Số liệu tổng khớp với `SUM(invoices.amount WHERE status='paid')` |
| 8 | 2 học sinh | Thi đấu Blitz 5+3 online | Không lag, kết quả PGN ghi đúng, ELO cập nhật cả hai |
| 9 | Giáo viên | Đăng nhập bằng Facebook | Tài khoản tạo đúng với facebook_id; không tạo duplicate account |
