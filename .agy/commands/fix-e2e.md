---
description: Sửa lỗi test Playwright trong frontend/e2e/
model: gemini-4-argon-low
---

# Lệnh tắt: /fix-e2e

Kiểm tra và sửa lỗi các test case Playwright trong thư mục `frontend/e2e/`.

## Quy trình thực hiện:

1. **Xác định lỗi kiểm thử:**
   - Đọc kết quả hoặc chạy test Playwright để xác định test case đang bị fail.
   - Trích xuất thông báo lỗi, stack trace, hoặc locator bị lỗi.

2. **Đối chiếu với mã nguồn giao diện:**
   - Đối chiếu vị trí lỗi trong file test (`frontend/e2e/*.spec.ts`) với component tương ứng trong thư mục `frontend/src/` (ví dụ: `Scanner.tsx`, `Login.tsx`, `Profile.tsx`, `Sidebar.tsx`).
   - Phân tích nguyên nhân gây lỗi: do logic component UI, do selector Playwright (strict mode violation, timing, mobile drawer), hay do API backend.

3. **Sửa trực tiếp:**
   - Chỉnh sửa trực tiếp file test trong `frontend/e2e/` hoặc component trong `frontend/src/` để giải quyết triệt để lỗi.
   - Ưu tiên các giải pháp bền vững (scoped locator, `.first()`, kiểm tra điều kiện responsive mobile/desktop).

4. **Kiểm tra lại:**
   - Chạy lại test case vừa sửa để xác nhận đã chuyển sang trạng thái PASS.
   - Báo cáo ngắn gọn các tệp đã sửa và kết quả.
