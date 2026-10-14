---
name: cams-backend-development
description: >
  Quy trình chuẩn implement API endpoint trong CAMS.
  Dùng khi cams-backend nhận task tạo/sửa API, service, hoặc endpoint FastAPI.
  Không dùng cho task chỉ đọc/review code.
---

# CAMS Backend Development Skill

Quy trình step-by-step khi implement hoặc sửa đổi backend API/service trong CAMS.

## Source of Truth

- `docs/01-sdlc/SDLC.md` → tech stack, roadmap
- `docs/02-architecture/02_system_design.md` → DB schema, API design
- `docs/02-architecture/PAYMENT_ARCHITECTURE.md` → khi task liên quan payment
- `docs/02-architecture/AI_SCANNER_ARCHITECTURE.md` → khi task liên quan AI pipeline

## Stack

- Python 3.11+, FastAPI, Pydantic v2, SQLAlchemy 2.0, Alembic
- PostgreSQL 16, Redis 7, MinIO (S3-compatible)
- Background: Celery-style worker hoặc FastAPI BackgroundTasks

## Quy trình Implementation

### Bước 1 — Đọc contract / requirement

1. Đọc Context Packet từ Orchestrator (task_id, objective, acceptance_criteria).
2. Đọc docs liên quan trong `docs/` — **không implement trước khi hiểu requirement**.
3. Xác định: endpoint nào? HTTP method? Input/Output schema? Authorization level?

### Bước 2 — Kiểm tra hiện trạng

1. Kiểm tra schema DB hiện tại trong `backend/app/models/`.
2. Kiểm tra service/route đã có chưa (tránh duplicate).
3. Kiểm tra dependency: có cần migration trước không? Có cần service khác chạy trước không?

### Bước 3 — Thiết kế Pydantic DTO

1. Tạo request/response schema trong `backend/app/schemas/`.
2. Schema phải match với DB model và API contract trong `02_system_design.md`.
3. Dùng Pydantic v2 syntax (`model_validator`, `field_validator`).
4. Không dùng `Any` trừ khi có lý do rõ ràng.

### Bước 4 — Implement Service Layer

1. Tạo/sửa service trong `backend/app/services/`.
2. Business logic nằm ở service, **không ở route handler**.
3. Service nhận DB session qua dependency injection.
4. Xử lý error rõ ràng (raise HTTPException hoặc custom exception).

### Bước 5 — Implement Route/Endpoint

1. Tạo/sửa route trong `backend/app/api/`.
2. Route chỉ: nhận request → gọi service → trả response.
3. Thêm dependency auth/RBAC phù hợp.
4. Response model phải match Pydantic schema.

### Bước 6 — Validation & Error Handling

1. Input validation qua Pydantic.
2. Business validation trong service (duplicate check, permission, state check).
3. Error response phải có message hữu ích nhưng không lộ internal/secret.

### Bước 7 — Viết Test

1. Unit test cho service logic.
2. Integration test cho endpoint (TestClient + test DB).
3. Test cả happy path và edge cases.
4. Test auth/permission nếu endpoint có RBAC.

### Bước 8 — Tự kiểm tra

1. Chạy `pytest` cho tests liên quan.
2. Kiểm tra linter/type errors nếu có.
3. Xác nhận migration chạy được (nếu có schema change).

### Bước 9 — Báo cáo Result Contract

Báo cáo theo đúng format `05-result-contract.md`:

```
STATUS: DONE | FAILED | BLOCKED | PARTIAL
SCOPE: ...
CHANGES: ...
TESTS: ...
RISKS: ...
DEPENDENCIES: ...
BLOCKERS: ...
NEXT_ACTION: ...
```

## Quy tắc bổ sung

- Không hard-code secret — dùng `.env` / `Settings`.
- Không sửa DB schema trực tiếp — phải qua Alembic migration.
- Nếu cần thay đổi API contract đã có, đề xuất rõ ràng cho Architect/Orchestrator.
- Logging cho action quan trọng (payment, auth, data mutation).
- Mọi endpoint phải trả JSON response nhất quán.
