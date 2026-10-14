# HANDOFF SOP — Quy trình chuyển đổi tài khoản Gemini Pro trong CAMS

> Standard Operating Procedure khi cần đổi tài khoản Gemini Pro giữa chừng.
> Xem thêm giải thích chi tiết tại [Q&A.md](../Q&A.md).

---

## Khi nào cần HANDOFF?

- TK hiện tại hết quota
- TK hiện tại bị lỗi / bị khoá tạm
- Chuyển từ TK cá nhân sang TK tổ chức (hoặc ngược lại)
- Kết thúc phiên làm việc, người khác tiếp tục

---

## Bước 1: Tạo HANDOFF checkpoint (trước khi logout TK cũ)

Gửi prompt sau cho agent:

```text
Before we switch to another Gemini account, create a complete
CAMS handoff checkpoint.

Do NOT modify implementation unless necessary.

Record:
1. Current task
2. Current phase
3. What has been completed
4. What remains
5. Files changed
6. Tests completed and results
7. Current blockers
8. Current decisions
9. Pending decisions
10. Task Ledger state
11. Git state (branch hiện tại, last commit, uncommitted changes)
12. Exact next action for the next agent

Save this checkpoint into the project's persistent state,
not only in conversation context.
```

Agent sẽ tạo / cập nhật:

```
.agents/
├── state/
│   └── <task_id>.json        ← Task Ledger (có handoff field)
└── handoff/
    └── <task_id>-handoff.md  ← Handoff report chi tiết
```

## Bước 2: Commit code (nếu ở mốc an toàn)

```bash
git add -A
git commit -m "chore: handoff checkpoint for CAMS-<ID>"
```

Nếu specialist đang làm dở trên branch riêng, commit vào branch đó — **không merge vào main**.

## Bước 3: Logout TK cũ

Logout khỏi Antigravity IDE / CLI.

## Bước 4: Login TK mới

Login TK Gemini Pro mới vào Antigravity IDE / CLI.  
Mở lại cùng CAMS project (cùng workspace).

## Bước 5: Resume task (TK mới)

### Nếu biết task ID:

```text
Resume CAMS task CAMS-<ID>.

Read these files in order:
1. .agents/state/<task_id>.json
2. .agents/handoff/<task_id>-handoff.md (if exists)
3. Relevant docs from source_of_truth listed in Task Ledger

Report:
- Current state and phase
- What has been completed
- What remains
- Any blockers

Then continue from the next_action.
Do NOT re-implement anything already marked DONE.
Do NOT assume context from any previous conversation.
```

### Nếu không biết task ID:

```text
List all CAMS tasks in .agents/state/ and show their current status.
Identify which tasks are IN_PROGRESS or BLOCKED.
```

---

## Checklist nhanh

| Việc                                | Cần?              | Ai làm?                          |
| ----------------------------------- | ----------------- | -------------------------------- |
| Compact conversation                | ❌ Không bắt buộc | —                                |
| Tạo HANDOFF                         | ✅ Nên            | Agent (trước khi logout)         |
| Cập nhật Task Ledger                | ✅ Rất nên        | Agent (tự động mỗi phase)        |
| Ghi Git state (branch, commit)      | ✅ Nên            | Agent (trong handoff)            |
| Commit code nếu đang ở mốc an toàn | ✅ Nên            | Agent hoặc User                  |
| Lưu quyết định quan trọng vào file  | ✅ Nên            | Agent                            |
| Logout TK1                          | ✅                | User                             |
| Login TK2                           | ✅                | User                             |
| TK2 đọc CAMS state (resume prompt)  | ✅                | Agent (tự động qua resume prompt)|
| Hy vọng TK2 tự nhớ conversation TK1 | ❌ Không nên      | —                                |

---

## Lưu ý quan trọng

### Terms of Service

> Việc sử dụng nhiều tài khoản Gemini Pro để luân phiên khi hết quota **có thể vi phạm Terms of Service** của Google nếu mục đích là bypass rate limit.
> - Dùng mỗi TK cho mục đích chính đáng (VD: TK cá nhân + TK tổ chức)
> - Không dùng script/tool tự động đổi TK để bypass quota
> - Theo dõi cập nhật TOS từ Google

### Nguyên tắc cốt lõi

```
Gemini context  = bộ nhớ tạm (volatile, per-session)
Task Ledger     = bộ nhớ lâu dài (persistent, per-project)
```

**Task Ledger là source of truth, không phải conversation history.**
