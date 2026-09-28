# Giai đoạn 5: Triển khai & DevOps (Deployment & DevOps)

> **CAMS — Chess Academy Management System**
> Tài liệu con của [SDLC.md](./SDLC.md)

---

## 5.1 Docker Compose (Development)

```yaml
# docker-compose.yml
version: "3.9"

services:
  backend:
    build: ./backend
    ports: ["8000:8000"]
    depends_on: [postgres, redis, minio]
    env_file: .env
    volumes:
      - ./backend/models:/app/models
    command: uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

  frontend:
    build: ./frontend
    ports: ["5173:5173"]
    command: npm run dev

  postgres:
    image: postgres:16-alpine
    volumes:
      - pgdata:/var/lib/postgresql/data
    environment:
      POSTGRES_DB: chess_academy
      POSTGRES_USER: postgres
      POSTGRES_PASSWORD: ${DB_PASSWORD}
    ports: ["5432:5432"]

  redis:
    image: redis:7-alpine
    command: redis-server --appendonly yes
    ports: ["6379:6379"]

  minio:
    image: minio/minio
    ports: ["9000:9000", "9001:9001"]
    command: server /data --console-address ":9001"
    environment:
      MINIO_ROOT_USER: ${MINIO_ACCESS_KEY}
      MINIO_ROOT_PASSWORD: ${MINIO_SECRET_KEY}
    volumes:
      - miniodata:/data

  # Worker cho background tasks (AI scan, email, cron)
  worker:
    build: ./backend
    depends_on: [postgres, redis]
    env_file: .env
    command: celery -A app.worker worker --loglevel=info

volumes:
  pgdata:
  miniodata:
```

---

## 5.2 CI/CD Pipeline (GitHub Actions)

```yaml
# .github/workflows/ci.yml
name: CI/CD Pipeline

on:
  push:
    branches: [main, develop]
  pull_request:
    branches: [main]

jobs:
  test-backend:
    runs-on: ubuntu-latest
    services:
      postgres:
        image: postgres:16
        env:
          POSTGRES_PASSWORD: test
          POSTGRES_DB: test_chess
        ports: ["5432:5432"]
      redis:
        image: redis:7
        ports: ["6379:6379"]
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.11"
      - run: pip install -r backend/requirements.txt
      - run: pytest backend/tests/unit/ backend/tests/integration/ \
               --cov=app --cov-fail-under=80 -v

  test-frontend:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with:
          node-version: "20"
      - run: cd frontend && npm ci && npm run build
      - run: npx playwright install --with-deps
      - run: npx playwright test

  test-ai-accuracy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.11"
      - run: pip install -r backend/requirements.txt
      - run: python backend/tests/test_piece_classifier.py \
               --dataset ./test_data/cells/ \
               --min-accuracy 0.95

  deploy-staging:
    needs: [test-backend, test-frontend]
    if: github.ref == 'refs/heads/develop'
    runs-on: ubuntu-latest
    steps:
      - name: Build & push Docker image
        run: |
          docker build -t registry/chess-academy:staging .
          docker push registry/chess-academy:staging
      - name: Deploy to staging via SSH
        run: ssh deploy@staging "docker-compose pull && docker-compose up -d"

  deploy-production:
    needs: [test-backend, test-frontend, test-ai-accuracy]
    if: github.ref == 'refs/heads/main'
    environment: production   # requires manual approval in GitHub
    runs-on: ubuntu-latest
    steps:
      - name: Build & push Docker image
        run: |
          docker build -t registry/chess-academy:latest .
          docker push registry/chess-academy:latest
      - name: Deploy to production (zero-downtime)
        run: |
          ssh deploy@prod "docker-compose pull && \
          docker-compose up -d --scale backend=2 && \
          sleep 10 && \
          docker-compose up -d"
```

---

## 5.3 Environment Variables

```env
# .env.example — Copy sang .env và điền giá trị thực

# ─── Database ────────────────────────────────────────────
DATABASE_URL=postgresql+asyncpg://user:pass@localhost/chess_academy
REDIS_URL=redis://localhost:6379

# ─── JWT ─────────────────────────────────────────────────
SECRET_KEY=your-super-secret-key-min-32-chars
ACCESS_TOKEN_EXPIRE_MINUTES=30
REFRESH_TOKEN_EXPIRE_DAYS=7

# ─── Storage (MinIO / AWS S3) ─────────────────────────────
MINIO_ENDPOINT=localhost:9000
MINIO_ACCESS_KEY=minioadmin
MINIO_SECRET_KEY=minioadmin
MINIO_BUCKET=chess-academy
MINIO_USE_SSL=false

# ─── OAuth ───────────────────────────────────────────────
GOOGLE_CLIENT_ID=your_google_client_id
GOOGLE_CLIENT_SECRET=your_google_client_secret
FACEBOOK_APP_ID=your_facebook_app_id
FACEBOOK_APP_SECRET=your_facebook_app_secret

# ─── Payment — VNPay ──────────────────────────────────────
VNPAY_TMN_CODE=your_tmn_code
VNPAY_HASH_SECRET=your_hash_secret
VNPAY_URL=https://sandbox.vnpayment.vn/paymentv2/vpcpay.html
VNPAY_RETURN_URL=https://yourdomain.vn/payment/vnpay-return
VNPAY_IPN_URL=https://yourdomain.vn/api/payments/webhook/vnpay

# ─── Payment — MoMo ───────────────────────────────────────
MOMO_PARTNER_CODE=your_partner_code
MOMO_ACCESS_KEY=your_access_key
MOMO_SECRET_KEY=your_secret_key
MOMO_ENDPOINT=https://test-payment.momo.vn/v2/gateway/api/create
MOMO_REDIRECT_URL=https://yourdomain.vn/payment/momo-return
MOMO_IPN_URL=https://yourdomain.vn/api/payments/webhook/momo

# ─── Payment — VietQR (Level 1) ───────────────────────────
VIETQR_BANK_ID=MB         # Mã ngân hàng
VIETQR_ACCOUNT_NO=your_account_number
VIETQR_ACCOUNT_NAME=TEN TRUNG TAM CO VUA

# ─── Firebase (FCM) ──────────────────────────────────────
FIREBASE_PROJECT_ID=your_project_id
FIREBASE_PRIVATE_KEY="-----BEGIN PRIVATE KEY-----\n..."
FIREBASE_CLIENT_EMAIL=firebase-adminsdk@project.iam.gserviceaccount.com

# ─── Email ────────────────────────────────────────────────
SENDGRID_API_KEY=SG.your_sendgrid_key
FROM_EMAIL=noreply@chessacademy.vn
FROM_NAME=Chess Academy

# ─── AI & Chess Engine ───────────────────────────────────
STOCKFISH_PATH=/usr/local/bin/stockfish
YOLO_MODEL_PATH=models/chess_yolov8.pt
AI_CONFIDENCE_THRESHOLD=0.70    # Ngưỡng cảnh báo ô nhận diện thấp

# ─── App ─────────────────────────────────────────────────
ENVIRONMENT=development         # development | staging | production
FRONTEND_URL=http://localhost:5173
```

---

## 5.4 Production Checklist

### Security
- [ ] SSL/TLS certificate (Let's Encrypt via Certbot + auto-renewal)
- [ ] Nginx reverse proxy: rate limiting (100 req/min/IP), gzip, security headers (HSTS, CSP, X-Frame-Options)
- [ ] Payment webhook endpoints: whitelist IP của VNPay/MoMo
- [ ] Secret rotation: JWT secret, payment keys lưu trong Vault hoặc GitHub Secrets
- [ ] PDPA compliance: `DELETE /api/users/me` (xóa data cá nhân), cookie consent banner

### Database
- [ ] PgBouncer (connection pooling)
- [ ] Redis Sentinel hoặc Redis Cluster (high availability)
- [ ] Automated backup: `pg_dump` hàng ngày → MinIO, retention 30 ngày
- [ ] Composite indexes:
  ```sql
  CREATE INDEX idx_student_progress_student ON student_progress(student_id, status);
  CREATE INDEX idx_assignments_class ON assignments(class_id, due_date);
  CREATE INDEX idx_puzzles_center ON puzzles(center_id, difficulty, exercise_type);
  CREATE INDEX idx_invoices_status ON invoices(center_id, status, due_date);
  CREATE INDEX idx_notifications_user ON notifications(user_id, is_read, created_at);
  ```

### Monitoring & Observability
- [ ] Prometheus + Grafana (latency, error rate, ELO distribution, queue depth)
- [ ] Sentry (error tracking: backend + frontend + mobile)
- [ ] Loki + Grafana (log aggregation)
- [ ] Uptime monitoring (UptimeRobot hoặc Grafana Cloud)
- [ ] Alert rules: error rate > 1%, P95 > 1s, payment webhook failure

### Deployment
- [ ] Zero-downtime deployment (rolling update hoặc blue-green)
- [ ] Health check endpoint: `GET /health` → `{"status":"ok","db":"ok","redis":"ok"}`
- [ ] Graceful shutdown: SIGTERM → drain connections → stop
