---
name: cams-handoff
description: >
  Quy trình tạo handoff checkpoint khi cần chuyển TK Gemini Pro trong CAMS.
  Dùng khi Orchestrator hoặc user yêu cầu tạo handoff trước khi đổi tài khoản,
  kết thúc phiên, hoặc khi phát hiện quota sắp hết.
---

# CAMS Handoff Skill

## Khi nào kích hoạt

- User yêu cầu "tạo handoff", "chuyển TK", "save checkpoint"
- Agent phát hiện quota warning / rate limit
- User yêu cầu "kết thúc phiên làm việc"

## Quy trình tạo HANDOFF

### Bước 1: Thu thập trạng thái

Đọc các nguồn sau:

1. **Task Ledger**: `.agents/state/` — tìm tất cả file `.json`, liệt kê task `IN_PROGRESS` hoặc `BLOCKED`
2. **Git state**: chạy các lệnh (nếu không phải git repo thì ghi `N/A`):
   ```bash
   git branch --show-current
   git log -1 --oneline
   git status --porcelain
   ```
3. **Conversation context**: tóm tắt những gì đã làm trong phiên hiện tại

### Bước 2: Cập nhật Task Ledger

Với mỗi task đang `IN_PROGRESS`, cập nhật file `.agents/state/<task_id>.json`:

```json
{
  "...existing fields...",
  "handoff": {
    "triggered_at": "<ISO timestamp hiện tại>",
    "reason": "quota_exhausted | manual | error",
    "resume_prompt": "<mô tả ngắn gọn bước tiếp theo>",
    "git_state": {
      "branch": "<branch hiện tại hoặc N/A>",
      "last_commit": "<commit hash ngắn hoặc N/A>",
      "has_uncommitted": "true | false | N/A"
    }
  },
  "updated_at": "<ISO timestamp hiện tại>"
}
```

### Bước 3: Tạo handoff report

Tạo file `.agents/handoff/<task_id>-handoff.md`:

```markdown
# Handoff Report — <task_id>

## Timestamp
<ISO timestamp>

## Reason
<quota_exhausted | manual | error>

## Current State
- **Phase**: <phase hiện tại>
- **Status**: <IN_PROGRESS | BLOCKED>
- **Progress**: <mô tả ngắn>

## Completed
- <liệt kê cụ thể những gì đã xong>

## Remaining
- <liệt kê cụ thể những gì chưa xong>

## Files Changed
- <liệt kê file đã thay đổi trong phiên này>

## Tests
- <kết quả test: pass/fail/not_run>

## Blockers
- <nếu có>

## Decisions Made
- <các quyết định đã chốt trong phiên này>

## Pending Decisions
- <các quyết định chưa chốt, cần user input>

## Git State
- Branch: `<branch>`
- Last commit: `<hash> <message>`
- Uncommitted changes: <yes/no>

## Next Action
<bước tiếp theo CỤ THỂ cho agent tiếp nhận>
```

### Bước 4: Commit (nếu an toàn)

Nếu code đang ở trạng thái ổn định (không giữa chừng refactor):

```bash
git add .agents/state/<task_id>.json .agents/handoff/<task_id>-handoff.md
git commit -m "chore: handoff checkpoint for <task_id>"
```

Nếu đang giữa chừng implementation trên branch riêng:

```bash
git add -A
git commit -m "WIP: handoff checkpoint for <task_id> (incomplete)"
```

### Bước 5: Báo cáo cho user

Output cuối cùng phải bao gồm:

```
HANDOFF COMPLETE

Task:       <task_id>
Phase:      <phase>
Status:     <status>
Branch:     <branch>
Last Commit: <hash>

Resume prompt for next account:
─────────────────────────────────
Resume CAMS task <task_id>.

Read these files in order:
1. .agents/state/<task_id>.json
2. .agents/handoff/<task_id>-handoff.md
3. <source_of_truth files>

Then continue from the next_action.
Do NOT re-implement anything already marked DONE.
─────────────────────────────────

You can now safely logout and login with another Gemini account.
```

## Quy trình RESUME (TK mới vào)

Khi agent mới nhận được resume prompt:

1. **Đọc Task Ledger** — xác định task, phase, status
2. **Đọc handoff report** — hiểu context chi tiết
3. **Kiểm tra Git state** — checkout đúng branch nếu cần
4. **Báo cáo trạng thái** — xác nhận với user trước khi tiếp tục
5. **Tiếp tục từ next_action** — không re-implement, không giả định

## Lưu ý

- Skill này **không sửa code** — chỉ thu thập và ghi trạng thái
- `read_only: true` ngoại trừ file `.agents/state/` và `.agents/handoff/`
- Nếu có nhiều task IN_PROGRESS, tạo handoff cho **tất cả**
- Thư mục `.agents/handoff/` sẽ được tạo tự động nếu chưa tồn tại
