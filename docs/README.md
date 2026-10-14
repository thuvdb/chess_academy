# 📚 Tài liệu CAMS — Mục lục tổng (Table of Contents)

> Tài liệu kỹ thuật của **Chess Academy Management System (CAMS)**.  
> Mọi đường dẫn trong file này là **đường dẫn tương đối** từ thư mục `docs/`.

---

## 📁 01-sdlc — Vòng đời phát triển phần mềm

Các tài liệu mô tả quy trình SDLC từ phân tích yêu cầu đến kiểm thử.

| File | Nội dung |
|------|----------|
| [SDLC.md](./01-sdlc/SDLC.md) | Tổng quan SDLC — mục lục chính của toàn bộ vòng đời phát triển CAMS |
| [01_requirements.md](./01-sdlc/01_requirements.md) | Giai đoạn 1 — Phân tích Yêu cầu (Stakeholders, FR, NFR, User Stories) |
| [03_sprint_plan.md](./01-sdlc/03_sprint_plan.md) | Giai đoạn 3 — Sprint Plan (Sprint 0–8 + 3A/3B/3C/3D, ~20 tuần) |
| [04_testing.md](./01-sdlc/04_testing.md) | Giai đoạn 4 — Chiến lược Kiểm thử (Unit, Integration, AI, E2E, Load) |

---

## 📁 02-architecture — Kiến trúc hệ thống

Tài liệu thiết kế kiến trúc kỹ thuật cho từng domain chuyên biệt.

| File | Nội dung |
|------|----------|
| [02_system_design.md](./02-architecture/02_system_design.md) | Giai đoạn 2 — Thiết kế Hệ thống (Kiến trúc, DB Schema, API, Screen Map) |
| [AI_SCANNER_ARCHITECTURE.md](./02-architecture/AI_SCANNER_ARCHITECTURE.md) | Kiến trúc AI Scanner Pipeline (PDF → OpenCV → YOLO → FEN, MLOps) |
| [PAYMENT_ARCHITECTURE.md](./02-architecture/PAYMENT_ARCHITECTURE.md) | Kiến trúc Payment Service (3 cấp Level 1/2/3, State Machine, VietQR) |
| [TOURNAMENT_ARCHITECTURE.md](./02-architecture/TOURNAMENT_ARCHITECTURE.md) | Kiến trúc Giải đấu (Swiss/Round Robin, WebSocket, Redis Game State) |

---

## 📁 03-operations — Vận hành & Bàn giao

Tài liệu triển khai, bảo trì và quy trình vận hành hệ thống.

| File | Nội dung |
|------|----------|
| [05_deployment.md](./03-operations/05_deployment.md) | Giai đoạn 5 — Triển khai & DevOps (Docker, CI/CD, Production Checklist) |
| [06_maintenance.md](./03-operations/06_maintenance.md) | Giai đoạn 6 — Bảo trì & Lộ trình (MLOps, Roadmap v1→v3.5) |
| [HANDOFF_SOP.md](./03-operations/HANDOFF_SOP.md) | Quy trình Bàn giao tài khoản Gemini Pro & Checkpoint kỹ thuật |

---

## 📁 04-guides — Hướng dẫn sử dụng

> 🚧 Thư mục dành cho hướng dẫn vận hành, onboarding, và FAQ — chưa có tài liệu.

---

## Sơ đồ quan hệ tài liệu

```
docs/
├── README.md          ← Bạn đang ở đây (Mục lục tổng)
│
├── 01-sdlc/
│   ├── SDLC.md        ← Điểm vào chính, liên kết tới tất cả tài liệu SDLC
│   ├── 01_requirements.md
│   ├── 03_sprint_plan.md
│   └── 04_testing.md
│
├── 02-architecture/
│   ├── 02_system_design.md
│   ├── AI_SCANNER_ARCHITECTURE.md
│   ├── PAYMENT_ARCHITECTURE.md
│   └── TOURNAMENT_ARCHITECTURE.md
│
├── 03-operations/
│   ├── 05_deployment.md
│   ├── 06_maintenance.md
│   └── HANDOFF_SOP.md
│
└── 04-guides/         ← (trống, sẵn sàng)
```

---

> **Xem thêm:** [README.md gốc dự án](../README.md) — hướng dẫn cài đặt và khởi động nhanh CAMS.
