# Đề xuất tối ưu quy trình e-learning: Luyện tập và Bài tập về nhà

Dự án Chess Academy. Tài liệu này tổng hợp phân tích và đề xuất cho ba yêu cầu: tách chế độ luyện tập với bài tập về nhà, xác định chốt chặn khi cho sinh viên đi sai đáp án, và khóa cứng việc nộp bài.

## 1. Vấn đề hiện tại

Hệ thống đang dùng **một cơ chế cho hai mục đích khác nhau**. Cơ chế "đi sai là chặn, phải làm lại" hợp với luyện tập vì phản hồi tức thì giúp học. Nhưng nó không hợp để đánh giá: giáo viên chỉ nhìn thấy kết quả cuối đã đúng, còn quá trình sai, chính là thứ cho biết sinh viên thiếu kỹ năng nào, thì bị che mất.

Hướng đề xuất là đúng và là cách thiết kế chuẩn: **luyện tập thì chặn, bài tập về nhà thì cho đi tiếp để quan sát và chẩn đoán**.

## 2. Tách hai chế độ

|  | Luyện tập | Bài tập về nhà |
| --- | --- | --- |
| Mục đích | Học, sửa lỗi ngay | Đo năng lực, chẩn đoán |
| Nước sai | Chặn, báo sai, cho làm lại | Cho đi tiếp, **không báo đúng/sai ngay** |
| Gợi ý | Có, tăng dần (tô quân, chỉ ô, lộ nước đi) | Không có hoặc bị trừ điểm |
| Dữ liệu ghi | Cơ bản | Toàn bộ nước đi, thời gian mỗi nước, số lần làm lại |

## 3. Chốt chặn khi cho sinh viên đi sai

Cho đi tiếp không có nghĩa là đi vô hạn. Mỗi bài cần có **mục tiêu** và **ngân sách nước đi**. Bài kết thúc khi gặp điều kiện đầu tiên trong các điều kiện sau:

- Đạt mục tiêu của bài.
- Hết ngân sách: số nước tối đa của sinh viên bằng độ dài đáp án cộng 1 hoặc 2.
- Thế cờ kết thúc (chiếu hết, hòa, hết nước).
- Mất lợi thế nghiêm trọng: engine thấy sinh viên mất quân nặng hoặc đánh giá tụt mạnh. Hệ thống dừng bài và ghi nhận "mất lợi thế".
- Sinh viên bấm "Chốt bài / Bài tiếp", hoặc hết giờ của bài.

### Mục tiêu và chốt chặn theo loại bài

Giáo viên khai báo mục tiêu khi soạn bài:

| Loại bài | Mục tiêu | Chốt chặn |
| --- | --- | --- |
| Chiếu hết trong N nước | Chiếu hết | Tối đa N+1 nước của sinh viên |
| Chiến thuật ăn quân (Pin, Fork, Double Attack, Skewer) | Thắng vật chất từ X điểm trở lên | Đi đúng đáp án là đạt, kết thúc ngay. Nếu lệch, tối đa độ dài đáp án + 1 nước |
| Giành lợi thế vị trí (không có đòn buộc) | Engine đánh giá từ ngưỡng đặt trước trở lên | Số nước cố định |
| Tàn cuộc | Thắng hoặc hòa theo lý thuyết | Tối đa N nước hoặc đến khi kết quả rõ |

Với bài Pin, Fork, Double Attack, nếu sinh viên đi đúng theo đáp án thì bài kết thúc. Phần "cho đi sai" chỉ cần khi sinh viên lệch đáp án.

### Hai điểm kỹ thuật cần quyết định

- **Ai đi quân đối phương sau khi lệch đáp án?** Đáp án chỉ có nhánh chuẩn nên sau khi lệch không còn nước đáp sẵn. Nên dùng Stockfish ở độ sâu thấp đi thay. Cách đơn giản hơn là dừng bài ngay tại nước lệch đầu tiên và chấm từ đó.
- **Nhiều đáp án đúng.** Không nên chỉ so khớp một đường đáp án. Nên chấp nhận nước đi mà engine đánh giá tương đương (cùng chiếu hết hoặc chênh lệch nhỏ) và đánh dấu để giáo viên duyệt. Như vậy hệ thống không trừ điểm oan những nước đúng khác đáp án.

## 4. Chấm điểm và chẩn đoán kỹ năng

- **Chấm theo bậc** thay vì đúng/sai: đúng toàn bộ hoặc tương đương được điểm đầy đủ. Đúng ý tưởng nhưng chưa hoàn thành (ví dụ đúng nước đầu) được một phần. Lệch ngay từ đầu được 0. Dùng gợi ý thì bị trừ.
- **Gắn thẻ kỹ năng** cho mỗi bài (pin, fork, mẫu chiếu hết, an toàn vua...) và phân loại lỗi bằng engine: bỏ lỡ đòn, treo quân, bỏ qua nước chiếu, đi sai ý tưởng.
- **Bảng kỹ năng**: giáo viên xem từng sinh viên và cả lớp yếu ở nhóm nào.
- **Khép vòng**: bài làm sai trong bài tập về nhà tự động đưa vào danh sách luyện tập của chính sinh viên đó. Bài tập (chẩn đoán) nuôi phần luyện tập (khắc phục).

## 5. Nộp bài khóa cứng

Dùng ba trạng thái: **Chưa làm → Đang làm (tự lưu nháp) → Đã nộp (khóa)**.

- Hoàn thành hết các bài **không tự nộp**. Hệ thống chỉ hiện nút "Nộp bài", kèm hộp xác nhận "không thể sửa sau khi nộp".
- Khi còn ở trạng thái "Đang làm", sinh viên vẫn làm lại được. Hệ thống lưu mọi lần làm, tính điểm theo lần cuối lúc nộp, còn giáo viên xem được toàn bộ lịch sử.
- Khóa phải kiểm tra **ở phía server**: sau khi `submitted`, mọi API ghi bài đều bị từ chối. Chỉ ẩn nút trên giao diện thì chưa đủ.
- **Tự động nộp khi hết hạn** bằng tác vụ định kỳ của Celery (dự án đã có Celery Beat), dùng giờ máy chủ theo múi giờ Việt Nam, không dùng giờ máy sinh viên.
- Nên có chức năng **giáo viên mở lại bài** (kèm nhật ký ai mở, lúc nào, lý do) cho trường hợp sinh viên bấm nhầm hoặc sự cố mạng. Sinh viên không tự mở lại được.

## 6. Thứ tự triển khai gợi ý

1. Khóa nộp bài (dễ, rủi ro thấp, tác dụng rõ).
2. Chế độ bài tập cho đi tiếp với ngân sách nước đi.
3. Engine chấm điểm, chấp nhận đáp án tương đương, gắn thẻ kỹ năng.
4. Bảng kỹ năng và tự động giao bài luyện bổ trợ.

## 7. Câu hỏi cần làm rõ

- Quy tắc "cho sửa 3 lần" hiện tính **theo từng bài** hay **theo cả bài tập**? Tài liệu này tạm hiểu là theo từng bài.
- Sau khi sinh viên lệch đáp án, hệ thống dừng bài ngay hay để engine đi quân đối phương tiếp?
- Ngưỡng "mất lợi thế nghiêm trọng" và ngưỡng đánh giá cho bài giành lợi thế vị trí do ai quyết định: giáo viên khai báo cho từng bài hay đặt mặc định chung?
