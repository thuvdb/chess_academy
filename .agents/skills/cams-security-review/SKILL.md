---
name: cams-security-review
description: >
  Quy trình chuẩn security review trong CAMS.
  Dùng khi cams-security nhận task review code/config liên quan auth, payment, data, upload, API, webhook, secrets, hoặc deployment.
  Không cần trigger cho thay đổi CSS/label/copy thuần UI.
---

# CAMS Security Review Skill

Quy trình step-by-step khi thực hiện security review trong CAMS.

## Khi nào Security Review bắt buộc?

Theo `04-orchestration-policy.md` §7:

- Authentication / Authorization
- Payment (mọi level)
- Personal data (PII)
- File upload
- API exposure (public endpoints)
- Webhook / callback
- Secrets management
- Deployment
- Database permission changes

**KHÔNG** cần cho: thay đổi CSS, label, copy thuần UI, không đụng logic hay dữ liệu.

## Source of Truth

- `docs/02-architecture/02_system_design.md` → Auth/RBAC design
- `docs/02-architecture/PAYMENT_ARCHITECTURE.md` → Payment security
- `docs/03-operations/05_deployment.md` → Deployment security checklist
- OWASP Top 10 (external reference)

## Quy trình Review

### Bước 1 — Scope Assessment

1. Đọc Context Packet và Result Contracts từ specialists.
2. Xác định: code nào thay đổi? Domain nào bị ảnh hưởng?
3. Phân loại severity tier:
   - **Critical**: auth bypass, payment manipulation, SQL injection
   - **High**: RBAC bypass, data exposure, insecure webhook
   - **Medium**: missing validation, weak password policy, verbose error
   - **Low**: missing headers, minor config issues

### Bước 2 — Authentication Review

1. Password hashing dùng bcrypt hoặc argon2 — KHÔNG MD5/SHA1.
2. JWT:
   - Access token short-lived (15-30 min).
   - Refresh token longer, stored securely.
   - Token phải có expiration.
   - Không lưu sensitive data trong JWT payload.
3. OAuth (Google/Facebook):
   - Verify token với provider.
   - Không trust client-side token claims.
4. Session: Redis-backed, httponly cookies khi dùng browser.

### Bước 3 — Authorization / RBAC Review

1. Kiểm tra quyền ở **server**, không tin UI.
2. CAMS roles: `super_admin`, `admin`, `teacher`, `student`, `parent`.
3. Mỗi endpoint phải check:
   - User authenticated?
   - User có role phù hợp?
   - User có quyền trên resource cụ thể? (center-scoped, class-scoped)
4. Không có horizontal privilege escalation (student A xem data student B).

### Bước 4 — Input Validation & Injection

1. SQL Injection: dùng parameterized queries (SQLAlchemy ORM đã handle, nhưng raw query phải check).
2. XSS: sanitize output, Content-Security-Policy headers.
3. CSRF: CSRF token cho form submissions.
4. SSRF: validate URLs, không fetch arbitrary URLs từ user input.
5. Path traversal: validate file paths, không cho `../`.

### Bước 5 — Payment Security

1. Payment state chỉ thay đổi qua server logic, KHÔNG từ client.
2. Webhook verify signature/checksum trước khi process.
3. Webhook idempotent — duplicate call không tạo duplicate payment.
4. Admin confirm payment: kiểm tra RBAC, log who confirmed.
5. Không lưu bank account / credit card detail.

### Bước 6 — File Upload Security

1. Validate file type (MIME + magic bytes, không chỉ extension).
2. Validate file size (limit).
3. Store trong MinIO, không trong application directory.
4. Không serve user-uploaded files trực tiếp — dùng presigned URL.
5. Scan for malware nếu có capability.

### Bước 7 — Secrets & Configuration

1. Không có secret trong source control.
2. `.env` files trong `.gitignore`.
3. API keys, DB credentials, JWT secret → environment variables.
4. Khác biệt dev/staging/prod configuration.

### Bước 8 — Deployment Security

1. HTTPS bắt buộc cho production.
2. Database không expose public port.
3. Docker images: dùng non-root user.
4. Health check endpoints không leak internal info.
5. Error messages: user-friendly, không lộ stack trace / internal path.

### Bước 9 — Báo cáo Result Contract

```
STATUS: DONE
SCOPE: Security review cho task CAMS-XXXX

CHANGES:
- (Thường read-only, trừ khi phát hiện vuln cần fix ngay)

TESTS:
- Security scan results
- Manual review checklist

FINDINGS:
- [CRITICAL] Mô tả + evidence + remediation
- [HIGH] ...
- [MEDIUM] ...
- [LOW] ...

VERDICT: PASS | FAIL | PASS_WITH_WARNINGS

RISKS:
- Residual risks sau khi fix

DEPENDENCIES:
- Specialist nào cần sửa nếu có findings

BLOCKERS:
- Critical/High findings chưa fix

NEXT_ACTION:
- Fix findings → re-review, hoặc DONE
```

## Quy tắc bổ sung

- Security review phải có **evidence** cho mỗi finding — không chỉ nêu lý thuyết.
- Severity phải match với impact thực tế trong CAMS context.
- Không tự ý phá hoặc xoá dữ liệu để kiểm thử.
- PASS_WITH_WARNINGS: chỉ khi findings là LOW và không block release.
