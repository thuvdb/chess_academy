"""
Tests cho tầng service: chứng minh lời giải khi nhập bài và chấm điểm theo cây.
Không cần DB — chỉ dùng model instance rời và các hàm thuần.

Run: $env:PYTHONIOENCODING='utf-8'; python tests/test_puzzle_validation.py
"""

import os
import sys
import uuid

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.models.puzzle import Puzzle
from app.schemas.progress import StudentAttemptCreate
from app.services import mate_solver
from app.services.progress_service import _grade_attempt, split_sides
from app.services.puzzle_service import (
    _solve_sync,
    declared_mate_in,
    format_line_errors,
)

FEN_MATE3 = "2r3k1/1p3ppp/p3p3/3pP2Q/2r5/P1Pq3P/1P2R2b/5R1K w - - 0 1"
LINE_OK = ["h5f7", "g8h8", "f7f8", "c8f8", "f1f8"]
LINE_MIXED = ["h5f7", "f7f8", "f1f8"]          # lan nuoc hai ben — lop bug da bao
WHITE_MOVES = ["h5f7", "f7f8", "f1f8"]
FEN_NO_MATE = "r3k2r/pb1p1ppp/1p2p3/2q5/2P1P3/2N2Q2/PP3PPP/R3K2R w KQkq - 0 1"


def _puzzle(fen=FEN_MATE3, **kw):
    p = Puzzle(id=uuid.uuid4(), fen=fen, title="t", rating=1200)
    p.solutions = []
    p.solution_tree = None
    p.solution_verified = False
    p.mate_in = None
    p.puzzle_type = "tactic"
    for k, v in kw.items():
        setattr(p, k, v)
    return p


def test_declared_mate_in():
    print("=" * 60)
    print("TEST: declared_mate_in")
    print("=" * 60)
    assert declared_mate_in("mate_in_3") == 3
    assert declared_mate_in("MATE_IN_2") == 2
    assert declared_mate_in("tactic") is None
    assert declared_mate_in(None) is None
    print("  [PASS] Suy so nuoc mate tu nhan bai")


def test_solve_accepts_correct_line():
    print("=" * 60)
    print("TEST: nhan bai khi loi giai chung minh duoc")
    print("=" * 60)

    build = _solve_sync(FEN_MATE3, "mate_in_3", LINE_OK, deadline_s=30.0)
    assert build.verified, f"Phai verify duoc: {build.error}"
    assert build.mate_in == 3
    assert build.tree is not None
    assert [m["uci"] for m in build.main_line] == LINE_OK
    print(f"  [PASS] verified=True mate_in=3")

    sides = [m["side"] for m in build.main_line]
    assert sides == ["w", "b", "w", "b", "w"], f"Sides sai: {sides}"
    white = [m["san"] for m in build.main_line if m["side"] == "w"]
    black = [m["san"] for m in build.main_line if m["side"] == "b"]
    assert len(white) == 3 and len(black) == 2
    print(f"  [PASS] Main line tach ben: Trang={white} Den={black}")


def test_solve_reclassifies_mislabeled_puzzle():
    """Bài quét PDF bị gắn nhãn 'tactic' nhưng thực chất là mate-in-3."""
    print("=" * 60)
    print("TEST: tu phan loai lai bai gan nhan sai")
    print("=" * 60)

    build = _solve_sync(FEN_MATE3, "tactic", [], deadline_s=30.0)
    assert build.verified, f"Phai verify duoc: {build.error}"
    assert build.puzzle_type == "mate_in_3", f"Phai doi nhan, nhan {build.puzzle_type}"
    assert build.mate_in == 3
    print(f"  [PASS] 'tactic' -> '{build.puzzle_type}' (dung bai trong anh bao loi)")
    print(f"         Main line tu sinh: {[m['san'] for m in build.main_line]}")


def test_solve_rejects_mixed_sides():
    print("=" * 60)
    print("TEST: tu choi chuoi lan nuoc hai ben khi nhap bai")
    print("=" * 60)

    try:
        _solve_sync(FEN_MATE3, "mate_in_3", LINE_MIXED, deadline_s=30.0)
        raise AssertionError("Chuoi lan ben phai bi tu choi bang ValueError")
    except ValueError as exc:
        msg = str(exc)
        assert "Nước 2" in msg, f"Phai chi dung nuoc 2:\n{msg}"
        assert "lẫn nước của hai bên" in msg, f"Phai giai thich lop loi:\n{msg}"
        assert "3 nước của Trắng xen 2 nước của Đen" in msg, f"Phai neu dang dung:\n{msg}"
        print("  [PASS] ValueError voi thong bao cho giao vien:")
        for line in msg.splitlines():
            print(f"         {line}")


def test_solve_rejects_wrong_mate_count():
    print("=" * 60)
    print("TEST: tu choi khi so nuoc khai bao lech")
    print("=" * 60)

    try:
        _solve_sync(FEN_MATE3, "mate_in_2", LINE_OK, deadline_s=30.0)
        raise AssertionError("Khai bao mate_in_2 phai bi tu choi")
    except ValueError as exc:
        assert "mate trong 3" in str(exc)
        print(f"  [PASS] {[l for l in str(exc).splitlines() if 'mate trong' in l][0]}")


def test_solve_non_mate_is_unverified_not_rejected():
    print("=" * 60)
    print("TEST: bai khong phai mate -> luu nhung chua chung minh")
    print("=" * 60)

    build = _solve_sync(FEN_NO_MATE, "tactic", [], deadline_s=30.0)
    assert not build.verified, "Khong duoc danh dau da chung minh"
    assert build.mate_in is None
    assert build.error and "mate cưỡng bức" in build.error
    assert build.puzzle_type == "tactic", "Khong duoc doi nhan bai non-mate"
    print(f"  [PASS] verified=False, giu nhan 'tactic', ly do: '{build.error}'")


def test_format_line_errors():
    print("=" * 60)
    print("TEST: thong bao loi neu ro dang dung")
    print("=" * 60)

    check = mate_solver.verify_solution_line(FEN_MATE3, LINE_MIXED, declared_mate_in=3)
    msg = format_line_errors(check)
    assert msg.startswith("Lời giải không hợp lệ:")
    assert "tối đa 5 nước" in msg, f"Phai neu so nuoc toi da:\n{msg}"
    print("  [PASS] Thong bao co huong dan so nuoc dung (toi da 5)")


def test_split_sides():
    print("=" * 60)
    print("TEST: tach mot mang tron lan thanh hai danh sach")
    print("=" * 60)

    player, opponent = split_sides(FEN_MATE3, LINE_OK)
    assert player == WHITE_MOVES, f"Nuoc nguoi choi sai: {player}"
    assert opponent == ["g8h8", "c8f8"], f"Nuoc doi phuong sai: {opponent}"
    print(f"  [PASS] Nguoi choi: {player}")
    print(f"  [PASS] Doi phuong: {opponent}")

    # Dung ngay khi gap nuoc khong hop le, khong lech ben
    player2, _ = split_sides(FEN_MATE3, ["h5f7", "f7f8"])
    assert player2 == ["h5f7"], f"Phai dung o nuoc khong hop le: {player2}"
    print("  [PASS] Dung dung cho khi gap nuoc khong hop le")


def test_grade_attempt_uses_tree():
    print("=" * 60)
    print("TEST: cham diem theo cay bien the")
    print("=" * 60)

    build = _solve_sync(FEN_MATE3, "mate_in_3", LINE_OK, deadline_s=30.0)
    p = _puzzle(
        solution_tree=build.tree,
        solution_verified=True,
        mate_in=3,
        puzzle_type="mate_in_3",
    )

    # Client moi: gui rieng nuoc cua nguoi choi
    ok = _grade_attempt(p, StudentAttemptCreate(
        puzzle_id=p.id, moves_uci=LINE_OK, player_moves_uci=WHITE_MOVES,
    ))
    assert ok, "3 nuoc Trang dung phai duoc cham dat"
    print("  [PASS] player_moves_uci dung -> dat")

    # Client cu: chi gui mang tron lan, backend tu tach
    ok2 = _grade_attempt(p, StudentAttemptCreate(puzzle_id=p.id, moves_uci=LINE_OK))
    assert ok2, "Client cu chi gui moves_uci cung phai cham dung"
    print("  [PASS] Chi co moves_uci tron lan -> backend tu tach -> dat")

    # Nuoc sai
    bad = _grade_attempt(p, StudentAttemptCreate(
        puzzle_id=p.id, moves_uci=["a3a4"], player_moves_uci=["a3a4"],
    ))
    assert not bad, "Nuoc sai phai truot"
    print("  [PASS] Nuoc sai -> truot")

    # Giai do dang
    partial = _grade_attempt(p, StudentAttemptCreate(
        puzzle_id=p.id, moves_uci=["h5f7"], player_moves_uci=["h5f7"],
    ))
    assert not partial, "Giai do dang chua tinh la dat"
    print("  [PASS] Giai do dang -> chua dat")


def test_grade_mate_puzzle_never_falls_back_to_cp():
    """Bài mate chưa verify: lợi thế vật chất không được tính là lời giải."""
    print("=" * 60)
    print("TEST: bai mate khong roi vao nguong cp cua Stockfish")
    print("=" * 60)

    # mate_in da biet nhung chua co cay -> khong duoc goi Stockfish
    # (Stockfish khong cai local; neu bi goi, test se no ra loi import)
    p = _puzzle(mate_in=3, puzzle_type="mate_in_3")
    res = _grade_attempt(p, StudentAttemptCreate(
        puzzle_id=p.id, moves_uci=["a3a4"], player_moves_uci=["a3a4"],
    ))
    assert res is False, "Bai mate phai truot thay vi hoi engine ve loi the"
    print("  [PASS] Bai mate chua verify -> truot, khong dung nguong cp")

    # Nhung chieu het that thi van duoc nhan du chua verify
    p2 = _puzzle(mate_in=3, puzzle_type="mate_in_3")
    res2 = _grade_attempt(p2, StudentAttemptCreate(
        puzzle_id=p2.id, moves_uci=LINE_OK, player_moves_uci=WHITE_MOVES,
    ))
    assert res2 is True, "Chieu het that phai duoc nhan"
    print("  [PASS] Chieu het that -> dat (khong can engine)")


def test_tactic_with_legal_non_mate_line_is_accepted():
    """
    Bài chiến thuật thật (đòn fork thắng Hậu) — hợp lệ nhưng KHÔNG dẫn tới
    chiếu hết. Phải được lưu ở trạng thái chưa chứng minh, không bị từ chối.
    """
    print("=" * 60)
    print("TEST: bai chien thuat hop le nhung khong mate -> khong bi tu choi")
    print("=" * 60)

    fen = "2q3k1/8/8/5N2/6P1/7K/8/8 w - - 0 1"       # Ne7+ Kf8 Nxc8 an Hau
    line = ["f5e7", "g8f8", "e7c8"]

    build = _solve_sync(fen, "tactic", line, deadline_s=30.0)
    assert not build.verified, "Khong co mate thi khong duoc danh dau da chung minh"
    assert build.mate_in is None
    assert build.puzzle_type == "tactic", "Khong duoc doi nhan"
    assert build.error and "mate cưỡng bức" in build.error
    print(f"  [PASS] Luu duoc, verified=False, ly do: '{build.error}'")


def test_illegal_line_always_rejected_even_for_tactic():
    """Nước không hợp lệ bị chặn với MỌI loại bài, kể cả bài non-mate."""
    print("=" * 60)
    print("TEST: nuoc khong hop le bi chan ca voi bai chien thuat")
    print("=" * 60)

    fen = "2q3k1/8/8/5N2/6P1/7K/8/8 w - - 0 1"
    try:
        # f5e7 roi lai di tiep quan Trang -> sai luot
        _solve_sync(fen, "tactic", ["f5e7", "e7c8"], deadline_s=30.0)
        raise AssertionError("Chuoi sai luot phai bi tu choi du la bai tactic")
    except ValueError as exc:
        assert "Nước 2" in str(exc), f"Phai chi dung nuoc 2:\n{exc}"
        print(f"  [PASS] {[l for l in str(exc).splitlines() if 'Nước 2' in l][0]}")


def test_mate_label_on_non_mate_position_rejected():
    """Gắn nhãn mate nhưng vị trí không có mate -> chặn."""
    print("=" * 60)
    print("TEST: gan nhan mate cho vi tri khong co mate -> chan")
    print("=" * 60)

    try:
        _solve_sync(FEN_NO_MATE, "mate_in_2", [], deadline_s=30.0)
        raise AssertionError("Phai bi tu choi")
    except ValueError as exc:
        assert "không có" in str(exc) and "mate cưỡng bức" in str(exc)
        print(f"  [PASS] {exc}")


def test_deep_mate_is_unverified_not_rejected():
    """
    Mate-in-4 vượt hạn mức tìm kiếm nhanh của đường request: phải lưu ở trạng
    thái chưa chứng minh kèm hướng dẫn, KHÔNG được từ chối bài đúng.
    """
    print("=" * 60)
    print("TEST: mate sau vuot han muc -> chua chung minh, khong tu choi")
    print("=" * 60)

    fen = "2k3r1/pp3R2/n6b/3QP3/3P3p/P5qP/1rP2RP1/7K w - - 0 1"   # mate in 4
    from unittest.mock import patch
    with patch("app.services.mate_solver._detect_mate_with_engine", return_value=None):
        build = _solve_sync(fen, "tactic", [], deadline_s=1.0, max_k=4)
        assert not build.verified
        assert build.error and "hạn mức" in build.error
        assert "revalidate_puzzles" in build.error, "Phai chi cho user cach xac minh nen"
        print(f"  [PASS] {build.error}")

    # Cho đủ thời gian thì chứng minh được
    deep = _solve_sync(fen, "tactic", [], deadline_s=180.0, max_k=4)
    assert deep.verified, f"Voi deadline rong phai verify duoc: {deep.error}"
    assert deep.mate_in == 4
    assert deep.puzzle_type == "mate_in_4", f"Phai phan loai lai: {deep.puzzle_type}"
    assert len(deep.main_line) == 7, f"Mate in 4 phai dai 7 ply, nhan {len(deep.main_line)}"
    print(f"  [PASS] Deadline rong -> mate_in=4, tactic -> mate_in_4, 7 ply")
    print(f"         {[m['san'] for m in deep.main_line]}")


def test_form_check_agrees_with_save():
    """
    Endpoint validate-solution (form) và _solve_sync (lúc lưu) phải cùng một
    luật. Lệch nhau thì form báo đỏ mà backend vẫn nhận, hoặc ngược lại.
    """
    print("=" * 60)
    print("TEST: form check va luc luu dong nhat luat")
    print("=" * 60)

    import asyncio
    from app.services.puzzle_service import verify_line

    cases = [
        # (nhan, fen, dãy nước, ky vong form.ok, ky vong luu duoc)
        ("tactic", "2q3k1/8/8/5N2/6P1/7K/8/8 w - - 0 1", ["f5e7", "g8f8", "e7c8"], True, True),
        ("mate_in_3", FEN_MATE3, LINE_OK, True, True),
        ("mate_in_3", FEN_MATE3, LINE_MIXED, False, False),
        ("tactic", FEN_MATE3, LINE_MIXED, False, False),
    ]

    for ptype, fen, line, want_form_ok, want_saveable in cases:
        form = asyncio.run(verify_line(fen=fen, moves_uci=line, puzzle_type=ptype))
        try:
            _solve_sync(fen, ptype, line, deadline_s=30.0)
            saveable = True
        except ValueError:
            saveable = False

        assert form.ok == want_form_ok, (
            f"{ptype} {line}: form.ok={form.ok}, mong doi {want_form_ok} "
            f"(loi: {form.errors})"
        )
        assert saveable == want_saveable, (
            f"{ptype} {line}: luu duoc={saveable}, mong doi {want_saveable}"
        )
        assert form.ok == saveable, (
            f"LECH LUAT: {ptype} {line} -> form.ok={form.ok} nhung luu duoc={saveable}"
        )
        print(f"  [PASS] {ptype:10s} {str(line):38s} form.ok={form.ok} luu={saveable}")


if __name__ == "__main__":
    import time
    t0 = time.perf_counter()
    test_declared_mate_in()
    test_solve_accepts_correct_line()
    test_solve_reclassifies_mislabeled_puzzle()
    test_solve_rejects_mixed_sides()
    test_solve_rejects_wrong_mate_count()
    test_solve_non_mate_is_unverified_not_rejected()
    test_tactic_with_legal_non_mate_line_is_accepted()
    test_illegal_line_always_rejected_even_for_tactic()
    test_mate_label_on_non_mate_position_rejected()
    test_deep_mate_is_unverified_not_rejected()
    test_form_check_agrees_with_save()
    test_format_line_errors()
    test_split_sides()
    test_grade_attempt_uses_tree()
    test_grade_mate_puzzle_never_falls_back_to_cp()
    print("=" * 60)
    print(f"ALL TESTS PASSED in {time.perf_counter() - t0:.1f}s")
    print("=" * 60)
