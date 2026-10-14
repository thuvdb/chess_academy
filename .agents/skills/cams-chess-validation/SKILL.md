---
name: cams-chess-validation
description: >
  Quy trình chuẩn validate và xử lý chess domain logic trong CAMS.
  Dùng khi cams-chess nhận task liên quan FEN/PGN validation, Stockfish analysis, puzzle generation, hoặc game logic.
  Ranh giới: nhận board-state thô từ AI-CV → validate/transform thành FEN/PGN hợp lệ.
---

# CAMS Chess Validation Skill

Quy trình step-by-step khi implement hoặc validate chess domain logic trong CAMS.

## Source of Truth

- `docs/02-architecture/AI_SCANNER_ARCHITECTURE.md` → FEN Validation Pipeline
- `docs/02-architecture/02_system_design.md` → Puzzle/Exercise tables
- `docs/01-sdlc/01_requirements.md` → Exercise & Training user stories

## Ranh giới AI-CV ↔ Chess

```
AI-CV (pixel → board-state thô)
  │
  ▼  Đầu ra có thể chưa hợp lệ theo luật cờ
  │
Chess (board-state → FEN/PGN hợp lệ)
  │
  ▼  Validate + Stockfish analysis + Puzzle generation
```

- AI-CV: nhận diện quân/bàn cờ từ ảnh, trả prediction per cell.
- Chess: nhận prediction → build FEN → validate legality → analysis.
- Lỗi kiểu "FEN sai sau khi scan" → cả AI-CV kiểm tra input VÀ Chess validate output.

## Quy trình Implementation

### Bước 1 — Xác định task type

1. **FEN Validation**: validate FEN string theo luật cờ.
2. **PGN Processing**: parse/validate PGN games.
3. **Puzzle Generation**: tạo puzzle từ position.
4. **Stockfish Analysis**: phân tích nước đi, tìm best move.
5. **Move Validation**: kiểm tra nước đi hợp lệ.

### Bước 2 — FEN Validation Rules

Dùng `python-chess` library:

```python
import chess

board = chess.Board(fen_string)
# Kiểm tra:
# 1. FEN syntax hợp lệ
# 2. Đúng 64 squares
# 3. Mỗi bên có đúng 1 King
# 4. Pawn không ở rank 1 hoặc rank 8
# 5. Tổng số quân hợp lệ (max 16 mỗi bên)
# 6. Side to move hợp lệ
# 7. Castling rights nhất quán với vị trí King/Rook
# 8. En passant square hợp lệ (nếu có)
```

### Bước 3 — Puzzle Generation

1. Từ FEN hợp lệ → phân tích bằng Stockfish.
2. Puzzle cần:
   - `fen`: starting position
   - `side_to_move`: color to play
   - `solution_moves`: danh sách nước đi đúng (UCI format)
   - `difficulty`: dựa trên Stockfish eval depth và centipawn difference
3. Puzzle có thể có nhiều solution lines — lưu tất cả.
4. Source: `pgn_import` | `fen_manual` | `ai_scanner`.

### Bước 4 — Stockfish Integration

1. Stockfish chạy như subprocess hoặc service riêng.
2. Cấu hình: depth, time limit, multipv (nhiều dòng phân tích).
3. **KHÔNG** lưu engine output như chân lý nếu chưa define rõ engine/depth/time.
4. Engine analysis là reference — teacher có thể override.

### Bước 5 — Move Notation

Phân biệt chính xác:

| Notation | Ví dụ | Dùng khi |
|---|---|---|
| **UCI** | `e2e4` | Giao tiếp với Stockfish |
| **SAN** | `e4`, `Nf3` | Hiển thị cho user |
| **FEN** | `rnbqkbnr/...` | Lưu position |
| **PGN** | `1. e4 e5 2. Nf3...` | Lưu game/puzzle |

### Bước 6 — Test

1. Test FEN validation với positions hợp lệ và invalid.
2. Test edge cases: en passant, castling, promotion, stalemate, checkmate.
3. Test puzzle generation output format.
4. Test Stockfish integration (connection, timeout, eval output).
5. Test move conversion (UCI ↔ SAN).

### Bước 7 — Báo cáo Result Contract

```
STATUS: DONE | FAILED | BLOCKED | PARTIAL
SCOPE: FEN validation / Puzzle generation / Stockfish analysis
CHANGES: Files cụ thể
TESTS: Validation tests, edge case chess rules
RISKS: Stockfish binary compatibility, performance
DEPENDENCIES: python-chess, Stockfish binary
BLOCKERS: ...
NEXT_ACTION: Integration test với AI-CV pipeline
```

## Quy tắc bổ sung

- Thuật toán tính điểm puzzle phải deterministic khi yêu cầu.
- ELO rating calculation phải theo công thức đã define trong requirements.
- Không implement anti-cheat ngoài phạm vi requirement đã được phê duyệt.
- FEN/PGN phải luôn được validate trước khi lưu vào DB.
