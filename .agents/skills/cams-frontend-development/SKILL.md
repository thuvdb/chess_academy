---
name: cams-frontend-development
description: >
  Quy trình chuẩn implement UI component/page trong CAMS web app.
  Dùng khi cams-frontend nhận task tạo/sửa React component, page, hoặc admin dashboard.
  Không dùng cho mobile (React Native).
---

# CAMS Frontend Development Skill

Quy trình step-by-step khi implement hoặc sửa đổi frontend web trong CAMS.

## Source of Truth

- `docs/02_system_design.md` §2.6 → Screen Map & UI Flow
- `docs/02_system_design.md` §2.4 → API Specification (contract với backend)
- `docs/01_requirements.md` → User Stories

## Stack

- React 18+, TypeScript, Vite
- Tailwind CSS
- React Query (TanStack Query) cho server state
- Zustand cho client state (khi cần)
- Form: React Hook Form + Zod validation

## Quy trình Implementation

### Bước 1 — Đọc requirement & API contract

1. Đọc Context Packet từ Orchestrator.
2. Xác định: page/component nào? User role nào? Dữ liệu từ API nào?
3. Đọc API contract trong `02_system_design.md` hoặc backend schemas.
4. Xác định: có API endpoint sẵn chưa? Nếu chưa → báo dependency cho Orchestrator.

### Bước 2 — Kiểm tra hiện trạng

1. Kiểm tra component/page đã có chưa (tránh duplicate).
2. Kiểm tra shared components có thể tái sử dụng.
3. Kiểm tra routing hiện tại.

### Bước 3 — Component Design

1. Tách thành component nhỏ, rõ trách nhiệm.
2. Props interface phải TypeScript strict (không dùng `any`).
3. Phân biệt:
   - **Server state** → React Query (`useQuery`, `useMutation`)
   - **Client state** → `useState` hoặc Zustand
4. Không duplicate logic gọi API trong nhiều component — tạo custom hook.

### Bước 4 — Implement UI

1. Dùng Tailwind CSS cho styling.
2. Responsive là yêu cầu mặc định (mobile-first).
3. Accessibility: aria-labels, keyboard navigation, focus states.
4. Loading states, error states, empty states đều phải handle.

### Bước 5 — Form & Validation

1. Form dùng React Hook Form.
2. Validation schema dùng Zod — match với backend Pydantic schema.
3. Error message phải user-friendly (tiếng Việt cho CAMS users).
4. Disable submit khi đang loading.

### Bước 6 — API Integration

1. API calls qua React Query hooks.
2. Optimistic updates khi phù hợp.
3. Error handling: toast notification hoặc inline error.
4. Không hard-code API base URL — dùng env config.

### Bước 7 — Test

1. Component test nếu logic phức tạp.
2. Kiểm tra UI render đúng với mock data.
3. Kiểm tra responsive trên các breakpoint.
4. Kiểm tra accessibility cơ bản.

### Bước 8 — Báo cáo Result Contract

```
STATUS: DONE | FAILED | BLOCKED | PARTIAL
SCOPE: Component/page/feature
CHANGES: Files cụ thể
TESTS: Component tests, manual verification
RISKS: ...
DEPENDENCIES: API endpoints cần
BLOCKERS: ...
NEXT_ACTION: QA review
```

## Quy tắc bổ sung

- Không thay đổi backend contract chỉ để tiện frontend — nếu thiếu, đề xuất rõ ràng.
- Dùng TypeScript strict mode — không tắt type checking.
- CAMS UI hỗ trợ tiếng Việt — text phải sẵn sàng cho i18n.
- Chess UI (bàn cờ, quân cờ) dùng library chuyên dụng (chessground hoặc tương đương).
