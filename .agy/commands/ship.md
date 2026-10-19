---
description: Commit và git push bằng model Flash
model: gemini-3.8-flash-high
---

# Lệnh tắt: /ship

Thực hiện commit và push thay đổi lên Git repository bằng model Flash nhanh chóng và tối ưu quota.

## Các bước thực hiện:

1. **Kiểm tra trạng thái Git:**
   - Chạy lệnh `git status`.
   - Nếu không có thay đổi nào cần commit (working tree clean), thông báo ngắn gọn và dừng lại.

2. **Stage các tệp thay đổi:**
   - Chạy lệnh `git add .`

3. **Tạo Commit theo chuẩn Conventional Commits tiếng Việt không dấu:**
   - Xem tóm tắt thay đổi qua `git diff --staged --stat`.
   - Tạo thông điệp commit theo chuẩn Conventional Commits tiếng Việt không dấu (ví dụ: `feat(ui): them nut phong to anh`, `fix(api): sua loi avatar endpoint`, `refactor(auth): toi uu ham dang nhap`, `test(e2e): bo sung test case`).
   - Chạy lệnh `git commit -m "<thông điệp commit>"`.

4. **Đẩy mã nguồn lên Remote (Git Push):**
   - Lấy nhánh hiện tại và chạy `git push origin <branch>`.

5. **Báo cáo ngắn gọn:**
   - Báo cáo kết quả ngắn gọn gồm:
     - **Commit hash**
     - **Thông điệp**
     - **Các tệp đã đẩy lên**
