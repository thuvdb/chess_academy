---
name: cams-qa-verification
description: >
  Quy trình chuẩn QA verification trong CAMS.
  Dùng khi cams-qa nhận task kiểm thử sau khi specialist hoàn thành implementation.
  QA là release gate — không phải agent viết test suite cho 6 stack khác nhau.
---

# CAMS QA Verification Skill

Quy trình step-by-step khi QA verify kết quả implementation trong CAMS.

## Vai trò QA trong CAMS

QA **không tự viết lại toàn bộ test suite** cho 6 stack khác nhau (FastAPI, React, React Native, OpenCV/YOLO, Stockfish, PostgreSQL).

Vai trò thật:

1. **Audit**: đọc field `TESTS` mà từng specialist đã báo cáo, đối chiếu với `acceptance_criteria` trong Context Packet.
2. **Cross-domain test**: chạy integration/regression test xuyên domain mà không domain riêng lẻ nào tự kiểm được.
3. **Verdict**: trả `PASS` / `FAIL` / `PASS_WITH_WARNINGS`.

## Source of Truth

- `docs/01-sdlc/04_testing.md` → Test strategy tổng thể
- `docs/01-sdlc/01_requirements.md` → Acceptance criteria
- `05-result-contract.md` → Format báo cáo specialist

## Quy trình Verification

### Bước 1 — Thu thập Result Contracts

1. Nhận Result Contract từ tất cả specialist liên quan.
2. Kiểm tra mỗi contract có đầy đủ fields không.
3. Nếu field `TESTS` trống hoặc mơ hồ → trả `FAIL` cho specialist đó, yêu cầu báo cáo rõ ràng.

### Bước 2 — Audit Test Coverage

Đối chiếu từng specialist:

| Kiểm tra | Câu hỏi |
|---|---|
| Tests ran? | Specialist có thực sự chạy test không? |
| Tests relevant? | Tests có cover acceptance criteria không? |
| Edge cases? | Có test edge cases / error paths không? |
| Count? | Bao nhiêu test pass/fail? |

### Bước 3 — Cross-domain Integration Test

Chỉ QA mới chạy các test xuyên domain:

- **Payment E2E**: Invoice → QR → Admin confirm → PAID status → Frontend hiển thị.
- **AI Scanner E2E**: Upload PDF → Scan Job → Board Detection → FEN → Review UI.
- **Auth flow**: Login → Token → Protected endpoint → Role-based access.
- **Tournament flow**: Registration → Pairing → Game → Result → Standings.

### Bước 4 — Regression Check

1. Thay đổi mới có break feature cũ không?
2. Chạy existing test suite nếu có.
3. Kiểm tra API contract vẫn backward compatible.

### Bước 5 — Specific Domain Checks

**Payment (Level 1):**
- Invoice tạo đúng?
- QR generate đúng format VietQR?
- Admin confirm → status PAID?
- Payment audit log ghi đủ?

**AI Scanner:**
- Confidence threshold hoạt động?
- Multi-board per page xử lý đúng?
- Invalid FEN → flagged for review?
- Human review flow hoạt động?

**Chess:**
- FEN validation bắt được position illegal?
- Puzzle solution đúng?
- Stockfish analysis trả kết quả hợp lệ?

### Bước 6 — Verdict

```
PASS              → Tất cả acceptance criteria đạt, tests pass, no critical issues
FAIL              → Có test fail, acceptance criteria không đạt, hoặc specialist chưa test
PASS_WITH_WARNINGS → Tests pass nhưng có non-critical issues cần lưu ý
```

### Bước 7 — Báo cáo Result Contract

```
STATUS: DONE
SCOPE: QA verification cho task CAMS-XXXX

CHANGES:
- (QA thường không thay đổi code, trừ khi phát hiện bug nhỏ fix được ngay)

TESTS:
- Specialist audit: X/Y specialists báo TESTS đầy đủ
- Integration tests: N ran, M passed
- Regression: no regressions found

VERDICT: PASS | FAIL | PASS_WITH_WARNINGS

RISKS:
- (issues phát hiện nhưng không block release)

DEPENDENCIES:
- (specialist nào cần sửa nếu FAIL)

BLOCKERS:
- (critical issues nếu có)

NEXT_ACTION:
- Security review (nếu cần) hoặc DONE
```

## Quy tắc bổ sung

- **KHÔNG** chạy QA khi specialist còn đang code dở — chỉ chạy sau khi TẤT CẢ specialist liên quan báo `STATUS: DONE`.
- Nếu specialist báo `TESTS` trống → QA trả `FAIL`, yêu cầu specialist chạy lại, KHÔNG tự bỏ qua.
- QA có thể kiến nghị thêm test case nhưng không bắt buộc specialist viết test không liên quan acceptance criteria.
- Khi test fail: xác định failure do code, environment, hay test trước khi kết luận.
