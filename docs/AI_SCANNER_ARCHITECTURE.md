# AI_SCANNER_ARCHITECTURE.md — Kiến trúc AI Scanner Pipeline CAMS

> **CAMS — Chess Academy Management System**
> Tài liệu con của [SDLC.md](./SDLC.md)
> **Phiên bản:** 1.0 | **Ngày tạo:** 2026-09-20

---

## Tổng quan

AI Scanner là module nhận diện bàn cờ từ PDF sách cờ vua. Thay vì một pipeline monolithic, CAMS chia thành **3 service độc lập** để dễ test, debug, và cải thiện từng bước.

```
PDF
 │
 ▼
[PDF Extractor]        → Images (PNG 300 DPI)
 │
 ▼
[Service A: Board Detector]   → Bounding Box + Confidence
 │
 ▼
[Service B: Board Rectifier]  → Normalized 640×640 + 64 Cells
 │
 ▼
[Service C: Piece Classifier] → 13 classes + Confidence per cell
 │
 ▼
[FEN Builder]                 → FEN Candidate
 │
 ▼
[Validation Pipeline]         → Validated FEN hoặc Flag for Review
 │
 ▼
[Human Review UI]             → Teacher approve/correct
 │
 ▼
[Exercise Generator]          → Puzzle saved to CAMS DB
 │
 ▼
Học viên luyện tập
```

---

## Nguyên tắc thiết kế

1. **Test từng bước** — Sprint 3A → 3B → 3C → 3D, không rush vào pipeline hoàn chỉnh
2. **AI đề xuất → người kiểm tra → hệ thống mới lưu** — Human-in-the-loop bắt buộc
3. **Confidence score minh bạch** — Hiển thị độ tin cậy từng ô để giáo viên biết cần kiểm tra đâu
4. **Ảnh AI nhận diện sai = dataset retraining** — Thu thập để improve model

---

## Service A: Board Detector

### Nhiệm vụ
Nhận một trang ảnh PDF → phát hiện bàn cờ → trả về bounding box.

### Input
```python
page_image_url: str  # URL ảnh PNG 300 DPI trên MinIO
```

### Output
```json
{
  "board_found": true,
  "boards": [
    {
      "x": 125,
      "y": 340,
      "width": 820,
      "height": 820,
      "confidence": 0.97,
      "board_id": "page_05_board_01"
    },
    {
      "x": 950,
      "y": 340,
      "width": 780,
      "height": 780,
      "confidence": 0.89,
      "board_id": "page_05_board_02"
    }
  ]
}
```

### Thuật toán
```python
# board_detector.py
import cv2
import numpy as np

class BoardDetector:
    
    def detect(self, image_path: str) -> list[BoundingBox]:
        img = cv2.imread(image_path)
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        
        # 1. Edge detection
        edges = cv2.Canny(gray, 50, 150)
        
        # 2. Tìm contours
        contours, _ = cv2.findContours(
            edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE
        )
        
        boards = []
        for contour in contours:
            # 3. Approximation → polygon
            peri = cv2.arcLength(contour, True)
            approx = cv2.approxPolyDP(contour, 0.02 * peri, True)
            
            # 4. Chỉ lấy hình vuông / chữ nhật 4 góc, diện tích đủ lớn
            if len(approx) == 4 and cv2.contourArea(contour) > 10000:
                x, y, w, h = cv2.boundingRect(approx)
                aspect_ratio = w / h
                
                # Bàn cờ phải gần vuông (0.85 < ratio < 1.15)
                if 0.85 < aspect_ratio < 1.15:
                    confidence = self._calculate_confidence(img, x, y, w, h)
                    boards.append(BoundingBox(x=x, y=y, width=w, height=h, confidence=confidence))
        
        return boards
    
    def _calculate_confidence(self, img, x, y, w, h) -> float:
        """Tính confidence dựa trên đặc trưng của bàn cờ: pattern ô vuông xen kẽ."""
        roi = img[y:y+h, x:x+w]
        # Phân tích pattern ô cờ (chess grid pattern)
        # ...
        return confidence_score
```

### Thách thức cần xử lý
| Thách thức | Giải pháp |
|---|---|
| Bàn cờ nghiêng | Corner detection + Perspective Transform (Service B) |
| Ảnh mờ | Gaussian blur pre-processing + Adaptive threshold |
| Nhiều bàn cờ/trang | Detect tất cả, xử lý từng cái |
| Bàn cờ kích thước nhỏ | Điều chỉnh min area threshold |
| Nền bàn cờ gần giống nền trang | Tăng contrast trước khi detect |

---

## Service B: Board Rectifier

### Nhiệm vụ
Nhận bounding box → cắt ảnh bàn cờ → perspective transform → ảnh chuẩn 640×640 px → cắt 64 ô.

### Input
```python
page_image_url: str
bounding_box: BoundingBox
```

### Output
```python
normalized_board_url: str    # 640×640 PNG trên MinIO
cells: list[CellImage]       # 64 ô, mỗi ô 80×80 px
# cells[0] = a8, cells[7] = h8, ..., cells[56] = a1, cells[63] = h1
```

### Thuật toán
```python
# board_rectifier.py
class BoardRectifier:
    TARGET_SIZE = 640
    
    def rectify(self, image_path: str, bbox: BoundingBox) -> RectifiedBoard:
        img = cv2.imread(image_path)
        
        # 1. Crop theo bounding box
        board_crop = img[bbox.y:bbox.y+bbox.height, bbox.x:bbox.x+bbox.width]
        
        # 2. Corner detection (tìm 4 góc chính xác)
        corners = self._find_corners(board_crop)
        
        # 3. Perspective transform → ảnh vuông 640×640
        dst_pts = np.float32([
            [0, 0], [self.TARGET_SIZE, 0],
            [self.TARGET_SIZE, self.TARGET_SIZE], [0, self.TARGET_SIZE]
        ])
        M = cv2.getPerspectiveTransform(corners, dst_pts)
        normalized = cv2.warpPerspective(
            board_crop, M, (self.TARGET_SIZE, self.TARGET_SIZE)
        )
        
        # 4. Cắt 64 ô (8×8 grid)
        cell_size = self.TARGET_SIZE // 8  # = 80 px
        cells = []
        for row in range(8):      # row 0 = rank 8 (a8→h8)
            for col in range(8):  # col 0 = file a
                x = col * cell_size
                y = row * cell_size
                cell = normalized[y:y+cell_size, x:x+cell_size]
                square = self._index_to_square(row, col)  # "a8", "b8", ...
                cells.append(CellImage(square=square, image=cell))
        
        return RectifiedBoard(normalized=normalized, cells=cells)
    
    def _index_to_square(self, row: int, col: int) -> str:
        files = "abcdefgh"
        rank = 8 - row  # row 0 = rank 8, row 7 = rank 1
        return f"{files[col]}{rank}"
```

---

## Service C: Piece Classifier

### Nhiệm vụ
Nhận 64 ô ảnh → classify từng ô → 13 nhãn → build FEN.

### 13 nhãn
| Nhãn | Ý nghĩa |
|---|---|
| `K` | White King |
| `Q` | White Queen |
| `R` | White Rook |
| `B` | White Bishop |
| `N` | White Knight |
| `P` | White Pawn |
| `k` | Black King |
| `q` | Black Queen |
| `r` | Black Rook |
| `b` | Black Bishop |
| `n` | Black Knight |
| `p` | Black Pawn |
| `empty` | Ô trống |

### Thuật toán
```python
# piece_classifier.py
from ultralytics import YOLO
import numpy as np

class PieceClassifier:
    
    def __init__(self, model_path: str, confidence_threshold: float = 0.70):
        self.model = YOLO(model_path)
        self.threshold = confidence_threshold
    
    def classify_board(self, cells: list[CellImage]) -> ClassificationResult:
        """Classify tất cả 64 ô."""
        results = {}
        low_confidence_cells = []
        
        for cell in cells:
            piece, confidence = self._classify_cell(cell.image)
            results[cell.square] = {
                "piece": piece,
                "confidence": confidence
            }
            
            if confidence < self.threshold:
                low_confidence_cells.append({
                    "square": cell.square,
                    "piece": piece,
                    "confidence": confidence
                })
        
        fen = self._build_fen(results)
        
        return ClassificationResult(
            cell_results=results,
            fen_candidate=fen,
            low_confidence_cells=low_confidence_cells,
            needs_review=len(low_confidence_cells) > 0
        )
    
    def _classify_cell(self, cell_image: np.ndarray) -> tuple[str, float]:
        result = self.model(cell_image)
        top_class = result[0].probs.top1
        confidence = float(result[0].probs.top1conf)
        piece = self.model.names[top_class]
        return piece, confidence
    
    def _build_fen(self, results: dict) -> str:
        """Dịch ma trận 8×8 → Board FEN (chỉ board placement, CHƯA PHẢI full FEN)."""
        import chess
        board = chess.Board(None)  # Empty board
        
        for square_name, data in results.items():
            piece_char = data["piece"]
            if piece_char != "empty":
                square = chess.parse_square(square_name)
                piece = chess.Piece.from_symbol(piece_char)
                board.set_piece_at(square, piece)
        
        # CHỈ trả về board placement — full FEN sẽ được FENAssembler build
        # sau khi có side_to_move, castling, en_passant từ Human Review
        fen_board = board.board_fen()
        return fen_board
```

---

## FEN Assembler

> **Quan trọng:** AI nhìn hình bàn cờ **không thể tự biết** side to move, castling rights, en passant.
> Các thông tin này có thể nằm ở phần đề bài trong sách, hoặc cần giáo viên xác nhận.

Service C chỉ output `board_fen` (VD: `r1bqkb1r/pppp1ppp/...`). FENAssembler ghép thêm metadata → Full FEN.

```python
# fen_assembler.py
class FENAssembler:
    """Ghép board_fen + metadata thành Full FEN hợp lệ cho python-chess / Stockfish."""
    
    def assemble(
        self,
        board_fen: str,           # Từ Piece Classifier (Service C)
        side_to_move: str = "w",  # Từ Human Review UI hoặc context sách
        castling: str = "-",      # Default: không castling (an toàn cho puzzle)
        en_passant: str = "-",    # Default: không en passant
        halfmove: int = 0,
        fullmove: int = 1
    ) -> str:
        """Trả về Full FEN string."""
        return f"{board_fen} {side_to_move} {castling} {en_passant} {halfmove} {fullmove}"
    
    def assemble_from_scan_result(self, scan_result) -> str:
        """Ghép FEN từ scan_result record (sau khi teacher đã review)."""
        return self.assemble(
            board_fen=scan_result.fen_candidate,
            side_to_move=scan_result.side_to_move or "w",
            castling=scan_result.castling_rights or "-",
            en_passant=scan_result.en_passant or "-"
        )
```

### Pipeline flow sau khi sửa

```
Service C: Piece Classifier
     │
     ▼
 Board FEN (chỉ board placement)
     │
     + side_to_move  ← từ context sách / Human Review
     + castling      ← default "-" / Human Review
     + en_passant    ← default "-" / Human Review
     │
     ▼
 FEN Assembler → Full FEN
     │
     ▼
 Validation Pipeline
     │
     ▼
 Human Review → Approve → Exercise Generator
```

### Output ví dụ
```json
{
  "fen_candidate": "r1bqkb1r/pppp1ppp/2n2n2/4p3/2B1P3/5N2/PPPP1PPP/RNBQK2R",
  "cell_results": {
    "a8": {"piece": "r", "confidence": 0.99},
    "b8": {"piece": "n", "confidence": 0.97},
    "c8": {"piece": "b", "confidence": 0.96},
    "d8": {"piece": "q", "confidence": 0.63},
    "e8": {"piece": "k", "confidence": 0.98},
    "f5": {"piece": "P", "confidence": 0.58}
  },
  "low_confidence_cells": [
    {"square": "d8", "piece": "q", "confidence": 0.63},
    {"square": "f5", "piece": "P", "confidence": 0.58}
  ],
  "needs_review": true
}
```

---

## Validation Pipeline

```
Full FEN (từ FEN Assembler)
     │
     ▼
┌─────────────────────────────────┐
│ Step 1: FEN Syntax Validator    │
│ python-chess.Board(fen)         │
│ → Exception nếu FEN invalid     │
└──────────────┬──────────────────┘
               │ valid
               ▼
┌─────────────────────────────────┐
│ Step 2: Chess Position Validator│
│ - 1 king mỗi bên               │
│ - Không quá 8 chốt mỗi bên     │
│ - Không quá 1 queen nếu không   │
│   có phong cấp                  │
│ - Vua không đang bị chiếu chéo  │
└──────────────┬──────────────────┘
               │ valid
               ▼
┌─────────────────────────────────┐
│ Step 3a: Chess Legality Check   │
│ python-chess built-in:          │
│ → board.is_valid()              │
│ → list(board.legal_moves) > 0   │
│ → Không phải game over          │
└──────────────┬──────────────────┘
               │ valid
               ▼
┌─────────────────────────────────┐
│ Step 3b: Stockfish Analysis     │
│ (Optional — chạy khi approve    │
│  puzzle, không chạy khi validate│
│  FEN ban đầu vì tốn tài nguyên)│
│ engine.analyse(board, depth=15) │
│ → Eval có hợp lý không?        │
│ → Gợi ý best move cho solution │
└──────────────┬──────────────────┘
               │
               ▼
┌─────────────────────────────────┐
│ Step 4: Confidence Check        │
│ Có ô nào < threshold (70%)?     │
│ → Nếu có: flag kèm cảnh báo    │
└──────────────┬──────────────────┘
               │
               ▼
        REVIEW_PENDING
        (v1: luôn cần teacher review)
               │
               ▼
        Human Review UI
        (hiển thị cảnh báo ô
         confidence thấp nếu có)

  v2 (future): Auto-approve khi đủ điều kiện:
  - confidence >= 0.95 tất cả ô
  - validation pass hoàn toàn
  - source book đã trusted
  - Admin bật chế độ AUTO_APPROVE_TRUSTED
  → review_status = 'auto_approved'
```

```python
# fen_validator.py
import chess

class FENValidator:
    
    def validate(self, fen: str) -> ValidationResult:
        """Validate Full FEN (đã qua FENAssembler)."""
        # Step 1: Syntax
        try:
            board = chess.Board(fen)
        except ValueError as e:
            return ValidationResult(valid=False, error=f"Invalid FEN syntax: {e}")
        
        # Step 2: Chess position rules
        errors = []
        if len(board.pieces(chess.KING, chess.WHITE)) != 1:
            errors.append("White must have exactly 1 king")
        if len(board.pieces(chess.KING, chess.BLACK)) != 1:
            errors.append("Black must have exactly 1 king")
        if len(board.pieces(chess.PAWN, chess.WHITE)) > 8:
            errors.append("White cannot have more than 8 pawns")
        if len(board.pieces(chess.PAWN, chess.BLACK)) > 8:
            errors.append("Black cannot have more than 8 pawns")
        
        if errors:
            return ValidationResult(valid=False, error="; ".join(errors))
        
        # Step 3a: Chess legality check (python-chess built-in, KHÔNG phải Stockfish)
        if board.is_game_over():
            return ValidationResult(valid=False, error="Position is already game over")
        
        if not list(board.legal_moves):
            return ValidationResult(valid=False, error="No legal moves available")
        
        return ValidationResult(valid=True)
    
    def stockfish_analysis(self, fen: str, engine_path: str, depth: int = 15) -> AnalysisResult:
        """Step 3b: Stockfish analysis — chạy khi approve puzzle, không phải khi validate FEN."""
        import chess.engine
        board = chess.Board(fen)
        
        with chess.engine.SimpleEngine.popen_uci(engine_path) as engine:
            result = engine.analyse(board, chess.engine.Limit(depth=depth))
            best_move = result.get("pv", [None])[0]
            score = result.get("score")
            
            return AnalysisResult(
                best_move_uci=str(best_move) if best_move else None,
                best_move_san=board.san(best_move) if best_move else None,
                evaluation=str(score.relative) if score else None,
                depth=depth
            )
```

---

## Human Review UI

```
┌─────────────────────────────────────────────────────┐
│  📄 PDF: Tactics_Book_v2.pdf  │  Trang 12  │  Bàn 1  │
├─────────────────────────────────────────────────────┤
│                                                     │
│  [Hình ảnh bàn cờ từ sách]    [Bàn cờ CAMS hiển thị] │
│                                                     │
│  ⚠️  Có 2 ô cần kiểm tra:                           │
│  ┌──────────────────────────────────┐               │
│  │  d8   Hậu đen    63%  [Sửa ▼]   │               │
│  │  f5   Chốt trắng 58%  [Sửa ▼]   │               │
│  └──────────────────────────────────┘               │
│                                                     │
│  Board FEN: r1bqkb1r/pppp1ppp/2n2n2/...             │
│  [Sửa FEN trực tiếp]                                │
│                                                     │
│  ── Metadata (bắt buộc) ──────────────────────────  │
│  Lượt đi:     ○ Trắng  ● Đen                       │
│                                                     │
│  Castling:    ☑ K (White O-O)                       │
│               ☑ Q (White O-O-O)                     │
│               ☑ k (Black O-O)                       │
│               ☑ q (Black O-O-O)                     │
│  (Mặc định: tắt tất cả cho bài tactic)             │
│                                                     │
│  En passant:  [ none ▼ ]                            │
│                                                     │
│  ── Phân loại ──────────────────────────────────── │
│  Loại bài: [Tactic ▼]  Độ khó: [Intermediate ▼]   │
│                                                     │
│  Full FEN (tự sinh):                                │
│  r1bqkb1r/pppp1ppp/2n2n2/... w - - 0 1             │
│                                                     │
│  [❌ Từ chối]          [✓ Chấp nhận & Lưu bài tập]  │
└─────────────────────────────────────────────────────┘
```

---

## MLOps Pipeline — Cải thiện liên tục

### Thu thập dữ liệu lỗi
```python
# Trong Review UI: giáo viên bấm "Sửa" → tự động log
scan_error_log = {
    "scan_result_id": "...",
    "square": "d8",
    "ai_prediction": "q",
    "ai_confidence": 0.63,
    "correct_piece": "k",     # giáo viên sửa lại
    "image_url": "...",       # ô ảnh gốc
    "book_name": "Tactics v2",
    "page": 12
}
# Lưu vào bảng scan_error_logs → dùng để retrain
```

### Retraining Trigger
| Điều kiện | Hành động |
|---|---|
| > 50 lỗi/tháng | Tạo task retraining |
| Accuracy giảm < 90% trong tuần | Alert + retraining ngay |
| Mỗi quý | Scheduled retraining |

### Dataset Annotation
1. Export ảnh lỗi từ `scan_error_logs`
2. Giáo viên gán nhãn lại trong Label Studio (hoặc UI tích hợp)
3. Data augmentation: flip, rotate ±15°, brightness ±30%
4. Fine-tune YOLOv8 trên dataset mới
5. Evaluate → deploy nếu accuracy tốt hơn

---

## Test Dataset Requirements

Để AI Scanner hoạt động tốt, cần test với đa dạng loại ảnh:

| Loại | Ví dụ | Thách thức |
|---|---|---|
| Sách scan đen trắng | Sách cũ | Ảnh mờ, độ tương phản thấp |
| Sách màu chụp ảnh | Sách hiện đại | Background phức tạp |
| Nhiều bàn cờ/trang | Tạp chí cờ vua | Detect đúng tất cả |
| Bàn cờ nhỏ | Diagram phụ | Area filter cần điều chỉnh |
| Bàn cờ nghiêng | Ảnh chụp sách | Perspective transform |
| Quân cờ kiểu classic | Sách Liên Xô | Khác nhãn training |
| Quân cờ kiểu modern | Sách điện tử | Đơn giản hơn |
| Chú thích xung quanh | Hầu hết sách | Tránh nhầm chú thích thành bàn cờ |

### Minimum Test Dataset
- 200 ảnh trang PDF (từ >= 5 loại sách khác nhau)
- 5,000 ô (cells) đã gán nhãn
- Ground truth FEN cho 200 bàn cờ

---

## Performance Targets

| Service | Target | Measurement |
|---|---|---|
| Board Detection | >= 99% bàn cờ phát hiện đúng | True positive rate |
| Board Rectifier | Cell alignment error < 2px | Pixel accuracy |
| Piece Classifier | >= 95% accuracy per cell | Per-cell accuracy |
| Confidence Calibration | Confidence cao = accuracy cao | ECE (Expected Calibration Error) |
| Full Pipeline | < 30s / trang PDF | End-to-end latency |
| Review UI | Teacher review time < 2 phút/trang | User testing |
