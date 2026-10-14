---
name: cams-payment-development
description: >
  Quy trình chuẩn implement payment feature trong CAMS.
  Dùng khi cams-payment nhận task liên quan invoice, VietQR, payment state, webhook, hoặc reconciliation.
  Bắt buộc đọc PAYMENT_ARCHITECTURE.md trước khi implement.
---

# CAMS Payment Development Skill

Quy trình step-by-step khi implement hoặc sửa đổi payment feature trong CAMS.

## Source of Truth

- `docs/02-architecture/PAYMENT_ARCHITECTURE.md` → **Bắt buộc đọc trước khi bắt đầu**
- `docs/02-architecture/02_system_design.md` §2.2 → Payment tables trong DB schema
- `docs/01-sdlc/01_requirements.md` → Payment user stories

## 3 Level Payment CAMS

```
Level 1 — MVP (bắt buộc cho v1.5)
  Static VietQR + mã hóa đơn + Admin xác nhận thủ công

Level 2 — Automation (optional, v2.5)
  QR + dịch vụ nhận diện giao dịch + Webhook + CAMS tự động PAID

Level 3 — Full Gateway (optional, v3.0)
  VNPay / MoMo / ZaloPay → Payment Service → Unified API
```

> **QUAN TRỌNG:** Không biến Level 2/3 thành dependency của MVP trừ khi được yêu cầu rõ ràng.

## Quy trình Implementation

### Bước 1 — Xác định Level

1. Đọc Context Packet → xác định task thuộc Level nào.
2. Đối chiếu với `PAYMENT_ARCHITECTURE.md` §Level tương ứng.
3. Nếu task yêu cầu Level 2/3 mà chưa có Level 1 → báo BLOCKED.

### Bước 2 — Payment State Machine

Tuân thủ state machine trong `PAYMENT_ARCHITECTURE.md`:

```
PENDING → SUCCESS (Level 1: admin confirm / Level 2: webhook / Level 3: gateway)
PENDING → FAILED
PENDING → EXPIRED (quá due_date)
SUCCESS → REFUND_REQUESTED → REFUNDED
```

- **KHÔNG** transition bỏ qua state (vd PENDING → REFUNDED).
- **KHÔNG** đánh dấu PAID chỉ dựa trên dữ liệu client.
- Mỗi transition phải ghi audit log.

### Bước 3 — Invoice Logic

1. Invoice tạo trước Payment record.
2. Invoice number format: `INV-{center_id_short}-{YYYYMM}-{seq}`.
3. Invoice phải có: student, class, period, amount, due_date.
4. Một invoice có thể có nhiều payment attempts.

### Bước 4 — VietQR Generation (Level 1)

1. QR encode theo chuẩn VietQR (NAPAS).
2. Nội dung chuyển khoản chứa mã invoice để đối soát.
3. QR là static — không có callback tự động.
4. Admin xác nhận thủ công qua admin UI.

### Bước 5 — Webhook/Callback (Level 2/3)

1. Webhook endpoint phải verify signature/checksum trước khi xử lý.
2. Webhook phải idempotent — gọi 2 lần cùng transaction không tạo duplicate.
3. Log toàn bộ webhook payload (masked sensitive data).
4. Timeout/retry: webhook nhà cung cấp có thể gọi lại → handle gracefully.

### Bước 6 — Security

1. Không lưu credit card / bank account detail trong DB.
2. Secret key (API key nhà cung cấp) phải nằm trong `.env`, không hard-code.
3. Payment endpoints phải có auth + RBAC (admin/teacher tạo invoice, admin confirm payment).
4. Webhook endpoint: verify signature, whitelist IP nếu có.

### Bước 7 — Test

1. Unit test cho state machine transitions.
2. Unit test cho invoice creation logic.
3. Test VietQR generation (format, encoding).
4. Test webhook idempotency.
5. Test authorization (role-based access).

### Bước 8 — Báo cáo Result Contract

```
STATUS: DONE | FAILED | BLOCKED | PARTIAL
SCOPE: Level mấy, feature nào
CHANGES: Files cụ thể
TESTS: State machine tests, webhook tests, auth tests
RISKS: Webhook idempotency, reconciliation gaps
DEPENDENCIES: DB migration, backend service
BLOCKERS: ...
NEXT_ACTION: QA integration test → Security review
```

## Quy tắc bổ sung

- Payment luôn cần **Security review** sau implementation.
- Reconciliation (đối soát) là feature Level 2+ — không bắt buộc Level 1.
- Mọi thay đổi payment state phải traceable (who, when, how).
