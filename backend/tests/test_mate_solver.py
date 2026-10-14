"""
Tests cho mate_solver: tìm mate cưỡng bức, dựng cây biến thể, kiểm tra dãy UCI.
Run: $env:PYTHONIOENCODING='utf-8'; python tests/test_mate_solver.py
"""

import os
import sys
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import chess

from app.services.mate_solver import (
    _Budget,
    build_solution_tree,
    detect_mate_in,
    extract_main_line,
    grade_against_tree,
    mating_moves,
    solve_puzzle,
    verify_solution_line,
)

# Bài trong báo lỗi: mate-in-3, lời giải Qxf7+ Kh8, Qf8+ Rxf8, Rxf8#
FEN_MATE3 = "2r3k1/1p3ppp/p3p3/3pP2Q/2r5/P1Pq3P/1P2R2b/5R1K w - - 0 1"
LINE_MATE3 = ["h5f7", "g8h8", "f7f8", "c8f8", "f1f8"]

# Hai nước đều mate ngay: Ra8# và Rb8#
FEN_TWO_MATES = "6k1/5ppp/8/8/8/8/8/RR5K w - - 0 1"

# Không có mate cưỡng bức trong 3 nước
FEN_NO_MATE = "r3k2r/pb1p1ppp/1p2p3/2q5/2P1P3/2N2Q2/PP3PPP/R3K2R w KQkq - 0 1"


def test_detect_mate_in():
    print("=" * 60)
    print("TEST: detect_mate_in")
    print("=" * 60)

    t0 = time.perf_counter()
    k = detect_mate_in(chess.Board(FEN_MATE3))
    dt = time.perf_counter() - t0
    assert k == 3, f"FEN trong ảnh phải là mate in 3, nhận {k}"
    print(f"  [PASS] FEN bao loi -> mate in 3 ({dt:.2f}s)")

    k2 = detect_mate_in(chess.Board(FEN_TWO_MATES))
    assert k2 == 1, f"Phai la mate in 1, nhan {k2}"
    print("  [PASS] Hai nuoc mate ngay -> mate in 1")

    t0 = time.perf_counter()
    k3 = detect_mate_in(chess.Board(FEN_NO_MATE))
    dt = time.perf_counter() - t0
    assert k3 is None, f"Vi tri khong co mate phai tra None, nhan {k3}"
    print(f"  [PASS] Vi tri khong co mate -> None ({dt:.2f}s)")


def test_multiple_mating_moves():
    """Yêu cầu cốt lõi: một nút phải giữ MỌI nước Trắng ép được mate."""
    print("=" * 60)
    print("TEST: nhieu nuoc Trang cung mate trong mot nut")
    print("=" * 60)

    board = chess.Board(FEN_TWO_MATES)
    keys = mating_moves(board, 1)
    sans = sorted(board.san(m) for m in keys)
    assert len(keys) >= 2, f"Phai tim duoc >= 2 nuoc mate, nhan {sans}"
    assert "Ra8#" in sans and "Rb8#" in sans, f"Thieu nuoc mate: {sans}"
    print(f"  [PASS] Tim duoc {len(keys)} nuoc mate: {sans}")

    tree = build_solution_tree(board, 1)
    tree_ucis = sorted(pm["uci"] for pm in tree["player_moves"])
    assert len(tree_ucis) == len(keys), "Cay phai giu moi nuoc mate"
    print(f"  [PASS] Cay giu ca {len(tree_ucis)} nuoc: {tree_ucis}")


def test_tree_and_main_line():
    print("=" * 60)
    print("TEST: cay bien the + main line")
    print("=" * 60)

    board = chess.Board(FEN_MATE3)
    t0 = time.perf_counter()
    tree = build_solution_tree(board, 3)
    dt = time.perf_counter() - t0

    assert tree["mate_in"] == 3
    assert tree["player_color"] == "w"
    print(f"  [PASS] Dung cay xong ({dt:.2f}s), player_color=w mate_in=3")

    line = extract_main_line(tree)
    ucis = [m["uci"] for m in line]
    assert ucis == LINE_MATE3, f"Main line sai:\n  nhan   {ucis}\n  can    {LINE_MATE3}"
    print(f"  [PASS] Main line = {ucis}")

    # Tách bên: 3 nước Trắng xen 2 nước Đen
    white = [m for m in line if m["side"] == "w"]
    black = [m for m in line if m["side"] == "b"]
    assert len(white) == 3, f"Phai co 3 nuoc Trang, nhan {len(white)}"
    assert len(black) == 2, f"Phai co 2 nuoc Den, nhan {len(black)}"
    assert len(line) == 3 * 2 - 1, "Mate in 3 phai dai dung 5 ply"
    print(f"  [PASS] Trang: {[m['san'] for m in white]}")
    print(f"  [PASS] Den:   {[m['san'] for m in black]}")


def test_tree_covers_every_defence():
    """Mỗi nút phải giữ MỌI nước chống đỡ hợp lệ — không được bỏ sót biến thể."""
    print("=" * 60)
    print("TEST: cay phu het moi nuoc chong do cua Den")
    print("=" * 60)

    board = chess.Board(FEN_MATE3)
    tree = build_solution_tree(board, 3)
    checked = [0]

    def walk(node, bd):
        for pm in node.get("player_moves", []):
            move = chess.Move.from_uci(pm["uci"])
            assert move in bd.legal_moves, f"Nuoc {pm['uci']} khong hop le"
            bd.push(move)
            try:
                if pm["is_mate"]:
                    assert bd.is_checkmate(), f"{pm['san']} danh dau is_mate nhung khong phai mate"
                    assert not pm["replies"], "Nut mate khong duoc co nuoc tiep"
                else:
                    legal = sorted(m.uci() for m in bd.legal_moves)
                    got = sorted(r["uci"] for r in pm["replies"])
                    assert got == legal, (
                        f"Sau {pm['san']}: cay co {got} nhung nuoc hop le la {legal}"
                    )
                    checked[0] += 1
                    for r in pm["replies"]:
                        rm = chess.Move.from_uci(r["uci"])
                        bd.push(rm)
                        try:
                            walk(r["next"], bd)
                        finally:
                            bd.pop()
            finally:
                bd.pop()

    walk(tree, board.copy())
    assert checked[0] > 0, "Khong kiem tra duoc nut nao"
    print(f"  [PASS] Da doi chieu {checked[0]} nut voi board.legal_moves, khong bo sot")


def test_verify_accepts_correct_line():
    print("=" * 60)
    print("TEST: verify_solution_line nhan dung chuoi 5 token")
    print("=" * 60)

    res = verify_solution_line(FEN_MATE3, LINE_MATE3, declared_mate_in=3)
    assert res.ok, f"Chuoi dung phai duoc nhan, loi: {res.errors}"
    assert res.ends_in_mate, "Phai ket thuc bang checkmate"
    assert res.mate_in == 3
    assert res.expected_plies == 5
    assert len(res.player_moves) == 3, f"Phai co 3 nuoc nguoi choi, nhan {len(res.player_moves)}"
    assert len(res.opponent_moves) == 2, f"Phai co 2 nuoc doi phuong, nhan {len(res.opponent_moves)}"
    assert all(p.forces_mate for p in res.player_moves), "Moi nuoc Trang phai ep duoc mate"
    print(f"  [PASS] ok=True, mate_in=3, 3 nuoc Trang xen 2 nuoc Den")
    print(f"         Trang: {[p.san for p in res.player_moves]}")
    print(f"         Den:   {[p.san for p in res.opponent_moves]}")

    # side ghi theo luot thuc te, khong suy tu chi so
    sides = [p.side for p in res.plies]
    assert sides == ["w", "b", "w", "b", "w"], f"Sides sai: {sides}"
    print(f"  [PASS] side theo luot thuc te: {sides}")


def test_verify_rejects_mixed_sides():
    """Lớp bug đã báo: chuỗi chỉ có nước Trắng, lẫn bên, bị gắn nhãn sai."""
    print("=" * 60)
    print("TEST: tu choi chuoi lan nuoc hai ben")
    print("=" * 60)

    res = verify_solution_line(FEN_MATE3, ["h5f7", "f7f8", "f1f8"], declared_mate_in=3)
    assert not res.ok, "Chuoi lan ben phai bi tu choi"
    # Loi phai chi dung ply 2
    bad = [p for p in res.plies if p.error]
    assert bad and bad[0].index == 2, f"Loi phai o ply 2, nhan {[(p.index, p.error) for p in bad]}"
    assert "lượt" in bad[0].error, f"Loi phai noi ro sai luot, nhan: {bad[0].error}"
    print(f"  [PASS] Tu choi, loi dung o ply 2:")
    print(f"         {bad[0].error}")


def test_verify_rejects_incomplete_line():
    print("=" * 60)
    print("TEST: tu choi chuoi khong ket thuc bang mate")
    print("=" * 60)

    res = verify_solution_line(FEN_MATE3, ["h5f7", "g8h8"], declared_mate_in=3)
    assert not res.ok, "Chuoi chua mate phai bi tu choi"
    assert not res.ends_in_mate
    assert any("chiếu hết" in e for e in res.errors), f"Loi: {res.errors}"
    print(f"  [PASS] Tu choi: {[e for e in res.errors if 'chiếu hết' in e][0]}")


def test_verify_rejects_wrong_declared_count():
    print("=" * 60)
    print("TEST: tu choi khi so nuoc khai bao lech")
    print("=" * 60)

    res = verify_solution_line(FEN_MATE3, LINE_MATE3, declared_mate_in=2)
    assert not res.ok, "Khai bao mate in 2 tren vi tri mate in 3 phai bi tu choi"
    assert any("mate trong 2" in e and "mate trong 3" in e for e in res.errors), f"Loi: {res.errors}"
    print(f"  [PASS] {[e for e in res.errors if 'mate trong' in e][0]}")


def test_verify_rejects_non_forcing_move():
    print("=" * 60)
    print("TEST: tu choi nuoc Trang khong ep duoc mate")
    print("=" * 60)

    # a3a4 hop le nhung khong phai nuoc chia khoa
    res = verify_solution_line(FEN_MATE3, ["a3a4"], declared_mate_in=3)
    assert not res.ok
    assert res.plies[0].legal, "a3a4 van phai duoc coi la hop le"
    assert res.plies[0].forces_mate is False, "Nhung khong ep duoc mate"
    print(f"  [PASS] Hop le nhung bi tu choi: {res.plies[0].error}")


def test_solve_puzzle():
    print("=" * 60)
    print("TEST: solve_puzzle (API cho tang service)")
    print("=" * 60)

    out = solve_puzzle(FEN_MATE3, declared_mate_in=3)
    assert out.verified, f"Phai verify duoc, loi: {out.error}"
    assert out.mate_in == 3
    assert [m["uci"] for m in out.main_line] == LINE_MATE3
    assert out.tree is not None
    assert out.player_color == "w"
    print(f"  [PASS] verified=True mate_in=3 main_line={len(out.main_line)} ply")

    out2 = solve_puzzle(FEN_NO_MATE)
    assert not out2.verified, "Vi tri khong co mate khong duoc verified"
    assert out2.mate_in is None
    assert out2.error, "Phai co ly do"
    print(f"  [PASS] Vi tri khong co mate: verified=False, ly do='{out2.error}'")

    out3 = solve_puzzle("khong-phai-fen")
    assert not out3.verified and out3.error
    print(f"  [PASS] FEN rac: '{out3.error}'")


def test_grade_against_tree():
    print("=" * 60)
    print("TEST: grade_against_tree (chap nhan moi loi giai dung)")
    print("=" * 60)

    tree = build_solution_tree(chess.Board(FEN_MATE3), 3)
    solved, matched = grade_against_tree(tree, ["h5f7", "f7f8", "f1f8"])
    assert solved, f"3 nuoc Trang dung phai duoc cham la giai xong (matched={matched})"
    assert matched == 3
    print("  [PASS] 3 nuoc Trang dung -> solved")

    solved, matched = grade_against_tree(tree, ["a3a4"])
    assert not solved and matched == 0, "Nuoc sai phai bi tu choi ngay"
    print("  [PASS] Nuoc dau sai -> khong giai duoc, matched=0")

    solved, matched = grade_against_tree(tree, ["h5f7"])
    assert not solved and matched == 1, "Giai do dang chua tinh la xong"
    print("  [PASS] Giai do dang -> matched=1, chua solved")

    # Moi nuoc mate deu duoc nhan, khong chi main line
    two = build_solution_tree(chess.Board(FEN_TWO_MATES), 1)
    for pm in two["player_moves"]:
        ok, _ = grade_against_tree(two, [pm["uci"]])
        assert ok, f"Nuoc mate {pm['san']} phai duoc nhan"
    print(f"  [PASS] Ca {len(two['player_moves'])} nuoc mate deu duoc nhan")


def test_budget_guard():
    print("=" * 60)
    print("TEST: han muc tim kiem")
    print("=" * 60)

    from app.services.mate_solver import SolverBudgetExceeded

    try:
        detect_mate_in(chess.Board(FEN_NO_MATE), max_k=3, budget=_Budget(max_nodes=500))
        raise AssertionError("Han muc qua nho phai raise SolverBudgetExceeded")
    except SolverBudgetExceeded:
        print("  [PASS] Han muc node nho -> raise SolverBudgetExceeded")

    out = solve_puzzle(FEN_NO_MATE, node_budget=500)
    assert not out.verified and "hạn mức" in (out.error or "")
    print(f"  [PASS] solve_puzzle bat loi han muc: '{out.error}'")


if __name__ == "__main__":
    t_all = time.perf_counter()
    test_detect_mate_in()
    test_multiple_mating_moves()
    test_tree_and_main_line()
    test_tree_covers_every_defence()
    test_verify_accepts_correct_line()
    test_verify_rejects_mixed_sides()
    test_verify_rejects_incomplete_line()
    test_verify_rejects_wrong_declared_count()
    test_verify_rejects_non_forcing_move()
    test_solve_puzzle()
    test_grade_against_tree()
    test_budget_guard()
    print("=" * 60)
    print(f"ALL TESTS PASSED in {time.perf_counter() - t_all:.1f}s")
    print("=" * 60)
