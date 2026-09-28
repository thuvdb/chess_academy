# Giai đoạn 6: Bảo trì & Lộ trình (Maintenance & Roadmap)

> **CAMS — Chess Academy Management System**
> Tài liệu con của [SDLC.md](./SDLC.md)

---

## 6.1 Bug Tracking Workflow

- GitHub Issues với labels: `bug`, `feature`, `ai-model`, `payment`, `security`, `urgent`
- **SLA:**
  - `urgent` (crash / payment failure / security) → fix trong **4 giờ**
  - `bug` bình thường → sprint tiếp theo
  - `feature` → backlog prioritization theo roadmap

### Bug Report Template
```markdown
## Mô tả lỗi
[Mô tả ngắn gọn]

## Bước tái hiện
1. Vào trang...
2. Click vào...
3. Thấy lỗi...

## Kết quả mong đợi
[Mô tả điều nên xảy ra]

## Thông tin môi trường
- Phiên bản CAMS: v1.0.x
- Trình duyệt / OS:
- Role người dùng:
- Screenshot / Sentry ID:
```

---

## 6.2 AI Model Retraining Pipeline (MLOps)

### Quy trình
```
1. Thu thập ảnh nhận diện sai
   (Giáo viên flag ô sai qua UI — nút "Báo lỗi nhận diện")
        ↓
2. Giáo viên gán nhãn lại
   (Label Studio hoặc UI annotation tích hợp trong CAMS)
        ↓
3. Data augmentation
   (flip ngang, rotate ±15°, brightness ±30%, contrast ±20%)
        ↓
4. Fine-tune YOLOv8 trên dataset mới
   (training script: backend/scripts/retrain_model.py)
        ↓
5. Evaluate model mới
   Target: piece accuracy >= 95%, board detection >= 99%
        ↓
6. Blue-green deployment
   Test model mới song song với model cũ (A/B test trên 10% traffic)
        ↓
7. Promote nếu accuracy tốt hơn
   Lưu version: models/chess_yolov8_v{n}.pt
   Cập nhật YOLO_MODEL_PATH trong .env
```

### Trigger retraining
- Tự động: mỗi quý (3 tháng)
- Manual: khi giáo viên report > 50 ảnh sai trong 1 tháng
- Post-release: sau mỗi lần thêm loại sách mới vào dataset

### Dataset Management
```
training_data/
├── boards/          # Ảnh bàn cờ đã rectify (640×640)
├── cells/           # Ảnh từng ô (80×80)
│   ├── K/           # White King
│   ├── Q/           # White Queen
│   ├── ...
│   └── empty/
├── annotations/     # YOLO format .txt labels
├── ground_truth/    # FEN strings đúng
└── rejected/        # Ảnh AI nhận diện sai (dùng để retrain)
```

---

## 6.3 Lộ trình Phát triển

| Phiên bản | Timeline | Tính năng chính |
|---|---|---|
| **v1.0 MVP** | Sprint 0–4 (tuần 1–12) | Auth (email + Google + Facebook), Lớp học, AI Scanner (3A→3D), Luyện tập, Chấm điểm AI & thủ công, ELO |
| **v1.5** | Sprint 5–6 (tuần 13–16) | Thanh toán Level 1 (VietQR + Admin confirm), Giải đấu online Swiss/Round Robin |
| **v2.0** | Sprint 7–8 (tuần 17–20) | Mobile App iOS/Android, Push Notifications, Offline cache |
| **v2.5** | Q1 2027 | Multi-center SaaS, Super Admin dashboard, Thanh toán Level 2 (Webhook) |
| **v3.0** | Q2 2027 | AI Coach (phân tích ván đấu cá nhân), Lichess/Chess.com sync, Thanh toán Level 3 (VNPay/MoMo đầy đủ) |
| **v3.5** | Q3 2027 | Video lesson management, Live streaming giải đấu |

---

## 6.4 Kế hoạch Backup & Recovery

### Backup
- PostgreSQL: `pg_dump -Fc` (custom format) hàng ngày lúc 2:00 AM → upload MinIO
  - Daily backup: retention 30 ngày
  - Weekly backup: retention 12 tuần
  - Monthly backup: retention 12 tháng (đáp ứng NFR-06: retention 1 năm)
- MinIO (PDF, ảnh): replicate sang S3/Cloudflare R2 hàng ngày
- AI Model files: lưu trên MinIO/S3 model registry
  - Git repo chỉ chứa `model_config.yaml` (version, path, sha256)
  - CI pipeline download model từ registry, verify checksum trước khi test
  - Không dùng Git LFS cho model files (gây chậm clone, tăng repo size)

### Recovery
- RTO (Recovery Time Objective): < 2 giờ
- RPO (Recovery Point Objective): < 24 giờ (1 ngày backup gần nhất)
- Quy trình restore:
  ```bash
  # Restore PostgreSQL
  pg_restore -d chess_academy backup_2026-09-20.dump
  
  # Restore MinIO
  mc mirror minio-backup/chess-academy minio/chess-academy
  ```

---

## 6.5 Dependency Updates

- Kiểm tra và cập nhật dependencies mỗi tháng
- Sử dụng Dependabot (GitHub) tự động tạo PR khi có bản vá bảo mật
- Không update minor/major version giữa sprint — chỉ update ở đầu sprint mới
- Test đầy đủ sau mỗi lần update

---

## 6.6 On-call & Incident Response

### Mức độ sự cố
| Level | Mô tả | Ví dụ | Response time |
|---|---|---|---|
| P0 - Critical | Hệ thống down hoàn toàn | Backend crash, DB unreachable | 15 phút |
| P1 - High | Tính năng quan trọng không hoạt động | Payment fail, AI scan không xử lý | 1 giờ |
| P2 - Medium | Ảnh hưởng một số users | Leaderboard không cập nhật | 4 giờ |
| P3 - Low | Vấn đề nhỏ, UI glitch | Typo, responsive trên màn nhỏ | Sprint tiếp theo |

### Incident Runbook
```
1. Phát hiện sự cố (Alert / User report)
2. Triage: xác định mức độ (P0/P1/P2/P3)
3. Notify team qua Slack #incidents
4. Investigate: check Sentry + Grafana + logs
5. Mitigate: rollback / hotfix / workaround
6. Resolve: deploy fix
7. Post-mortem: viết bài học trong 48h (nếu P0/P1)
```
