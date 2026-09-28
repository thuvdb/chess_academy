---
name: cams-database-change
description: >
  Quy trình chuẩn thay đổi database schema trong CAMS.
  Dùng khi cams-database nhận task tạo/sửa table, index, constraint, hoặc migration.
  Không dùng cho query/report thuần túy.
---

# CAMS Database Change Skill

Quy trình step-by-step khi thay đổi PostgreSQL schema, tạo migration, hoặc tối ưu database trong CAMS.

## Source of Truth

- `docs/02_system_design.md` §2.2 → Schema chính thức
- `docs/PAYMENT_ARCHITECTURE.md` → Payment tables
- `docs/AI_SCANNER_ARCHITECTURE.md` → AI Scanner tables
- `backend/app/models/` → SQLAlchemy models hiện tại

## Quy trình

### Bước 1 — Đọc requirement & contract

1. Đọc Context Packet từ Orchestrator.
2. Xác định: table nào? Column nào? Constraint nào? Index nào?
3. Đối chiếu với schema trong `02_system_design.md`.

### Bước 2 — Kiểm tra hiện trạng

1. Đọc models hiện tại trong `backend/app/models/`.
2. Kiểm tra migration history trong `alembic/versions/`.
3. Xác định: thay đổi này có backward compatible không?
4. Xác định: có FK dependency với table khác không?

### Bước 3 — Phân tích ảnh hưởng

1. Kiểm tra API endpoints nào dùng table/column bị ảnh hưởng.
2. Kiểm tra services, reports, workers nào query table này.
3. Kiểm tra dữ liệu hiện hữu có bị ảnh hưởng không.
4. Nếu thay đổi contract (thêm NOT NULL, đổi FK, đổi type) → báo Orchestrator để Architect review.

### Bước 4 — Thiết kế migration

1. Tạo/sửa SQLAlchemy model trong `backend/app/models/`.
2. Chạy `alembic revision --autogenerate -m "mô tả ngắn"`.
3. Review migration file tự sinh — **không tin hoàn toàn autogenerate**.
4. Nếu cần data migration (đổi type, split column), viết migration thủ công.

### Bước 5 — Xử lý backward compatibility

- **Thêm column nullable** → an toàn, deploy trước API.
- **Thêm column NOT NULL** → cần default value hoặc data migration.
- **Đổi tên column** → cần phối hợp Backend sửa model/query trước.
- **Xóa column** → cần xác nhận không còn code nào dùng.
- **Đổi type** → cần data migration + kiểm tra cast.

### Bước 6 — Test migration

1. Chạy `alembic upgrade head` trên test DB.
2. Kiểm tra `alembic downgrade -1` hoạt động (rollback test).
3. Kiểm tra dữ liệu seed/fixture vẫn hợp lệ.
4. Chạy unit/integration test liên quan.

### Bước 7 — Index & Performance

1. Không over-index — chỉ thêm index cho column có query frequency cao.
2. Composite index theo đúng thứ tự query.
3. Đánh giá ảnh hưởng đến write performance.

### Bước 8 — Báo cáo Result Contract

```
STATUS: DONE | FAILED | BLOCKED | PARTIAL
SCOPE: Table/column/index đã thay đổi
CHANGES: Migration file + model file cụ thể
TESTS: Migration up/down test, integration test
RISKS: Backward compatibility, data loss potential
DEPENDENCIES: API/service cần cập nhật theo
BLOCKERS: ...
NEXT_ACTION: Backend cập nhật model/service
```

## Quy tắc bổ sung

- **KHÔNG** sửa schema trực tiếp mà bỏ qua migration.
- **KHÔNG** drop column/table trước khi xác nhận không còn code dùng.
- Ưu tiên database-level integrity (FK, CHECK, UNIQUE) khi phù hợp.
- CAMS dùng UUID cho PK, TIMESTAMP cho audit fields.
- ENUM trong CAMS: dùng PostgreSQL ENUM type hoặc VARCHAR + CHECK.
