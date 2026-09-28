---
trigger: always_on
description: >
---

# 05. Result Contract

Áp dụng cho mọi specialist: `cams-architect`, `cams-backend`, `cams-database`, `cams-ai-cv`, `cams-chess`, `cams-frontend`, `cams-mobile`, `cams-qa`, `cams-devops`, `cams-security`, `cams-payment`, `cams-tournament`.

Khi hoàn thành (hoặc dừng) một task được Orchestrator giao qua Context Packet, LUÔN báo cáo theo đúng format sau — không tự do diễn giải, không đổi tên field:

```
STATUS: DONE | FAILED | BLOCKED | PARTIAL

SCOPE:
<phạm vi đã làm, 1-2 dòng>

CHANGES:
- <file / endpoint / bảng đã đổi, liệt kê cụ thể, không mô tả chung chung>

TESTS:

- Implementation / Bugfix / Refactor / Infra:
  BẮT BUỘC chạy các test phù hợp trong domain trước khi báo STATUS: DONE.
  Phải ghi rõ loại test và số pass/fail.

- Research / Architecture / Design / Review read-only:
  Ghi `NOT_APPLICABLE` nếu không có test thực thi phù hợp.
  Thay vào đó phải ghi phương pháp verification đã thực hiện.

- Không được để field TESTS trống.
- Không được tuyên bố test PASS nếu test chưa thực sự chạy.

RISKS:
- <rủi ro còn lại, kể cả khi STATUS: DONE>

DEPENDENCIES:
- <đang chờ gì từ specialist khác, nếu có>

BLOCKERS:
- <lý do không thể hoàn thành, bắt buộc nếu STATUS khác DONE>

NEXT_ACTION:
- <bước tiếp theo đề xuất, vd "QA integration test">
```

Ví dụ (Backend):

```
STATUS: DONE

SCOPE:
Payment API

CHANGES:
- POST /payments
- GET /payments/{id}
- confirm payment endpoint

TESTS:
- unit: 12 passed

RISKS:
- webhook idempotency chưa implement

DEPENDENCIES:
- DB migration đã apply

BLOCKERS:
- none

NEXT_ACTION:
- QA integration test
```

## Vai trò của `cams-qa` trong contract này

QA **không tự viết lại toàn bộ test suite cho 6 stack khác nhau** (FastAPI, React, React Native, OpenCV/YOLO, Stockfish, PostgreSQL) — điều đó không khả thi cho một agent duy nhất. Vai trò thật của QA:

1. **Audit**: đọc field `TESTS` mà từng specialist đã tự báo cáo, đối chiếu với `acceptance_criteria` trong Context Packet gốc của task.
2. **Tự chạy**: các test xuyên domain (integration/regression) mà không domain riêng lẻ nào tự kiểm được — vd luồng payment end-to-end chạm cả backend + database + frontend.
3. Trả kết quả `PASS` / `FAIL` / `PASS_WITH_WARNINGS`. Nếu một specialist báo `TESTS` trống hoặc mơ hồ, QA trả `FAIL` và yêu cầu specialist đó chạy lại và báo cáo rõ ràng — không tự bỏ qua hay tự suy diễn đã test.
