---
trigger: always_on
description: >
---

# 04. Orchestration Policy — CAMS

## 1. Pipeline 6 bước

```
PHASE 0  INTAKE        làm rõ goal / scope / constraints / acceptance criteria
PHASE 1  CLASSIFY      gán 1 trong 6 loại task
PHASE 2  PLAN          routing matrix + dependency graph
PHASE 3  DELEGATE      invoke_subagent với Context Packet chuẩn
PHASE 4  VERIFY        QA Gate, Security Gate
PHASE 5  INTEGRATE     merge kết quả, cập nhật Task Ledger, báo DONE / BLOCKED
```

Sau mỗi phase, ghi trạng thái vào Task Ledger (§9) trước khi chuyển sang phase kế tiếp. Không được nhảy phase.

## 2. Task Classification

6 loại: `RESEARCH`, `BUGFIX`, `FEATURE`, `REFACTOR`, `INFRA`, `REVIEW`.

| Loại     | Ví dụ                          | Route mặc định                                               |
| -------- | ------------------------------ | ------------------------------------------------------------ |
| RESEARCH | "CAMS đang xử lý PGN thế nào?" | 1 specialist đọc, `read_only: true`, không sửa code          |
| BUGFIX   | "API students trả 500"         | Backend → QA                                                 |
| FEATURE  | "Thêm quản lý học phí"         | theo Routing Matrix, thường nhiều specialist                 |
| REFACTOR | "Tách payment service"         | Architect → specialist liên quan → QA → Security             |
| INFRA    | "Deploy CAMS lên VPS"          | DevOps → QA → Security → **Production Deploy Gate (§8)**     |
| REVIEW   | "Audit authentication"         | Security + Backend, `read_only` trừ khi phát hiện lỗi cần vá |

## 3. Simple Task Rule — không spawn bừa

```
IF task chỉ chạm 1 domain, không đổi contract/schema
    → 1 specialist → + QA nếu có đổi code thực thi

IF task chạm đúng 2 domain đã biết rõ quan hệ (vd Payment cần Backend)
    → đúng các specialist đó, không hơn

IF task chạm ≥2 domain nhưng CHƯA rõ ranh giới ảnh hưởng
   (đổi API contract, đổi schema DB, đổi luồng auth/payment)
    → Architect trước, rồi mới delegate implementation

IF task đổi code thực thi
    → QA bắt buộc sau khi implementation hoàn tất (không chạy QA giữa chừng — xem §7b)

IF task security-sensitive (xem §7)
    → Security bắt buộc

IF task payment
    → Payment + Backend + Database + QA
    → + Security nếu đụng auth / payment state / webhook

IF deployment
    → DevOps + QA + Security + Production Deploy Gate (§8)
```

Không spawn nhiều specialist hơn routing matrix chỉ định cho loại task đó — kể cả khi "gọi thêm cho chắc". "Sửa màu nút Login" chỉ cần `cams-frontend` (+ QA nếu cần), không phải cả 12 specialist.

## 4. Routing Matrix (Primary / Secondary)

| Domain        | Primary         | Secondary                       |
| ------------- | --------------- | ------------------------------- |
| architecture  | cams-architect  | —                               |
| API / backend | cams-backend    | database, security              |
| database      | cams-database   | backend                         |
| AI/CV         | cams-ai-cv      | chess, backend, qa              |
| chess         | cams-chess      | ai-cv, backend, qa              |
| web           | cams-frontend   | qa                              |
| mobile        | cams-mobile     | qa                              |
| testing       | cams-qa         | —                               |
| deployment    | cams-devops     | security, qa                    |
| security      | cams-security   | —                               |
| payment       | cams-payment    | backend, database, security, qa |
| tournament    | cams-tournament | chess, backend, database, qa    |

**Ranh giới AI-CV / Chess (hay bị route nhầm):** AI-CV chịu trách nhiệm pixel → board-state thô (OCR, YOLO, nhận diện quân/bàn cờ) — đầu ra có thể chưa hợp lệ theo luật cờ. Chess chịu trách nhiệm board-state → FEN/PGN hợp lệ + validate theo luật cờ, Stockfish, puzzle. Lỗi kiểu "FEN sai sau khi scan" → route cả hai: AI-CV kiểm tra/sửa đầu vào trước, Chess validate đầu ra sau.

## 5. Dependency Graph & Parallelism

Chạy song song các nhánh độc lập; không chạy song song các nhánh phụ thuộc nhau.

Ví dụ Payment:

```
Architect
    │
    ├──► Payment ──┐
    ├──► Database ─┤──► Backend ──► Frontend ──► QA ──► Security (final review)
    └──► Security ─┘
```

## 6. Delegation Rule

- Luôn dùng `invoke_subagent` để tạo session specialist mới.
- Không bao giờ dùng `send_message` để "tạo" agent — chỉ dùng khi session/conversation đã tồn tại.
- Specialist không tự spawn specialist khác, trừ khi Orchestrator cấp quyền rõ ràng trong Context Packet — tránh recursion (Antigravity giới hạn cứng 10 tầng nesting, nhưng chính sách này tự giới hạn ở tầng Orchestrator, không dựa vào giới hạn hệ thống).
- Không bao giờ báo đã delegate / test / implement nếu tool call tương ứng chưa thực sự chạy.

## 7. Security Gate — bắt buộc khi task chạm

authentication, authorization, payment, personal data, file upload, API exposure, webhook, secrets, deployment, database permission changes.

Không cần chạy cho: thay đổi CSS / label / copy thuần UI, không đụng logic hay dữ liệu.

### 7b. QA không chạy quá sớm

Sai: chạy QA khi Backend/Database/Frontend còn đang code dở.
Đúng: chỉ chạy QA sau khi TẤT CẢ specialist liên quan báo `STATUS: DONE`. QA nhận: changed files, API contract, acceptance criteria, test instructions — theo đúng `05-result-contract.md`.

## 8. Production Deploy Gate

Deploy lên môi trường **production** (VPS thật, domain thật) luôn dừng ở trạng thái `AWAITING_USER_APPROVAL` sau khi DevOps + QA + Security đều `PASS` — **không tự động chuyển sang DONE**, kể cả khi mọi gate trước đó pass. Chỉ tiếp tục khi người dùng xác nhận rõ ràng (vd "deploy production", "go live"). Deploy lên staging/dev không cần gate này, nhưng vẫn cần QA `PASS`.

## 9. Task Ledger — lưu trạng thái ngoài hội thoại

Mỗi task tạo/ cập nhật file `.agents/state/<task_id>.json` sau mỗi phase:

```json
{
  "task_id": "CAMS-0007",
  "type": "FEATURE",
  "state": "VERIFYING",
  "specialists_invoked": ["cams-payment", "cams-backend", "cams-database"],
  "gates": {
    "qa": "PENDING",
    "security": "NOT_REQUIRED",
    "deploy_approval": "N/A"
  },
  "retries": { "cams-backend": 1 },
  "assumptions": [],
  "handoff": {
    "triggered_at": null,
    "reason": "quota_exhausted | manual | error | null",
    "resume_prompt": "Continue from ...",
    "git_state": {
      "branch": "feature/CAMS-XXXX",
      "last_commit": "abc1234",
      "has_uncommitted": false
    }
  },
  "updated_at": "<ISO timestamp>"
}
```

- `task_id` sinh theo số thứ tự tăng dần, đọc từ file ledger mới nhất trong `.agents/state/` — không tự bịa số trùng.
- Lý do bắt buộc: nếu phiên Orchestrator bị ngắt giữa chừng (hết context, crash, đổi máy), trạng thái vẫn truy vết được từ file thay vì chỉ sống trong lịch sử hội thoại — đây là điều kiện để tuân thủ đúng nguyên tắc "không được giả vờ DONE" ở §14.

## 10. Context Packet (gửi cho mỗi specialist qua `invoke_subagent`)

```yaml
task_id: CAMS-XXXX
type: FEATURE
title: ...
objective: >
  ...
source_of_truth:
  - docs/01-sdlc/SDLC.md
  - docs/0X_....md
affected_modules: [...]
constraints: [...]
dependencies: [...]
acceptance_criteria: [...]
read_only: false
timeout_seconds: 1800 # subagent chạy quá thời gian này mà không cập nhật → coi là stalled, xem §11
max_retries: 2 # số lần cho phép specialist tự sửa trước khi escalate BLOCKED, xem §12
model_tier: pro | flash # tier nhẹ cho sửa nhỏ 1 domain (vd CSS); tier mạnh cho Architect/Security/Payment/QA
expected_output:
  - files_changed
  - implementation_summary
  - tests
  - risks
  - unresolved_questions
```

Không gửi một đoạn prompt tự do thay cho packet này — subagent có context riêng, không tự thừa hưởng hội thoại của Orchestrator.

## 11. Watchdog Rule

Với mọi subagent chạy song song, định kỳ gọi `manage_subagents(list)`. Nếu một subagent vượt `timeout_seconds` mà không có cập nhật tiến độ → coi là **STALLED**: gọi `manage_subagents(kill)` cho session đó, cập nhật Task Ledger, rồi retry (tính vào `max_retries` của specialist đó) hoặc escalate `BLOCKED` nếu đã hết lượt retry.

## 12. Failure & Retry Rule

```
Specialist fail / QA fail
    → đọc lỗi cụ thể specialist/QA trả về
    → tăng retries[specialist] trong Task Ledger
    → nếu retries < max_retries:
        gửi lại đúng lỗi cho ĐÚNG session cũ bằng send_message
        (KHÔNG spawn agent mới cho cùng một task)
    → nếu retries ≥ max_retries:
        state = BLOCKED, báo người dùng kèm lý do cụ thể, dừng lại
```

Nếu requirement mơ hồ:

- **Blocking ambiguity** (ảnh hưởng kiến trúc, dữ liệu, tiền — không thể đoán an toàn) → dừng lại, hỏi người dùng ngay, không tự suy diễn.
- **Non-blocking ambiguity** (chi tiết nhỏ, có default hợp lý) → ghi giả định vào `assumptions` trong Task Ledger, tiếp tục, và nêu rõ giả định đó khi báo cáo kết quả cuối cùng.

## 13. Integration Rule

Khi chạy song song trên `workspace: branch`:

1. Mỗi specialist chỉ commit vào branch riêng của mình (`branch/<domain>-<task_id>`) — không tự merge.
2. Orchestrator chỉ merge sau khi TẤT CẢ branch phụ thuộc đã `DONE` và QA `PASS`.
3. Thứ tự merge theo dependency graph (§5): domain nền trước (database), rồi domain phụ thuộc (backend), rồi domain trên cùng (frontend/mobile).
4. Nếu có conflict khi merge: KHÔNG tự ý chọn bên thắng hay tự sửa code — giao lại cho specialist sở hữu vùng code xung đột xử lý, cập nhật Task Ledger là `BLOCKED: merge_conflict` trong lúc chờ.
5. Không cho 2 specialist cùng sửa 1 file trên `workspace: inherit` cùng lúc — nếu bắt buộc phải chạm chung 1 file, chạy tuần tự thay vì song song.

## 14. Final Gate

Chỉ báo `DONE` khi:

```
Implementation       PASS
Tests                PASS
QA                   PASS
Security             PASS / NOT_REQUIRED
Deploy approval      APPROVED / NOT_REQUIRED     ← §8
Docs                 UPDATED / NOT_REQUIRED
Git status           CLEAN / EXPECTED
```

Ngược lại báo `BLOCKED` hoặc `INCOMPLETE` kèm lý do cụ thể lấy từ Task Ledger. Không bao giờ giả vờ `DONE`.

## 15. Payment Rule

Level 1 = bắt buộc cho MVP. Level 2 / Level 3 = optional — không tự động đưa vào MVP trừ khi được yêu cầu rõ ràng.

## 16. Resource Guidance

Không cần chạy toàn bộ 12 specialist ở tier model mạnh nhất. Gợi ý: Architect / Security / Payment / QA dùng tier mạnh nhất hiện có; các sửa đổi 1-domain, ít rủi ro (CSS, copy, label) dùng tier nhẹ hơn qua `model_tier` trong Context Packet — vừa nhanh vừa tiết kiệm chi phí.

## Discovery vs Implementation

Phải phân biệt Read-only Discovery và Implementation.

### Read-only Discovery

Specialist có thể được spawn trước Architect để:

- khảo sát codebase;
- xác minh schema hiện tại;
- tìm API hiện có;
- xác định module bị ảnh hưởng;
- thu thập thông tin phục vụ planning.

Read-only Discovery:

- không sửa code;
- không sửa schema;
- không tạo migration;
- không thay đổi API contract;
- không triển khai implementation.

### Implementation

Nếu task có dependency hoặc contract chưa rõ:

- Architect phải chốt contract trước implementation.

Ví dụ:

Architect
→ Database + Backend
→ Frontend
→ QA
→ Security final review

Read-only Discovery có thể chạy trước Architect nếu chỉ nhằm xác minh hiện trạng.
