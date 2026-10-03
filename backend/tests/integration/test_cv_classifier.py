"""Integration test: classify_cells (YOLO whole-board) + build_fen_from_grid trên board thật."""
import cv2
import chess
from app.services.board_rectifier import _slice_cells
from app.services.piece_classifier import classify_cells, _get_model
from app.services.fen_builder import build_fen_from_grid

JID = "68ba94bd-b14b-40a1-8911-840ff1246794"
EXPECTED = {
    # page040_board00 đọc bằng mắt từ ảnh diagram
    "page040_board00": "4R3/kp4p1/P1p5/5Q2/2q2r2/P7/7P/7K",
}

assert _get_model() is not None, "YOLO model KHÔNG load được"
fails = 0
for name in ("page040_board00", "page003_board00", "page010_board02", "page060_board03"):
    img = cv2.imread(f"/app/storage/scans/{JID}/boards/{name}_rectified.png")
    cells = classify_cells(_slice_cells(img))
    data = build_fen_from_grid(cells)
    fen = data.get("fen_candidate")
    print(name, fen, data.get("validation"), data.get("errors"))
    placement = fen.split()[0] if fen else ""
    try:
        chess.Board(fen + " w - - 0 1" if " " not in fen else fen)
    except Exception as e:
        print("  invalid FEN:", e)
    if name in EXPECTED and placement != EXPECTED[name]:
        print("  FAIL expected", EXPECTED[name])
        fails += 1
print("FAILS:", fails)
raise SystemExit(1 if fails else 0)
