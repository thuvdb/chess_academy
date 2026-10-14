# SDLC — Chess Academy Management System (CAMS)

> **Phiên bản:** 2.0 | **Ngày cập nhật:** 2026-09-20 | **Trạng thái:** Đang phát triển

---

## Giới thiệu

**CAMS** — Hệ thống Quản lý Học viện Cờ Vua trực tuyến. Nền tảng toàn diện giúp trung tâm dạy cờ vua số hoá toàn bộ hoạt động: quản lý lớp học, AI quét bài tập từ PDF, luyện tập tương tác, thanh toán học phí và tổ chức giải đấu online.

---

## Cấu trúc tài liệu

| File                                                       | Nội dung                                                                |
| ---------------------------------------------------------- | ----------------------------------------------------------------------- |
| [01_requirements.md](./01_requirements.md)                 | Giai đoạn 1 — Phân tích Yêu cầu (Stakeholders, FR, NFR, User Stories)   |
| [02_system_design.md](../02-architecture/02_system_design.md)               | Giai đoạn 2 — Thiết kế Hệ thống (Kiến trúc, DB Schema, API, Screen Map) |
| [03_sprint_plan.md](./03_sprint_plan.md)                   | Giai đoạn 3 — Sprint Plan (Sprint 0–8 + 3A/3B/3C/3D, ~20 tuần)          |
| [04_testing.md](./04_testing.md)                           | Giai đoạn 4 — Chiến lược Kiểm thử (Unit, Integration, AI, E2E, Load)    |
| [05_deployment.md](../03-operations/05_deployment.md)                     | Giai đoạn 5 — Triển khai & DevOps (Docker, CI/CD, Production Checklist) |
| [06_maintenance.md](../03-operations/06_maintenance.md)                   | Giai đoạn 6 — Bảo trì & Lộ trình (MLOps, Roadmap v1→v3.5)               |
| [PAYMENT_ARCHITECTURE.md](../02-architecture/PAYMENT_ARCHITECTURE.md)       | Kiến trúc Payment Service (3 cấp Level 1/2/3, State Machine, Webhook)   |
| [AI_SCANNER_ARCHITECTURE.md](../02-architecture/AI_SCANNER_ARCHITECTURE.md) | Kiến trúc AI Scanner (3 Service + FEN Validation + MLOps)               |
| [TOURNAMENT_ARCHITECTURE.md](../02-architecture/TOURNAMENT_ARCHITECTURE.md) | Kiến trúc Giải đấu (Swiss/Round Robin, WebSocket, Redis Game State)     |

---

## Tech Stack

| Layer        | Công nghệ                 | Lý do                            |
| ------------ | ------------------------- | -------------------------------- |
| Backend API  | Python / FastAPI          | Async, tích hợp AI tốt           |
| Frontend Web | React + Vite + TypeScript | Hiệu năng cao, type-safe         |
| Mobile       | React Native (Expo)       | Code sharing iOS/Android         |
| Database     | PostgreSQL 16             | Quan hệ phức tạp, ACID           |
| Cache        | Redis 7                   | Session, game state, leaderboard |
| File Storage | Local Filesystem + HMAC   | PDF, ảnh bàn cờ (S3 future-ready)|
| AI / CV      | OpenCV + YOLOv8           | Nhận diện bàn cờ                 |
| Chess Engine | Stockfish + python-chess  | Phân tích nước đi                |
| Payment      | VNPay / MoMo / VietQR     | Cổng thanh toán Việt Nam         |
| Push Notify  | Firebase FCM              | Notification mobile              |
| Email        | SendGrid                  | Gửi email tự động                |
| Container    | Docker + Docker Compose   | Triển khai                       |
| CI/CD        | GitHub Actions            | Tự động test & deploy            |

---

## Lộ trình tổng quan

| Phiên bản    | Timeline                | Tính năng chính                                                                                        |
| ------------ | ----------------------- | ------------------------------------------------------------------------------------------------------ |
| **v1.0 MVP** | Sprint 0–4 (tuần 1–12)  | Auth (email + Google + Facebook), Lớp học, AI Scanner (3A→3D), Luyện tập, Chấm điểm AI & thủ công, ELO |
| **v1.5**     | Sprint 5–6 (tuần 13–16) | Thanh toán Level 1 (VietQR + Admin confirm), Giải đấu online                                           |
| **v2.0**     | Sprint 7–8 (tuần 17–20) | Mobile App iOS/Android, Push Notifications, Offline cache                                              |
| **v2.5**     | Q1 2027                 | Multi-center SaaS, Super Admin, Thanh toán Level 2 (Webhook auto)                                      |
| **v3.0**     | Q2 2027                 | AI Coach, Lichess/Chess.com sync, Thanh toán Level 3 (VNPay/MoMo đầy đủ)                               |
| **v3.5**     | Q3 2027                 | Video lesson management, Live streaming giải đấu                                                       |

---

_Tài liệu được cập nhật liên tục theo tiến độ dự án. Xem chi tiết từng giai đoạn trong các file con._
