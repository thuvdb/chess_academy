# CAMS Project Rule

CAMS = Chess Academy Management System.

Source of truth:
1. `SDLC.md`
2. Documents explicitly referenced by `SDLC.md`
3. Current code and tests
4. User-approved decisions in the current task

Không tự bịa requirement. Nếu tài liệu không đủ, nêu rõ gap.

Core architecture:
- Frontend: React/Vite
- Mobile: React Native/Expo
- Backend: FastAPI
- Database: PostgreSQL
- Cache/queue: Redis
- Object storage: MinIO
- Worker: background/Celery-style worker
- Chess: python-chess/Stockfish where applicable

Payment:
- Level 1 = MVP requirement.
- Level 2 = optional automation.
- Level 3 = optional full gateway.
Không tạo dependency bắt buộc vào Level 2/3 nếu task không yêu cầu.
