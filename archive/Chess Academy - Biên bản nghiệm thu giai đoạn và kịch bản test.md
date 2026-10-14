# Chess Academy (CAMS) - Biên bản nghiệm thu giai đoạn và kịch bản test

*Bản mẫu, điều chỉnh theo quy định nội bộ của đơn vị.*

## Phần 1. Biên bản nghiệm thu giai đoạn

**BIÊN BẢN NGHIỆM THU GIAI ĐOẠN**

**Dự án:** Hệ thống Chess Academy (CAMS) **Giai đoạn nghiệm thu:** Đợt ... (từ ...../...../...... đến ...../...../......) **Môi trường thử nghiệm:** Máy chủ thử nghiệm (Oracle Cloud free tier), địa chỉ: ....................... **Phiên bản:** v...... (commit/tag: CAMS-........) **Ngày nghiệm thu:** ...../...../......

### 1. Thành phần tham dự

| STT | Họ tên | Chức danh / Đơn vị | Vai trò |
| --- | --- | --- | --- |
| 1 |  |  | Bên phát triển |
| 2 |  |  | Người sử dụng / kiểm thử |
| 3 |  |  | Đại diện phê duyệt |

### 2. Phạm vi nghiệm thu giai đoạn này

| STT | Chức năng | Trạng thái | Kết quả |
| --- | --- | --- | --- |
| 1 | Đăng nhập, phân quyền (học viên, giáo viên, quản trị) | Hoàn thành | Đạt / Không đạt |
| 2 | Quản lý lớp học | Hoàn thành | Đạt / Không đạt |
| 3 | Giao và làm bài tập cờ (puzzle, mate in N) | Hoàn thành | Đạt / Không đạt |
| 4 | Chấm điểm tự động bằng Stockfish, cập nhật Puzzle Rating | Hoàn thành | Đạt / Không đạt |
| 5 | Quét bài tập từ tài liệu PDF | Hoàn thành | Đạt / Không đạt |
| 6 | ...... | Chưa hoàn thành, không thuộc phạm vi đợt này | Không nghiệm thu |

### 3. Chức năng chưa nằm trong phạm vi (dự kiến các đợt sau)

| STT | Chức năng | Dự kiến hoàn thành |
| --- | --- | --- |
| 1 |  | ...../...../...... |
| 2 |  | ...../...../...... |

### 4. Tổng hợp kết quả kiểm thử

| Chỉ tiêu | Số lượng |
| --- | --- |
| Tổng số kịch bản test |  |
| Đạt |  |
| Không đạt |  |
| Lỗi đã sửa trong đợt |  |
| Lỗi còn tồn tại (kèm mức độ) |  |

### 5. Danh sách lỗi còn tồn tại và hướng xử lý

| Mã lỗi | Mô tả | Mức độ (Nghiêm trọng / Trung bình / Nhẹ) | Người xử lý | Hạn xử lý |
| --- | --- | --- | --- | --- |
| BUG-001 |  |  |  |  |

### 6. Ý kiến của các bên

- Bên sử dụng: ................................................................
- Bên phát triển: ................................................................

### 7. Kết luận

☐ Nghiệm thu đạt, chuyển sang giai đoạn tiếp theo. ☐ Nghiệm thu có điều kiện, sửa các lỗi nêu tại mục 5 trước ngày ...../...../...... ☐ Không nghiệm thu, thực hiện lại kiểm thử sau khi sửa lỗi.

### 8. Chữ ký

| Bên phát triển | Người sử dụng / kiểm thử | Đại diện phê duyệt |
| --- | --- | --- |
| (Ký, ghi rõ họ tên) | (Ký, ghi rõ họ tên) | (Ký, ghi rõ họ tên) |

## Phần 2. Kịch bản kiểm thử (mẫu)

**Cách dùng:** mỗi kịch bản có mã riêng, người test ghi kết quả thực tế và đánh dấu Đạt hoặc Không đạt. Nếu không đạt, ghi mã lỗi (BUG-xxx) và đính kèm ảnh chụp màn hình.

### A. Tài khoản và phân quyền

| Mã | Các bước thực hiện | Kết quả mong đợi | Kết quả thực tế | Đạt / Không đạt |
| --- | --- | --- | --- | --- |
| TC-A01 | Đăng nhập bằng tài khoản học viên hợp lệ | Vào được trang học viên |  |  |
| TC-A02 | Đăng nhập sai mật khẩu | Báo lỗi rõ ràng, không vào được |  |  |
| TC-A03 | Học viên truy cập đường dẫn của trang quản trị | Bị từ chối truy cập |  |  |
| TC-A04 | Đăng xuất rồi bấm nút Back của trình duyệt | Không xem lại được nội dung cần đăng nhập |  |  |

### B. Quản lý lớp học

| Mã | Các bước thực hiện | Kết quả mong đợi | Kết quả thực tế | Đạt / Không đạt |
| --- | --- | --- | --- | --- |
| TC-B01 | Giáo viên tạo lớp mới | Lớp xuất hiện trong danh sách |  |  |
| TC-B02 | Thêm học viên vào lớp | Học viên thấy lớp trong tài khoản của mình |  |  |
| TC-B03 | Xóa học viên khỏi lớp | Học viên không còn thấy lớp |  |  |
| TC-B04 | Sửa tên lớp | Tên mới hiển thị ở mọi nơi |  |  |

### C. Làm bài tập cờ

| Mã | Các bước thực hiện | Kết quả mong đợi | Kết quả thực tế | Đạt / Không đạt |
| --- | --- | --- | --- | --- |
| TC-C01 | Mở bài Mate in 1, đi đúng nước chiếu hết | Báo chính xác, được điểm |  |  |
| TC-C02 | Mở bài Mate in 1, đi nước sai | Báo không chính xác, cho thử lại |  |  |
| TC-C03 | Mở bài Mate in 3, đi đúng nước 1, máy đáp trả, đi tiếp đúng | Hoàn thành bài, được điểm |  |  |
| TC-C04 | Mở bài Mate in 3, đi nước đầu khác đáp án nhưng vẫn là mate nhanh nhất | Hệ thống xử lý đúng theo quy ước (chấp nhận hoặc từ chối, ghi rõ) |  |  |
| TC-C05 | Bấm Gợi ý (Hint) | Hiển thị gợi ý, không tiết lộ toàn bộ đáp án |  |  |
| TC-C06 | Bấm Đặt lại giữa chừng | Bàn cờ về thế ban đầu |  |  |
| TC-C07 | Đi nước không hợp lệ (kéo quân sai luật) | Quân trở về chỗ cũ, không tính lượt |  |  |
| TC-C08 | Làm lại câu sai khi còn hạn và còn lượt thử | Tính điểm đúng theo quy tắc đã thống nhất (nêu rõ quy tắc trong biên bản) |  |  |
| TC-C09 | Làm lại khi đã hết hạn nộp hoặc hết số lần thử | Hệ thống từ chối, báo rõ lý do |  |  |

### D. Chấm điểm và xếp hạng

| Mã | Các bước thực hiện | Kết quả mong đợi | Kết quả thực tế | Đạt / Không đạt |
| --- | --- | --- | --- | --- |
| TC-D01 | Làm bài 10 câu, đúng 8, sai 2 | Điểm hiển thị 8/10 |  |  |
| TC-D02 | Làm lại 2 câu sai, nay đúng cả hai | Điểm theo đúng quy tắc (10/10 nếu tính kết quả mới nhất) |  |  |
| TC-D03 | Hoàn thành bài, kiểm tra Puzzle Rating | Rating được cập nhật hợp lý |  |  |
| TC-D04 | Giáo viên xem bảng điểm lớp | Số liệu khớp với điểm từng học viên |  |  |

### E. Quét bài từ PDF

| Mã | Các bước thực hiện | Kết quả mong đợi | Kết quả thực tế | Đạt / Không đạt |
| --- | --- | --- | --- | --- |
| TC-E01 | Tải lên PDF có sơ đồ cờ rõ nét | Nhận diện đủ quân, thế cờ khớp với ảnh gốc |  |  |
| TC-E02 | So sánh thế cờ nhận diện với trang gốc | Không thiếu hoặc thừa quân |  |  |
| TC-E03 | Kiểm tra đáp án sinh ra cho bài Mate in N | Dãy nước hợp lệ, đúng số nước, Stockfish xác nhận là mate |  |  |
| TC-E04 | Tải lên PDF chất lượng thấp hoặc ảnh mờ | Hệ thống cảnh báo hoặc đánh dấu bài cần duyệt thủ công |  |  |

### F. Giao diện, tương thích, hiệu năng

| Mã | Các bước thực hiện | Kết quả mong đợi | Kết quả thực tế | Đạt / Không đạt |
| --- | --- | --- | --- | --- |
| TC-F01 | Mở trên Chrome và Edge | Hiển thị và thao tác bình thường |  |  |
| TC-F02 | Mở trên điện thoại (trình duyệt hoặc app) | Bàn cờ vừa màn hình, kéo thả quân được |  |  |
| TC-F03 | 5 đến 10 người cùng làm bài | Không treo, phản hồi dưới vài giây |  |  |
| TC-F04 | Mất mạng giữa chừng rồi kết nối lại | Không mất dữ liệu đã nộp, báo lỗi rõ ràng |  |  |

### G. Bảo mật cơ bản

| Mã | Các bước thực hiện | Kết quả mong đợi | Kết quả thực tế | Đạt / Không đạt |
| --- | --- | --- | --- | --- |
| TC-G01 | Truy cập qua HTTPS | Có chứng chỉ, không cảnh báo |  |  |
| TC-G02 | Thử đổi mã bài tập hoặc mã học viên trên đường dẫn | Không xem được dữ liệu của người khác |  |  |
| TC-G03 | Kiểm tra tài khoản mặc định | Đã đổi mật khẩu mặc định |  |  |

## Phần 3. Mẫu phiếu báo lỗi

| Trường | Nội dung |
| --- | --- |
| Mã lỗi | BUG-... |
| Người báo |  |
| Ngày giờ |  |
| Chức năng / mã kịch bản liên quan | TC-... |
| Các bước tái hiện | 1. ... 2. ... 3. ... |
| Kết quả mong đợi |  |
| Kết quả thực tế |  |
| Mức độ | Nghiêm trọng / Trung bình / Nhẹ |
| Ảnh chụp màn hình | (đính kèm) |
| Trạng thái | Mới / Đang sửa / Đã sửa / Đã kiểm tra lại |
