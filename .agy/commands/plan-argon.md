---
description: Lập kế hoạch kiến trúc với Argon (không sửa file)
model: gemini-4-argon-medium
---

# Lệnh tắt: /plan-argon

Phân tích kiến trúc sâu và lập kế hoạch sửa code chi tiết cho yêu cầu: $ARGUMENTS

## Nguyên tắc thực hiện:
- **KHÔNG SỬA FILE**: Tuyệt đối không chỉnh sửa, tạo mới hoặc xóa bất kỳ file mã nguồn nào trong quá trình thực hiện lệnh này.
- **CHỈ ĐỌC FILE**: Chỉ sử dụng công cụ đọc file (`view_file`, tìm kiếm code) để đọc các file liên quan trực tiếp đến yêu cầu trong `$ARGUMENTS`.

## Quy trình lập kế hoạch:

1. **Khảo sát mã nguồn liên quan:**
   - Tìm và đọc các file liên quan đến yêu cầu `$ARGUMENTS` trong frontend (`frontend/src/`), backend (`backend/app/`), hoặc test (`frontend/e2e/`).

2. **Phân tích kiến trúc & Đánh giá tác động:**
   - Phân tích luồng dữ liệu (data flow), API contract, schema và các thành phần liên quan.
   - Nhận diện rủi ro tiềm ẩn hoặc các điểm cần lưu ý.

3. **Lập kế hoạch triển khai từng bước:**
   - Liệt kê danh sách các file cụ thể cần sửa hoặc tạo mới.
   - Trình bày chi tiết từng bước thực hiện theo thứ tự hợp lý (Backend -> Frontend -> Test).

4. **Dừng lại để chuyển giao thực thi:**
   - Kết thúc kế hoạch và thông báo để người dùng chuyển về model Flash thực thi viết code theo kế hoạch đã vạch ra.
