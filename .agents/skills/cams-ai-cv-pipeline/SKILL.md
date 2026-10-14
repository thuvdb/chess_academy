---
name: cams-ai-cv-pipeline
description: >
  Quy trình chuẩn implement/sửa AI Scanner pipeline trong CAMS.
  Dùng khi cams-ai-cv nhận task liên quan PDF extraction, board detection, rectification, piece classification, hoặc FEN building.
  Bắt buộc đọc AI_SCANNER_ARCHITECTURE.md trước khi implement.
---

# CAMS AI/CV Pipeline Skill

Quy trình step-by-step khi implement hoặc sửa đổi AI Scanner pipeline trong CAMS.

## Source of Truth

- `docs/02-architecture/AI_SCANNER_ARCHITECTURE.md` → **Bắt buộc đọc trước khi bắt đầu**
- `docs/02-architecture/02_system_design.md` → AI-related tables
- `docs/01-sdlc/03_sprint_plan.md` → Sprint 3A–3D (AI development sprints)

## Pipeline Architecture

```
PDF
 │
 ▼
[PDF Extractor]           → Images (PNG 300 DPI trên MinIO)
 │
 ▼
[Service A: Board Detector]    → Bounding Box + Confidence
 │                                (1 page có thể có N boards)
 ▼
[Service B: Board Rectifier]   → Normalized 640×640 + 64 Cells
 │
 ▼
[Service C: Piece Classifier]  → 13 classes + Confidence per cell
 │
 ▼
[FEN Builder]                  → FEN Candidate
 │
 ▼
[Validation Pipeline]          → Validated FEN hoặc Flag for Review
 │
 ▼
[Human Review UI]              → Teacher approve/correct
 │
 ▼
[Exercise Generator]           → Puzzle saved to CAMS DB
```

## Quy trình Implementation

### Bước 1 — Xác định stage

1. Đọc Context Packet → task ở stage nào trong pipeline?
2. Mỗi stage có input/output contract riêng — đọc trong `AI_SCANNER_ARCHITECTURE.md`.
3. Không implement nhiều stage cùng lúc nếu chưa test stage trước.

### Bước 2 — Input/Output Contract

Mỗi service phải tuân thủ contract:

**Service A (Board Detector):**
- Input: `page_image_url: str` (MinIO URL)
- Output: `boards: [{x, y, width, height, confidence, board_id}]`
- Có thể trả nhiều boards trên 1 trang

**Service B (Board Rectifier):**
- Input: `board_image_url + bounding_box`
- Output: `normalized_image_url + cells[64]: [{cell_id, image_url}]`

**Service C (Piece Classifier):**
- Input: `cells[64]: [{cell_id, image_url}]`
- Output: `predictions[64]: [{cell_id, piece_class, confidence}]`
- 13 classes: K, Q, R, B, N, P, k, q, r, b, n, p, empty

### Bước 3 — Confidence & Threshold

1. Mỗi prediction phải có confidence score.
2. Threshold mặc định: 0.85 cho auto-accept, < 0.85 → flag for review.
3. Threshold có thể configurable qua settings.
4. **KHÔNG** coi AI prediction là ground truth — luôn có human review path.

### Bước 4 — FEN Building & Validation

1. FEN Builder: chuyển 64 predictions → FEN string.
2. Validation pipeline:
   - Đúng số quân (max 1 King mỗi bên, max pieces theo rules).
   - Position hợp lệ (không pawn trên rank 1/8).
   - python-chess validate nếu có thể.
3. Nếu FEN invalid → flag for human review, không reject hoàn toàn.

### Bước 5 — Error Handling & Logging

1. Mỗi stage log: input, output, processing time, confidence.
2. Ảnh AI nhận diện sai → lưu vào dataset cho retraining.
3. Nếu service A không tìm thấy board → trả `board_found: false`, không crash.
4. Timeout cho AI processing — tách thành background task nếu nặng.

### Bước 6 — Storage

1. Input images (PDF pages) → MinIO.
2. Intermediate images (cropped boards, cells) → MinIO.
3. Scan results → PostgreSQL (`scan_jobs`, `scan_results` tables).
4. Không lưu model weights trong Git — dùng MinIO hoặc model registry.

### Bước 7 — Test

1. Unit test cho từng stage riêng biệt.
2. Test với ảnh tốt (high quality, clear board).
3. Test với ảnh xấu (blur, partial, rotated, no board).
4. Test confidence thresholds.
5. Test FEN validation edge cases.
6. Performance test (processing time per page).

### Bước 8 — Báo cáo Result Contract

```
STATUS: DONE | FAILED | BLOCKED | PARTIAL
SCOPE: Stage nào trong pipeline
CHANGES: Files cụ thể
TESTS: Stage tests, accuracy metrics, edge case results
RISKS: Model accuracy, processing time, memory usage
DEPENDENCIES: MinIO, PostgreSQL, model files
BLOCKERS: ...
NEXT_ACTION: Integration test toàn pipeline / cams-chess validate FEN
```

## Quy tắc bổ sung

- Sprint order: 3A (Board Detector) → 3B (Rectifier) → 3C (Classifier) → 3D (Integration).
- AI worker phải tách khỏi API request — dùng background task/Celery.
- Multi-board per page: DB schema phải support (1 page → N boards).
- Ranh giới AI-CV / Chess: AI-CV chịu trách nhiệm pixel → board-state thô. Chess chịu trách nhiệm board-state → FEN/PGN hợp lệ.
