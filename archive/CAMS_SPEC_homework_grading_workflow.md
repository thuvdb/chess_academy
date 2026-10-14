# CAMS – Đặc tả quy trình Bài tập về nhà: giao bài, chấm bài, trả bài (phía giáo viên)

> Tài liệu dành cho AI Agent (Antigravity IDE). Đọc toàn bộ trước khi viết code.
> Dự án: `chess_academy` – backend Python (FastAPI) + PostgreSQL, frontend React (TypeScript).
> Mã nguồn, tên bảng/cột/API: tiếng Anh. Giao diện: tiếng Việt.
> Spec phân quyền đa trung tâm (`CAMS_SPEC_multi_center_rbac_v1.1.md`) **chưa triển khai**; tài liệu này chỉ chuẩn bị sẵn cột `center_id` (mục 3.3), không làm phân quyền.

---

## 0. Quy tắc làm việc cho Agent

1. **Không phỏng đoán.** Trước khi sửa, đọc code thực tế: `backend/app/models/*` (assignment, progress, puzzle), `backend/app/services/progress_service.py`, `puzzle_service.py`, `backend/app/api/endpoints/assignments.py`, và các trang frontend `Assignments`, `Classes`, `Puzzles`. Nếu spec mâu thuẫn với code, **dừng và báo cáo**, không tự quyết.
2. **Kiểm tra quyền ở Backend**, ẩn nút ở Frontend chỉ là UX.
3. **Không hard-code** ngưỡng, số lần, nhãn: đưa vào bảng `settings`/danh mục có giá trị mặc định (mục 7).
4. Mỗi thay đổi schema là một migration Alembic, có rollback; sao lưu `pg_dump` trước khi chạy; chạy dry-run trước.
5. **Không làm lại Stockfish và chấm Elo.** Hai phần này đã có; chỉ tái sử dụng kết quả của chúng.
6. Commit theo quy ước `CAMS-xxxx: <mô tả>`, mỗi bước ở mục 10 là một commit.

---

## 1. Hiện trạng (quan sát từ màn hình thực tế, ngày 13/10/2026)

Bài giao "Tìm các đòn chiến thuật", lớp "Test", 5 thế cờ, học viên Nguyễn Minh Triết đã nộp.

| Quan sát | Phía học viên | Phía giáo viên |
|---|---|---|
| Tiến độ | "5 / 5 thẻ cờ" (đã làm đủ) | Cột "Tiến độ (5)" hiện **1 / 5** |
| Số đúng | "Giải đúng: 1 / 5" | Không hiển thị riêng |
| Điểm | "34 pts" (điểm tích lũy) | "Tổng điểm 34 pts" (cùng giá trị, không tách) |
| Kết quả từng thế cờ | Thấy ngay sau khi nộp: 4 thế "Đã ghi nhận", 1 thế "Đã giải đúng" | **Không có** |
| Xem lại cách giải | Học viên có nút "Xem lại" | **Không có** |
| Trạng thái | "Đã nộp bài chính thức (Đã khóa)" | "Đã nộp 🔒" + nút "Mở lại bài" |

Vấn đề cần giải quyết:
1. Cột Tiến độ của giáo viên đang hiển thị số đúng nhưng gắn nhãn tiến độ. Hai chỉ số (hoàn thành, chính xác) bị gộp.
2. Giáo viên không có chỗ xem từng thế cờ, nước đi, lời giải của học viên để đánh giá.
3. Kết quả đúng/sai lộ cho học viên ngay sau khi nộp, trước hạn nộp và trước khi giáo viên xem.
4. Không có khâu chấm tay, nhận xét, trả bài.

> Agent kiểm chứng các quan sát trên bằng code và dữ liệu thật rồi mới sửa; báo lại nếu nguyên nhân khác với mô tả.

---

## 2. Quy trình đích

**Giao bài → Làm bài → Nộp (khóa) → Chấm tự động → Giáo viên xem lại và chấm → Trả bài → Học viên xem kết quả và ôn lỗi**

### 2.1 Trạng thái bài nộp (`submission.status`)

| Trạng thái | Ý nghĩa | Chuyển tiếp |
|---|---|---|
| `not_started` | Chưa làm thế cờ nào | → `in_progress` |
| `in_progress` | Đang làm, chưa nộp | → `submitted` |
| `submitted` | Đã nộp, khóa chỉnh sửa, đã chấm tự động | → `graded`, `reopened` |
| `graded` | Giáo viên đã xem/chấm xong, chưa công bố | → `returned`, `reopened` |
| `returned` | Đã trả bài, học viên xem được kết quả theo chính sách | → `reopened` |
| `reopened` | Giáo viên mở lại cho học viên làm lần tiếp | → `in_progress` |

Cờ phụ: `is_late` (nộp sau hạn). Trạng thái hiển thị cho học viên chỉ gồm: Chưa làm, Đang làm, Đã nộp (chờ chấm), Đã có kết quả, Được mở lại.

### 2.2 Quy tắc làm bài (giữ hành vi hiện có, Agent kiểm tra)
- **Chế độ luyện tập:** chặn nước sai, học viên làm lại đến khi đúng (không thuộc phạm vi spec này).
- **Chế độ bài tập về nhà:** học viên được đi cả nước ngoài đáp án để giáo viên/AI chấm và thấy lỗ hổng kỹ năng.
- **Khóa khi nộp:** sau khi bấm Nộp, bài bị khóa trên server, kể cả trước hạn nộp. Mọi lượt giải sau đó chỉ là "Xem lại", không ghi vào kết quả.
- **Điều kiện kết thúc một thế cờ trong chế độ bài tập về nhà** (giả định, cần chủ dự án xác nhận ở mục 11): thế cờ kết thúc khi học viên giải đúng, hoặc bấm "Chốt thế cờ này", hoặc đạt số nước sai tối đa (`settings.homework_max_wrong_moves`, mặc định 3). Khi kết thúc, kết quả thế cờ được ghi nhận và không đổi lại trừ khi bài được mở lại.

---

## 3. Mô hình dữ liệu

> Đối chiếu với bảng hiện có (`assignment`, `progress`…); **mở rộng bảng có sẵn nếu hợp lý, không tạo bảng trùng chức năng**. Nếu bảng hiện tại chỉ lưu tổng điểm, thêm các bảng dưới đây.

### 3.1 `assignment_submissions` (một dòng cho mỗi học viên × bài giao × lần làm)
- `id`, `assignment_id`, `student_id`, `class_id`, **`center_id`**, `attempt_no` (1, 2, …), `status` (mục 2.1), `is_late`
- `started_at`, `submitted_at`, `graded_at`, `returned_at`, `reopened_at`
- `reopen_reason` (bắt buộc khi mở lại), `reopened_by`
- `auto_score`, `teacher_adjustment` (có thể âm/dương), `final_score` (tính = auto + adjustment)
- `teacher_feedback` (nhận xét chung), `graded_by`
- Unique `(assignment_id, student_id, attempt_no)`.
- Khi mở lại: giữ nguyên lần cũ, tạo lần mới `attempt_no + 1`. Số lần mở lại tối đa là `settings.homework_max_reopens` (mặc định 3, thay cho số lần làm lại đang hard-code nếu có).

### 3.2 `submission_items` (một dòng cho mỗi thế cờ trong một bài nộp)
- `id`, `submission_id`, `assignment_puzzle_id`, `puzzle_id`, **`center_id`**
- `status`: `not_attempted | in_progress | finished`
- `auto_result`: `correct | incorrect | partial | skipped`
- `teacher_result`: nullable, cùng tập giá trị, là kết quả giáo viên ghi đè
- `final_result`: tính = `teacher_result` nếu có, ngược lại `auto_result`
- `moves_played` (JSON, chuỗi nước UCI học viên đi, kèm thời điểm từng nước)
- `first_wrong_move_index` (nullable), `error_class` (nullable: `blunder|mistake|inaccuracy`, lấy từ kết quả Stockfish hiện có)
- `engine_eval` (JSON, đánh giá Stockfish từng nước nếu đã có; không có thì để trống, **không chạy lại engine hàng loạt**)
- `time_spent_seconds`, `hints_used`, `attempts_count`
- `points_earned` (theo công thức hiện có: rating thế cờ / 100, trừ điểm gợi ý)
- `teacher_comment` (nhận xét riêng cho thế cờ)

### 3.3 Cột `center_id` (chuẩn bị cho phân quyền, bắt buộc)
- Cột `center_id` có trong mọi bảng mới ở trên và bảng lịch sử mở lại (nếu tạo riêng `submission_events`: `id`, `submission_id`, **`center_id`**, `event` (`submitted|graded|returned|reopened`), `actor_id`, `note`, `created_at`).
- **Server tự lấy `center_id` từ lớp của bài giao** khi tạo bản ghi. Không nhận `center_id` từ client.
- Agent kiểm tra lớp (`classes`) và bài giao (`assignments`) hiện đã có `center_id` chưa. **Nếu chưa, không tự thêm: báo lại chủ dự án** (việc đó thuộc spec phân quyền). Trong trường hợp đó, tạm dùng `center_id` nullable cho các bảng mới và ghi rõ trong báo cáo.
- Chưa làm ở bước này: lọc theo trung tâm của người đăng nhập, trả 404 chéo trung tâm, kiểm tra vai trò đa trung tâm, backfill bảng cũ. Những việc đó thuộc spec phân quyền.

### 3.4 Cấu hình bài giao
Thêm vào `assignments`: `release_policy` (`after_returned | after_deadline | immediately`, mặc định lấy từ settings, ban đầu `after_returned`), `show_solutions` (hiển thị lời giải sau khi công bố, mặc định bật).

---

## 4. Định nghĩa chỉ số (dùng chung cả hai phía, tính ở Backend)

| Chỉ số | Công thức | Ghi chú |
|---|---|---|
| **Tiến độ** | số `submission_items.status = finished` / tổng thế cờ | Minh Triết: 5 / 5 |
| **Độ chính xác** | số `final_result = correct` / tổng thế cờ | Minh Triết: 1 / 5 = 20% |
| **Điểm tự động** | tổng `points_earned` | Công thức hiện có, giữ nguyên |
| **Điểm cuối** | `auto_score + teacher_adjustment` | Điểm vào bảng xếp hạng lấy theo điểm cuối của lần làm cao nhất hoặc gần nhất (`settings.leaderboard_attempt_rule`, mặc định "lần gần nhất đã trả bài") |

- Frontend không tự tính lại; hiển thị đúng các trường Backend trả về.
- Cột "Tiến độ" của giáo viên phải dùng **Tiến độ**, thêm cột **Độ chính xác** riêng.

---

## 5. Màn hình phía giáo viên

### 5.1 Tổng quan bài giao (mở từ danh sách bài giao hoặc từ lớp)
- Thẻ tóm tắt: số học viên đã nộp / tổng lớp, số nộp muộn, điểm trung bình, độ chính xác trung bình.
- **Bảng học viên × thế cờ:** hàng là học viên, cột là từng thế cờ (#1…#n); mỗi ô là ✓ (đúng), ✗ (sai), – (bỏ qua/chưa làm), có màu phân biệt; bấm ô để vào chi tiết thế cờ của học viên đó. Cột cuối: Tiến độ, Độ chính xác, Điểm cuối, Trạng thái.
- Hàng cuối: **tỷ lệ đúng từng thế cờ** của cả lớp để biết thế nào khó nhất.
- Bộ lọc theo trạng thái (đã nộp chưa chấm, đã chấm, đã trả bài, nộp muộn).
- Nút hành động: Chấm hàng loạt (đánh dấu đã xem), **Trả bài** (một học viên hoặc nhiều học viên đã chọn), **Mở lại bài** (bắt buộc nhập lý do).

### 5.2 Chi tiết một học viên
- Đầu trang: tên, trạng thái, lần làm (nếu có nhiều lần thì chọn được lần xem), thời gian nộp, nộp muộn hay không.
- Mỗi thế cờ là một khối gồm:
  - Bàn cờ **phát lại** chuỗi nước đi của học viên (nút trước/sau, tự phát) cạnh **đáp án mẫu**.
  - Đánh dấu nước sai đầu tiên, phân loại sai lầm (nếu có từ Stockfish), đánh giá từng nước (nếu có).
  - Thời gian làm, số lần thử, số gợi ý.
  - Chọn kết quả: giữ kết quả tự động hoặc **ghi đè** (đúng / sai / đúng một phần), ô nhận xét riêng.
- Cuối trang: điều chỉnh điểm (`teacher_adjustment`), nhận xét chung, nút **Lưu**, **Lưu và trả bài**.
- Mọi ghi đè, nhận xét, điều chỉnh điểm ghi vào `submission_events`.

---

## 6. Màn hình phía học viên

- Khi bài ở trạng thái `submitted` hoặc `graded`, trước thời điểm công bố theo `release_policy`: chỉ hiển thị "Đã nộp, chờ giáo viên chấm", **Tiến độ (5/5)** và thời gian nộp. **Không hiển thị** đúng/sai, độ chính xác, điểm từng thế cờ, hay nhãn "Đã giải đúng". Thay bằng nhãn trung tính "Đã ghi nhận" cho mọi thế cờ.
- Chính sách công bố:
  - `after_returned`: hiển thị khi giáo viên bấm Trả bài (mặc định).
  - `after_deadline`: hiển thị khi qua hạn nộp **và** bài đã được chấm tự động; giáo viên ghi đè sau đó vẫn cập nhật.
  - `immediately`: hiển thị ngay sau khi nộp (hành vi hiện tại).
- Sau khi công bố: hiển thị kết quả từng thế cờ, điểm, nhận xét giáo viên, **lời giải** (nếu `show_solutions`), nút "Xem lại" phát lại nước đi của mình và đáp án.
- **Ôn lại thế cờ sai:** nút "Luyện lại các thế cờ sai" đưa các thế cờ `final_result != correct` vào chế độ luyện tập (chặn nước sai). Điểm luyện tập này **không** cộng vào bài giao đã nộp.
- Khi bài được mở lại: hiển thị lý do, chỉ cho làm lại theo `attempt_no` mới.
- Phải kiểm tra ở **API phía học viên**: endpoint trả kết quả không được gửi trường đúng/sai, điểm, lời giải trước thời điểm công bố, kể cả khi lấy trực tiếp bằng gọi API (không chỉ ẩn ở giao diện).

---

## 7. API (đối chiếu tên và đường dẫn với `assignments.py` hiện có)

Giáo viên:
- `GET /assignments/{id}/overview`: tóm tắt, bảng học viên × thế cờ, tỷ lệ đúng từng thế cờ.
- `GET /assignments/{id}/submissions/{student_id}?attempt=`: chi tiết một bài nộp kèm từng thế cờ, nước đi, đánh giá engine nếu có.
- `PATCH /submissions/{id}/items/{item_id}`: ghi đè `teacher_result`, `teacher_comment`.
- `PATCH /submissions/{id}`: `teacher_adjustment`, `teacher_feedback`, chuyển `graded`.
- `POST /assignments/{id}/return`: body danh sách `submission_ids` hoặc `all_graded=true`; chuyển `returned`.
- `POST /submissions/{id}/reopen`: bắt buộc `reason`; tạo lần làm mới.

Học viên:
- `GET /me/assignments/{id}`: trả dữ liệu đã **lọc theo `release_policy`** (xem mục 6).
- `POST /me/assignments/{id}/submit`: khóa bài, chạy chấm tự động, ghi `auto_result`.
- `GET /me/assignments/{id}/review`: chỉ khả dụng sau thời điểm công bố, trả lời giải và nước đi.

Quyền trong spec này (tối thiểu, theo vai trò hiện có):
- Giáo viên chỉ thao tác trên bài giao thuộc lớp mình dạy. Admin/super_admin theo quyền hiện có của hệ thống.
- Học viên chỉ xem bài nộp của chính mình.
- Phần kiểm tra theo trung tâm sẽ bổ sung ở spec phân quyền.

---

## 8. Cài đặt (không hard-code)

Đưa vào `settings` (giá trị mặc định ghi trong seed, đổi qua giao diện Cài đặt, nơi spec phân quyền sẽ mở rộng theo vai trò; trước mắt đặt ở trang quản trị hiện có hoặc file cấu hình đọc từ DB):

| Khóa | Mặc định | Ý nghĩa |
|---|---|---|
| `homework_release_policy_default` | `after_returned` | Chính sách công bố mặc định khi giao bài |
| `homework_show_solutions_default` | `true` | Hiển thị lời giải sau khi công bố |
| `homework_max_reopens` | 3 | Số lần mở lại tối đa mỗi bài nộp |
| `homework_max_wrong_moves` | 3 | Số nước sai tối đa trước khi tự chốt thế cờ |
| `leaderboard_attempt_rule` | `latest_returned` | Lần làm nào được tính vào bảng xếp hạng |
| `late_submission_allowed` | `true` | Cho phép nộp muộn (đánh dấu `is_late`) |

Nếu số lần làm lại (hiện tại là 3) đang viết cứng trong code, chuyển sang `homework_max_reopens` với giá trị mặc định đúng bằng giá trị hiện tại.

---

## 9. Tiêu chí nghiệm thu và kiểm thử

Viết test tự động (pytest cho API, Playwright hoặc tương đương cho UI chính). Tối thiểu:

**Chỉ số**
- [ ] Học viên làm đủ 5 thế cờ, đúng 1: Tiến độ hiển thị 5/5, Độ chính xác 1/5, ở cả hai phía; không còn cột "Tiến độ" hiện số đúng.
- [ ] Điểm tự động khớp công thức hiện có (không đổi so với trước khi sửa với cùng dữ liệu).

**Quy trình**
- [ ] Nộp bài khóa trên server: gọi API ghi nước đi sau khi nộp bị từ chối; lượt "Xem lại" không ghi vào kết quả.
- [ ] Mở lại bài bắt buộc có lý do; tạo `attempt_no` mới, lần cũ giữ nguyên; vượt `homework_max_reopens` bị từ chối.
- [ ] Giáo viên ghi đè `teacher_result` làm `final_result` và độ chính xác đổi theo; có bản ghi trong `submission_events`.
- [ ] Trả bài chuyển trạng thái `returned`; trả hàng loạt chỉ áp dụng cho bài đã `graded`.

**Công bố kết quả**
- [ ] Với `after_returned`: trước khi trả bài, API học viên **không chứa** đúng/sai, điểm, lời giải (kiểm tra bằng gọi API trực tiếp); sau khi trả bài thì có.
- [ ] Với `after_deadline`: trước hạn không có, sau hạn có.
- [ ] Với `immediately`: có ngay sau khi nộp.
- [ ] Học viên chỉ xem được bài nộp của chính mình; giáo viên chỉ chấm được bài của lớp mình dạy.

**Giao diện giáo viên**
- [ ] Bảng học viên × thế cờ hiển thị đúng ✓/✗/– và tỷ lệ đúng từng thế cờ.
- [ ] Trang chi tiết phát lại đúng chuỗi nước đi của học viên và hiển thị đáp án mẫu.
- [ ] Bài giao cũ (nộp trước khi có tính năng này) vẫn mở được, thế cờ thiếu dữ liệu hiển thị "Không có dữ liệu chi tiết" thay vì lỗi.

**Dữ liệu**
- [ ] Mọi bảng mới có cột `center_id`; server lấy giá trị từ lớp, bỏ qua giá trị client gửi.
- [ ] Migration chạy được trên bản sao DB hiện có, có rollback; dữ liệu cũ được backfill tối thiểu (xem mục 10, bước 1).

---

## 10. Thứ tự triển khai (mỗi bước một commit)

1. **Dữ liệu và backfill:** thêm `assignment_submissions`, `submission_items`, `submission_events`, cột cấu hình bài giao, cột `center_id`; backfill từ dữ liệu tiến độ hiện có (tạo `attempt_no=1`, `status` suy từ trạng thái cũ, `auto_result` từ kết quả đang lưu). Dữ liệu nào không có chi tiết nước đi thì để trống, không bịa.
2. **Sửa chỉ số:** định nghĩa Tiến độ / Độ chính xác / Điểm ở Backend; sửa nhãn và cột ở màn hình giáo viên và học viên (việc cấp bách, có thể phát hành riêng).
3. **Ghi dữ liệu chi tiết khi học viên làm bài:** lưu chuỗi nước, thời gian, gợi ý, số lần thử, nước sai đầu tiên, kết quả Stockfish có sẵn.
4. **Màn hình giáo viên:** tổng quan (bảng học viên × thế cờ), chi tiết học viên với phát lại nước đi.
5. **Chấm tay:** ghi đè kết quả, nhận xét, điều chỉnh điểm, nhật ký sự kiện.
6. **Công bố kết quả:** `release_policy`, lọc dữ liệu ở API học viên, nút Trả bài, trả hàng loạt.
7. **Mở lại bài có lý do và theo lần làm;** đưa số lần làm lại ra `settings`.
8. **Phía học viên sau công bố:** kết quả, lời giải, nhận xét, xem lại, luyện lại thế cờ sai.
9. **Kiểm thử tổng thể và báo cáo.**

Sau mỗi bước Agent báo cáo: file đã sửa, migration đã thêm, test đã chạy (pass/fail), điểm mâu thuẫn với code hiện có, và các giả định cần chủ dự án xác nhận.

---

## 11. Quyết định đã chốt và điểm còn mở

**Đã chốt:**
1. Chính sách công bố mặc định là **sau khi giáo viên trả bài**; giáo viên đổi được từng bài giao.
2. Các bảng mới có sẵn `center_id`, lấy từ lớp của bài giao; phân quyền theo trung tâm làm sau trong spec phân quyền v1.1.
3. Khóa bài khi học viên nộp được giữ nguyên; mở lại bài do giáo viên thực hiện, có lý do và tạo lần làm mới.
4. Không làm lại Stockfish và chấm Elo; chỉ tái sử dụng kết quả.

**Cần chủ dự án xác nhận (Agent dùng giá trị mặc định trong lúc chờ):**
1. Điều kiện kết thúc thế cờ trong bài tập về nhà (mục 2.2: giải đúng, hoặc bấm chốt, hoặc đạt 3 nước sai).
2. Lần làm nào tính vào bảng xếp hạng (mục 4: lần gần nhất đã trả bài).
3. Cho phép nộp muộn hay chặn hẳn sau hạn (mặc định: cho phép và đánh dấu).
4. Học viên có thấy lời giải đầy đủ của thế cờ sau khi được trả bài hay chỉ thấy đúng/sai (mặc định: thấy lời giải).
