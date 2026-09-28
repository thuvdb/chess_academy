# Git Workflow Rule

- Mỗi feature/bug lớn dùng branch/worktree riêng.
- Không ghi đè thay đổi của agent khác.
- Trước khi kết thúc: kiểm tra diff, test liên quan và file thay đổi.
- Không commit secrets.
- Migration/schema changes phải được review.
- Không squash/merge branch khác nếu chưa được yêu cầu.
