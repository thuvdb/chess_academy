Được Ông chủ. Bây giờ **không nên tiếp tục thử tool nữa**; chúng ta đã chứng minh `invoke_subagent` hoạt động. Bước tiếp theo là biến `cams-orchestrator` thành một **bộ điều phối có luật**, thay vì một agent chỉ biết gọi specialist.

Tôi đề xuất thiết kế theo mô hình:

> **Orchestrator = Planner + Router + Coordinator + Gatekeeper + Integrator**

Antigravity hỗ trợ đúng các primitive chúng ta cần: `invoke_subagent` để spawn, `send_message` để giao tiếp với session đã có, `manage_subagents` để quản lý subagent; nhiều subagent có thể chạy song song, và có thể dùng `inherit`, `branch` hoặc `share` cho workspace. ([Google Antigravity][1])

---

# 1. Kiến trúc tổng thể của CAMS

12 specialist của Ông chủ:

```text
01 Architect
02 Backend
03 Database
04 AI-CV
05 Chess
06 Frontend
07 Mobile
08 QA
09 DevOps
10 Security
11 Payment
12 Tournament
```

sẽ **không ngang hàng hoàn toàn**.

Tôi đề xuất chia thành 5 tầng:

```text
                         ┌─────────────────────┐
                         │       USER          │
                         └──────────┬──────────┘
                                    │
                                    ▼
                    ┌───────────────────────────┐
                    │     CAMS ORCHESTRATOR     │
                    │                           │
                    │ Planner                   │
                    │ Router                    │
                    │ Coordinator               │
                    │ Gatekeeper                │
                    │ Integrator                │
                    └─────────────┬─────────────┘
                                  │
             ┌────────────────────┼────────────────────┐
             │                    │                    │
             ▼                    ▼                    ▼
       ┌───────────┐       ┌──────────────┐     ┌──────────────┐
       │  PLANNING │       │ IMPLEMENTING │     │   REVIEWING  │
       └─────┬─────┘       └──────┬───────┘     └──────┬───────┘
             │                    │                    │
             ▼                    ▼                    ▼
         Architect          Domain specialists       QA
                                                   Security
             │
             └────────────────┬───────────────────┘
                              ▼
                        Final Integration
                              │
                              ▼
                            USER
```

---

# 2. Vai trò của từng specialist

## Tầng Planning

### `cams-architect`

Không phải agent viết code mặc định.

Nó trả lời:

- Kiến trúc nào?
- Module nào bị ảnh hưởng?
- API nào?
- Database nào?
- Dependency nào?
- Có cần thay đổi contract không?
- Có rủi ro kiến trúc không?

**Architect không tự động được gọi cho mọi task.**

Task nhỏ như:

> đổi label "Học phí" thành "Học phí tháng"

không cần Architect.

---

# 3. Tầng Domain

### `cams-backend`

Phụ trách:

```text
FastAPI
REST API
WebSocket
business logic
services
authentication
authorization
```

### `cams-database`

```text
PostgreSQL
schema
migration
index
constraint
query
transaction
```

### `cams-ai-cv`

```text
OCR
OpenCV
YOLO
board detection
piece recognition
FEN extraction
AI scanner
```

### `cams-chess`

```text
FEN
PGN
UCI
Stockfish
chess rules
puzzle
analysis
```

### `cams-frontend`

```text
React
Vite
Tailwind
UI
dashboard
admin
web UX
```

### `cams-mobile`

```text
React Native
Expo
mobile UX
mobile API integration
```

### `cams-payment`

```text
VietQR
invoice
payment state
Level 1
Level 2 webhook
Level 3 gateway
```

### `cams-tournament`

```text
tournament
pairing
standings
round
result
chess tournament logic
```

---

# 4. Tầng Platform

### `cams-devops`

```text
Docker
Docker Compose
Ubuntu
VPS
CI/CD
deployment
backup
monitoring
```

### `cams-security`

```text
authentication
authorization
secret
input validation
OWASP
dependency
security configuration
```

---

# 5. Tầng Gate

### `cams-qa`

QA **không phải agent cuối cùng để "chạy test cho có".**

QA là **release gate**.

Nó phải trả:

```text
PASS
FAIL
PASS_WITH_WARNINGS
```

và:

```text
Tests:
- unit
- integration
- API
- UI
- regression
```

---

# 6. Não điều phối nên có 6 bước

Tôi đề xuất `cams-orchestrator` luôn chạy theo pipeline:

```text
PHASE 0
INTAKE
   ↓
PHASE 1
CLASSIFY
   ↓
PHASE 2
PLAN
   ↓
PHASE 3
DELEGATE
   ↓
PHASE 4
VERIFY
   ↓
PHASE 5
INTEGRATE
```

---

# 7. PHASE 0 — Intake

Orchestrator nhận yêu cầu.

Ví dụ:

> "Thêm chức năng học phí."

Không được lập tức gọi Backend.

Trước tiên phải xác định:

```text
Goal:
?

Scope:
?

Affected domains:
?

Constraints:
?

Acceptance criteria:
?
```

---

# 8. PHASE 1 — Classify

Orchestrator xác định loại task.

Tôi đề xuất 6 loại:

```text
RESEARCH
BUGFIX
FEATURE
REFACTOR
INFRA
REVIEW
```

Ví dụ:

### Research

> "Kiểm tra CAMS hiện đang xử lý PGN như thế nào."

→ không sửa code.

### Bugfix

> "API students trả 500."

→ Backend + QA.

### Feature

> "Thêm quản lý học phí."

→ nhiều specialist.

### Refactor

> "Tách payment service."

→ Architect + Backend + QA + Security.

### Infra

> "Deploy CAMS lên VPS."

→ DevOps + Security + QA.

### Review

> "Audit authentication."

→ Security + Backend.

---

# 9. PHASE 2 — Routing Matrix

Đây là **trái tim của Orchestrator**.

Ta tạo một bảng:

| Domain       | Agent      |
| ------------ | ---------- |
| architecture | Architect  |
| API          | Backend    |
| DB           | Database   |
| AI/CV        | AI-CV      |
| chess        | Chess      |
| web          | Frontend   |
| mobile       | Mobile     |
| testing      | QA         |
| deployment   | DevOps     |
| security     | Security   |
| payment      | Payment    |
| tournament   | Tournament |

Nhưng phải có **primary / secondary**.

Ví dụ:

```text
Payment:

Primary:
  Payment

Secondary:
  Backend
  Database
  Security
  QA
```

Tournament:

```text
Primary:
  Tournament

Secondary:
  Chess
  Backend
  Database
  QA
```

AI scanner:

```text
Primary:
  AI-CV

Secondary:
  Chess
  Backend
  QA
```

---

# 10. PHASE 3 — Dependency Graph

Orchestrator không chỉ biết **ai làm**, mà phải biết **ai phải làm trước**.

Ví dụ Payment:

```text
                 Architect
                    │
          ┌─────────┼─────────┐
          ▼         ▼         ▼
       Payment    Database  Security
          │         │
          └────┬────┘
               ▼
            Backend
               │
               ▼
            Frontend
               │
               ▼
               QA
               │
               ▼
           Security
          final review
```

Nhưng có thể chạy song song:

```text
             Architect
                 │
        ┌────────┼────────┐
        ▼        ▼        ▼
     Payment     DB    Security
        │        │
        └────┬───┘
             ▼
          Backend
```

Antigravity cho phép parent spawn nhiều subagent concurrent, nên đây là chỗ chúng ta tận dụng multi-agent thực sự. ([Google Antigravity][2])

---

# 11. Quy tắc cực kỳ quan trọng: không spawn bừa

Orchestrator phải có luật:

```text
IF task đơn giản
    → 1 specialist

IF task liên quan 2 domain
    → 2 specialists

IF task cross-domain
    → Architect trước

IF task thay đổi code
    → QA sau implementation

IF task security-sensitive
    → Security bắt buộc

IF task payment
    → Payment + Backend + Database + QA
    → Security nếu có auth/payment state/webhook

IF deployment
    → DevOps + QA + Security

IF release
    → QA + Security
```

---

# 12. Tránh lỗi "13 agent cùng lao vào"

Ví dụ user:

> "Sửa màu nút Login."

**KHÔNG:**

```text
Architect
Backend
Database
AI-CV
Chess
Frontend
Mobile
QA
DevOps
Security
Payment
Tournament
```

Đó là orchestration tệ.

Phải:

```text
Frontend
   ↓
QA
```

Thậm chí nếu thay đổi CSS rất nhỏ:

```text
Frontend
```

rồi chạy kiểm tra phù hợp.

---

# 13. Context Packet

Đây là phần tôi rất muốn thêm vào CAMS.

Mỗi lần Orchestrator gọi specialist, **không gửi một prompt dài lan man**.

Gửi một `Task Packet` chuẩn:

```yaml
task_id: CAMS-XXXX
type: FEATURE
title: Add tuition payment

objective: >
  Implement tuition payment Level 1.

source_of_truth:
  - docs/SDLC.md
  - docs/05_payment_architecture.md

affected_modules:
  - backend
  - database
  - frontend
  - payment

constraints:
  - Level 1 required
  - Level 2 optional
  - no gateway required

dependencies:
  - database schema
  - invoice model

acceptance_criteria:
  - invoice created
  - VietQR generated
  - admin can confirm
  - payment status audited

read_only: false

expected_output:
  - files_changed
  - implementation_summary
  - tests
  - risks
  - unresolved_questions
```

Điều này cực kỳ quan trọng vì subagent được spawn có **context window độc lập**, không tự thừa hưởng toàn bộ conversation của parent. ([Google Antigravity][2])

---

# 14. Result Contract

Specialist cũng không được trả lời tùy ý.

Mỗi specialist phải trả:

```text
STATUS
SCOPE
CHANGES
TESTS
RISKS
DEPENDENCIES
BLOCKERS
NEXT_ACTION
```

Ví dụ Backend:

```text
STATUS: DONE

SCOPE:
Payment API

CHANGES:
- POST /payments
- GET /payments/{id}
- confirm payment endpoint

TESTS:
- 12 passed

RISKS:
- webhook idempotency not implemented

DEPENDENCIES:
- DB migration applied

BLOCKERS:
- none

NEXT_ACTION:
- QA integration test
```

Orchestrator đọc format này rất dễ.

---

# 15. `send_message` dùng khi nào?

Quy tắc:

```text
invoke_subagent
    ↓
spawn session
    ↓
session tồn tại
    ↓
send_message
```

Không bao giờ:

```text
send_message
    ↓
hy vọng agent tự xuất hiện
```

Đây chính là lỗi chúng ta vừa sửa xong.

Antigravity hiện hỗ trợ `send_message` cho giao tiếp giữa các agent có conversation ID; `manage_subagents` dùng để list/terminate session. ([Google Antigravity][1])

---

# 16. Không để specialist tự gọi specialist vô hạn

Tôi đề xuất:

```text
Orchestrator
   │
   ├── Architect
   ├── Backend
   ├── Database
   └── ...
```

**Specialist không tự spawn specialist khác**, trừ khi Orchestrator cấp quyền rõ ràng.

Lý do:

```text
Backend
 ↓
Database
 ↓
Architect
 ↓
Backend
 ↓
...
```

rất dễ thành recursion.

Antigravity hiện có giới hạn nesting tối đa 10 tầng, nhưng CAMS không nên dựa vào giới hạn đó; nên tự áp policy ở tầng Orchestrator. ([Google Antigravity][3])

---

# 17. Quy tắc workspace

Đây là điểm cực kỳ quan trọng khi chạy song song.

### Research / Read-only

```text
workspace: inherit
```

OK.

### Parallel implementation

Tôi khuyến nghị:

```text
workspace: branch
```

nếu task có thể sửa code độc lập.

Antigravity hỗ trợ `branch` để tạo isolated Git worktree. ([Google Antigravity][2])

Ví dụ:

```text
Frontend ───── branch/frontend-payment
Backend  ───── branch/backend-payment
Database ───── branch/database-payment
```

Sau đó Orchestrator điều phối việc tích hợp.

**Không cho 3 agent cùng sửa một file trên `inherit` nếu không cần thiết.**

---

# 18. QA không được chạy quá sớm

Sai:

```text
Backend đang code
     ↓
QA chạy
```

Đúng:

```text
Backend
Database
Frontend
     │
     ▼
Implementation complete
     │
     ▼
QA
```

QA phải nhận:

```text
changed files
API contract
acceptance criteria
test instructions
```

---

# 19. Security cũng là Gate

Security không cần chạy cho mọi CSS change.

Nhưng bắt buộc với:

```text
authentication
authorization
payment
personal data
file upload
API exposure
webhook
secrets
deployment
database permissions
```

Ví dụ Payment:

```text
Payment
Backend
Database
     │
     ▼
QA
     │
     ▼
Security
     │
     ▼
Release
```

---

# 20. Final Gate

Orchestrator chỉ được báo:

```text
DONE
```

khi:

```text
Implementation      PASS
Tests               PASS
QA                  PASS
Security            PASS / NOT_REQUIRED
Docs                UPDATED / NOT_REQUIRED
Git status          CLEAN / EXPECTED
```

Nếu QA fail:

```text
QA FAIL
   ↓
Orchestrator
   ↓
gửi đúng lỗi
   ↓
specialist sửa
   ↓
QA lại
```

Không spawn lại toàn bộ pipeline.

---

# 21. Tôi đề xuất thêm State Machine cho Orchestrator

```text
RECEIVED
   ↓
ANALYZING
   ↓
PLANNED
   ↓
DELEGATED
   ↓
IMPLEMENTING
   ↓
VERIFYING
   ↓
QA
   ↓
SECURITY
   ↓
INTEGRATING
   ↓
DONE
```

Có lỗi:

```text
ANY STATE
   │
   ▼
BLOCKED
   │
   ├── dependency
   ├── permission
   ├── unclear requirement
   └── specialist failure
```

Không được giả vờ `DONE`.

---

# 22. Bộ não thực tế của `cams-orchestrator`

Tôi đề xuất thay body hiện tại bằng cấu trúc này:

```markdown
# CAMS Orchestrator

Bạn là bộ điều phối trung tâm của Chess Academy Management System (CAMS).

Bạn KHÔNG phải implementation agent mặc định.

Mục tiêu của bạn là:

1. Hiểu yêu cầu.
2. Phân loại task.
3. Xác định specialist cần thiết.
4. Xây dependency graph.
5. Spawn specialist bằng invoke_subagent.
6. Chạy song song khi các task độc lập.
7. Điều phối dependency giữa các specialist.
8. Thu nhận kết quả.
9. Yêu cầu QA.
10. Yêu cầu Security khi cần.
11. Tích hợp kết quả.
12. Chỉ báo DONE khi Definition of Done đạt.

---

# 1. SOURCE OF TRUTH

Trước khi quyết định kiến trúc hoặc thay đổi hành vi hệ thống:

- Đọc docs/SDLC.md.
- Đọc tài liệu domain liên quan.
- Không tự ý thay đổi architecture nếu chưa có căn cứ.

---

# 2. SPECIALIST ROUTING

Architecture:

- cams-architect

Backend/API:

- cams-backend

Database:

- cams-database

AI/CV:

- cams-ai-cv

Chess:

- cams-chess

Web:

- cams-frontend

Mobile:

- cams-mobile

Testing:

- cams-qa

Infrastructure:

- cams-devops

Security:

- cams-security

Payment:

- cams-payment

Tournament:

- cams-tournament

---

# 3. DELEGATION RULE

Always use invoke_subagent to create a new specialist session.

Never use send_message to create a new agent.

Use send_message only when a valid subagent session/conversation already exists.

Never claim that delegation happened unless the tool invocation actually happened.

---

# 4. TASK CLASSIFICATION

Classify every request as one of:

- RESEARCH
- BUGFIX
- FEATURE
- REFACTOR
- INFRA
- REVIEW

---

# 5. SIMPLE TASK RULE

Do not spawn unnecessary agents.

Examples:

CSS/UI-only:
Frontend → QA if needed.

Backend bug:
Backend → QA.

Database-only migration:
Database → QA.

Research:
appropriate read-only specialist only.

---

# 6. CROSS-DOMAIN RULE

For cross-domain changes:

Architect first when architectural decisions are required.

Then delegate implementation to the affected specialists.

---

# 7. PARALLELISM

Run independent tasks concurrently.

Do not run dependent tasks concurrently.

Example:

Architect
↓
Database + Payment + Security
↓
Backend
↓
Frontend
↓
QA
↓
Security final review

---

# 8. CONTEXT PACKET

Every delegated task must include:

- task_id
- objective
- source_of_truth
- affected_modules
- constraints
- dependencies
- acceptance_criteria
- expected_output

---

# 9. RESULT CONTRACT

Every specialist must report:

- STATUS
- SCOPE
- CHANGES
- TESTS
- RISKS
- DEPENDENCIES
- BLOCKERS
- NEXT_ACTION

---

# 10. WORKSPACE SAFETY

Read-only research may use inherit.

Parallel implementation should prefer isolated branch/worktree when appropriate.

Do not allow multiple agents to modify the same files concurrently without an explicit integration plan.

---

# 11. QA GATE

Any implementation that changes executable code should normally pass QA before final completion.

QA failures must be routed back to the responsible specialist.

Do not mark DONE while known QA blockers remain.

---

# 12. SECURITY GATE

Security review is required for:

- authentication
- authorization
- payment
- webhook
- personal data
- file upload
- secrets
- public API exposure
- deployment
- permission changes

---

# 13. PAYMENT RULE

CAMS payment architecture:

Level 1 = required MVP.
Level 2 = optional.
Level 3 = optional.

Do not force Level 2/3 into an MVP implementation unless explicitly requested.

---

# 14. FAILURE RULE

If a specialist fails:

1. inspect the failure;
2. determine whether retry is appropriate;
3. send the corrected task;
4. do not blindly spawn duplicates.

If requirement is ambiguous:
ask the user instead of inventing requirements.

---

# 15. FINAL GATE

Only report DONE when:

- implementation complete;
- required tests pass;
- QA passes;
- required security review passes;
- blockers are resolved;
- documentation is updated when required.

Otherwise report BLOCKED or INCOMPLETE.

Never fabricate successful delegation, testing, or implementation.
```

---

# 23. Tôi còn muốn tách "bộ não" thành Rule riêng

**Không nên nhét toàn bộ orchestration policy vào `agent.md`.**

Cấu trúc nên thành:

```text
.agents/
│
├── agents/
│   ├── 00-orchestrator/
│   │   └── agent.md
│   ├── 01-architect/
│   ├── 02-backend/
│   ├── ...
│   └── 12-tournament/
│
└── rules/
    ├── 00-cams-project.md
    ├── 01-git-workflow.md
    ├── 02-code-quality.md
    ├── 03-agent-collaboration.md
    └── 04-orchestration-policy.md   ← THÊM
```

Antigravity hiện load các rule trong `.agents/rules/*.md`, và rule phải có frontmatter hợp lệ nếu dùng rule dạng modular. ([Google Antigravity][4])

Tôi sẽ để:

### `agent.md`

chứa:

> **Orchestrator là ai và nó phải làm gì.**

### `04-orchestration-policy.md`

chứa:

> **Khi nào gọi ai, theo thứ tự nào, khi nào song song, khi nào QA/Security.**

Đây là thiết kế sạch hơn.

---

# 24. Và quan trọng nhất: đừng biến Orchestrator thành "siêu agent làm tất cả"

Nguyên tắc tôi muốn giữ cho CAMS:

```text
Orchestrator
    ≠ coder
    ≠ database expert
    ≠ chess expert
    ≠ security expert
```

Mà:

```text
Orchestrator
      =
     CEO
      +
  Project Manager
      +
  Technical Coordinator
```

Specialist mới là người **làm việc chuyên môn**.

```text
                    ORCHESTRATOR
                         │
          ┌──────────────┼──────────────┐
          │              │              │
       Architect      Specialists      Gates
          │              │              │
          │        ┌─────┼─────┐        │
          │        │     │     │        │
          │       DB   Backend Frontend QA/Security
          │        │     │     │        │
          └────────┴─────┴─────┴────────┘
                         │
                         ▼
                      RESULT
```

**Đó là “bộ não” tôi đề xuất cho CAMS.**

Và vì `invoke_subagent` của Ông chủ đã PASS thực tế, bước triển khai hợp lý tiếp theo là **tạo `04-orchestration-policy.md` + thay body `00-orchestrator/agent.md` theo thiết kế trên**, rồi dùng một task thực tế nhỏ để test routing trước khi cho Orchestrator xử lý task lớn.

[1]: https://www.antigravity.google/docs/hooks?utm_source=chatgpt.com "Hooks | Google Antigravity Docs"
[2]: https://www.antigravity.google/docs/subagents/?utm_source=chatgpt.com "Custom Subagents | Google Antigravity Docs"
[3]: https://antigravity.google/docs/subagents?tab=cli&utm_source=chatgpt.com "Custom Subagents | Google Antigravity Docs"
[4]: https://antigravity.google/docs/rules/?utm_source=chatgpt.com "Rules | Google Antigravity Docs"
