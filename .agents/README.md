# CAMS Multi-Agent Pack for Antigravity

Gói cấu hình mẫu cho CAMS.

## Cài đặt
Copy thư mục `.agents` vào thư mục gốc repository CAMS:

CAMS/
├── .agents/
│   ├── agents/
│   └── rules/

Sau đó mở lại Antigravity và kiểm tra Customizations/Agents.

## Model strategy
- `pro`: Architect, Backend, Database, AI/CV, Chess, QA, DevOps, Security, Payment, Tournament
- `flash`: Frontend, Mobile

`model: pro` là model tier, không phải một Google account riêng cho từng agent.

## Nếu Antigravity IDE hiện tại chưa nhận custom agents
Tài liệu Google hiện ghi Custom Agents được hỗ trợ đầy đủ trên Antigravity 2.0/CLI; IDE đang có Agent/parallel conversations và Rules/Skills. Khi IDE build của bạn chưa discover `.agents/agents`, có thể dùng Antigravity 2.0/CLI để chạy custom-agent pack này. Không cần thay đổi kiến trúc project.

## Kích hoạt
Trong môi trường hỗ trợ custom agents, mở Agent Manager (`/agents` trong CLI) để kiểm tra agent và subagents.

## Thứ tự triển khai khuyến nghị
1. Orchestrator
2. Architect
3. Backend
4. Database
5. AI/CV
6. Chess
7. Frontend
8. QA
9. Security
10. DevOps
11. Mobile (khi tới roadmap mobile)
12. Payment/Tournament (khi tới các sprint tương ứng)
