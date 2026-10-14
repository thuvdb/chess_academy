"""
Mate Solver — tìm và chứng minh mate cưỡng bức bằng python-chess thuần.

Không phụ thuộc engine ngoài: Stockfish chỉ có trong container (xem Dockerfile)
nên mọi tính năng dựa vào nó im lặng vô hiệu khi chạy local. Phần mate là bài
toán hữu hạn và cưỡng bức, giải chính xác được bằng tìm kiếm đầy đủ.

Khác biệt cốt lõi so với danh sách nước phẳng cũ: lời giải được biểu diễn thành
CÂY BIẾN THỂ — mỗi nút của bên tấn công giữ MỌI nước ép được mate, và mỗi nước
đó giữ MỌI nước chống đỡ hợp lệ của bên phòng ngự, mỗi nước chống đỡ lại có
nhánh tiếp riêng.
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone

import chess

logger = logging.getLogger(__name__)

# Mate-in-4 trở lên tốn thời gian theo cấp số nhân; giới hạn mặc định cho
# đường request là 3, script backfill có thể nâng lên qua tham số.
MAX_MATE_IN = 3
HARD_MAX_MATE_IN = 4

DEFAULT_NODE_BUDGET = 400_000
DEFAULT_DEADLINE_S = 8.0
MAX_TREE_NODES = 20_000

GENERATED_BY = "mate_solver/python-chess"

_COLOR_NAME_VI = {"w": "Trắng", "b": "Đen"}


class SolverBudgetExceeded(Exception):
    """Tìm kiếm vượt quá hạn mức node hoặc thời gian cho phép."""


class _Budget:
    """Hạn mức tìm kiếm: số node (tất định) + deadline (bảo vệ request)."""

    __slots__ = ("remaining", "deadline", "_checks")

    def __init__(self, max_nodes: int = DEFAULT_NODE_BUDGET, deadline_s: float | None = None):
        self.remaining = max_nodes
        self.deadline = (time.monotonic() + deadline_s) if deadline_s else None
        self._checks = 0

    def spend(self) -> None:
        self.remaining -= 1
        if self.remaining <= 0:
            raise SolverBudgetExceeded("Vượt hạn mức node tìm kiếm")
        if self.deadline is not None:
            self._checks += 1
            if self._checks >= 2048:
                self._checks = 0
                if time.monotonic() > self.deadline:
                    raise SolverBudgetExceeded("Vượt hạn mức thời gian tìm kiếm")


# ── Sắp xếp nước để fail-fast ────────────────────────────────

def _order_attacker(board: chess.Board) -> list[chess.Move]:
    """Bên tấn công: thử nước chiếu rồi nước ăn quân trước — mate hay nằm ở đó."""
    moves = list(board.legal_moves)
    moves.sort(key=lambda m: (
        0 if board.gives_check(m) else 1,
        0 if board.is_capture(m) else 1,
        m.uci(),
    ))
    return moves


def _order_defender(board: chess.Board) -> list[chess.Move]:
    """Bên phòng ngự: thử nước Vua và nước ăn quân trước — thoát hay nằm ở đó."""
    moves = list(board.legal_moves)

    def key(m: chess.Move):
        piece = board.piece_at(m.from_square)
        return (
            0 if piece is not None and piece.piece_type == chess.KING else 1,
            0 if board.is_capture(m) else 1,
            m.uci(),
        )

    moves.sort(key=key)
    return moves


# ── Tìm kiếm mate ────────────────────────────────────────────

def attacker_can_mate(board: chess.Board, k: int, budget: _Budget) -> bool:
    """Bên đang đi có ép được mate trong <= k nước hay không."""
    if k <= 0:
        return False
    budget.spend()
    for move in _order_attacker(board):
        board.push(move)
        try:
            if board.is_checkmate():
                return True
            if k >= 2 and defender_is_lost(board, k - 1, budget):
                return True
        finally:
            board.pop()
    return False


def defender_is_lost(board: chess.Board, k: int, budget: _Budget) -> bool:
    """
    Bên đang đi (phòng ngự) bị mate trong <= k nước dù đi bất cứ nước nào.

    Hết nước đi nghĩa là hoà cờ (bí) — người gọi đã loại trường hợp checkmate
    trước đó — nên không tính là thua.
    """
    budget.spend()
    has_move = False
    for move in _order_defender(board):
        has_move = True
        board.push(move)
        try:
            if not attacker_can_mate(board, k, budget):
                return False
        finally:
            board.pop()
    return has_move


def mating_moves(
    board: chess.Board,
    k: int,
    budget: _Budget | None = None,
) -> list[chess.Move]:
    """MỌI nước của bên đang đi ép được mate trong <= k nước."""
    if k <= 0 or board.is_game_over():
        return []
    budget = budget or _Budget()
    found: list[chess.Move] = []
    for move in _order_attacker(board):
        board.push(move)
        try:
            if board.is_checkmate():
                found.append(move)
                continue
            if k >= 2 and defender_is_lost(board, k - 1, budget):
                found.append(move)
        finally:
            board.pop()
    return found


def detect_mate_in(
    board: chess.Board,
    max_k: int = MAX_MATE_IN,
    budget: _Budget | None = None,
) -> int | None:
    """
    Khoảng cách mate cưỡng bức NHỎ NHẤT cho bên đang đi, hoặc None nếu không có
    trong phạm vi max_k. Tăng dần độ sâu nên mate ngắn được phát hiện trước.

    Raises SolverBudgetExceeded khi không kết luận được trong hạn mức — người
    gọi phải phân biệt "không có mate" với "chưa xác định được".
    """
    if board.is_game_over():
        return None
    budget = budget or _Budget()
    for k in range(1, min(max_k, HARD_MAX_MATE_IN) + 1):
        if mating_moves(board, k, budget):
            return k
    return None


def _detect_mate_with_engine(board: chess.Board, max_k: int) -> int | None:
    """Tăng tốc tìm mate bằng Stockfish nếu có sẵn trong môi trường."""
    if board.is_game_over():
        return None
    try:
        from app.services.stockfish_service import get_stockfish
        sf = get_stockfish(depth=14)
        sf.set_fen_position(board.fen())
        eval_res = sf.get_evaluation()
        if eval_res.get("type") == "mate":
            val = eval_res.get("value")
            effective_max = max(max_k, HARD_MAX_MATE_IN)
            if val is not None and 1 <= val <= effective_max:
                return val
    except Exception:
        pass
    return None


def _get_engine_mating_moves(board: chess.Board, remaining: int) -> list[chess.Move] | None:
    """Lấy danh sách các nước đi ép được mate trong <= remaining nước bằng Stockfish."""
    if board.is_game_over() or remaining <= 0:
        return None
    try:
        from app.services.stockfish_service import get_stockfish
        sf = get_stockfish(depth=13)
        sf.set_fen_position(board.fen())
        eval_res = sf.get_evaluation()
        if eval_res.get("type") != "mate":
            return None
        val = eval_res.get("value")
        if val is None or val > remaining:
            return None

        top_moves = sf.get_top_moves(5)
        mating: list[chess.Move] = []
        for item in top_moves:
            m_val = item.get("Mate")
            if m_val is not None and 1 <= m_val <= remaining:
                m_uci = item.get("Move")
                if m_uci:
                    try:
                        move_obj = chess.Move.from_uci(m_uci)
                        if move_obj in board.legal_moves:
                            mating.append(move_obj)
                    except ValueError:
                        pass
        return mating if mating else None
    except Exception:
        return None


# ── Dựng cây biến thể ────────────────────────────────────────

def _build_node(
    board: chess.Board,
    remaining: int,
    budget: _Budget,
    counter: list[int],
    cap: int,
) -> dict:
    """Nút của bên TẤN CÔNG, cần mate trong <= remaining nước."""
    node: dict = {"player_moves": []}
    engine_moves = _get_engine_mating_moves(board, remaining)
    candidate_moves = engine_moves if engine_moves is not None else mating_moves(board, remaining, budget)
    for key_move in candidate_moves:
        san = board.san(key_move)
        board.push(key_move)
        try:
            is_mate = board.is_checkmate()
            replies = []
            if not is_mate:
                # MỌI nước chống đỡ hợp lệ, mỗi nước một nhánh riêng
                for reply in sorted(board.legal_moves, key=lambda m: m.uci()):
                    reply_san = board.san(reply)
                    board.push(reply)
                    try:
                        sub = _build_node(board, remaining - 1, budget, counter, cap)
                    finally:
                        board.pop()
                    replies.append({"uci": reply.uci(), "san": reply_san, "next": sub})
            node["player_moves"].append({
                "uci": key_move.uci(),
                "san": san,
                "is_mate": is_mate,
                "replies": replies,
            })
        finally:
            board.pop()

        counter[0] += 1
        if counter[0] > cap:
            raise SolverBudgetExceeded(f"Cây biến thể vượt {cap} nút")
    return node


def _mark_main_replies(node: dict) -> None:
    """
    Đánh dấu nhánh chống đỡ cầm cự lâu nhất ở mỗi nút là `is_main`.

    Client dùng cờ này để chọn nước đáp trả mà không phải tự tính lại độ sâu
    cây, và nó khớp đúng main line lưu trong puzzle_solutions.
    """
    for pm in node.get("player_moves", []):
        replies = pm.get("replies") or []
        if not replies:
            continue
        best = max(replies, key=lambda r: _node_plies(r["next"]))
        for r in replies:
            r["is_main"] = r is best
            _mark_main_replies(r["next"])


def build_solution_tree(
    board: chess.Board,
    mate_in: int,
    budget: _Budget | None = None,
    node_cap: int = MAX_TREE_NODES,
) -> dict:
    """Cây biến thể đầy đủ kèm metadata ở nút gốc."""
    budget = budget or _Budget()
    root = _build_node(board.copy(), mate_in, budget, [0], node_cap)
    _mark_main_replies(root)
    root.update({
        "player_color": "w" if board.turn == chess.WHITE else "b",
        "mate_in": mate_in,
        "generated_by": GENERATED_BY,
        "generated_at": datetime.now(timezone.utc).isoformat(),
    })
    return root


def _node_plies(node: dict) -> int:
    """Độ sâu (tính theo ply) của nhánh dài nhất trong nút."""
    best = 0
    for pm in node.get("player_moves", []):
        if pm.get("is_mate") or not pm.get("replies"):
            depth = 1
        else:
            depth = 1 + max(1 + _node_plies(r["next"]) for r in pm["replies"])
        best = max(best, depth)
    return best


def _main_reply(player_move: dict) -> dict | None:
    """Nhánh chống đỡ chính của một nước, dùng cờ is_main nếu đã đánh dấu."""
    replies = player_move.get("replies") or []
    if not replies:
        return None
    for r in replies:
        if r.get("is_main"):
            return r
    return max(replies, key=lambda r: _node_plies(r["next"]))


def extract_main_line(tree: dict) -> list[dict]:
    """
    Main line = biến thể bên phòng ngự cầm cự lâu nhất. Với mate trong N đúng
    nghĩa thì dài đúng 2N-1 ply. Mỗi phần tử ghi rõ `side` nên hai bên không
    còn bị trộn vào một danh sách vô danh.
    """
    player_color = tree.get("player_color", "w")
    other = "b" if player_color == "w" else "w"
    line: list[dict] = []
    node = tree

    while node and node.get("player_moves"):
        best_pm = max(node["player_moves"], key=lambda pm: _node_plies({"player_moves": [pm]}))
        line.append({
            "move_order": len(line) + 1,
            "uci": best_pm["uci"],
            "san": best_pm["san"],
            "side": player_color if len(line) % 2 == 0 else other,
        })
        best_reply = _main_reply(best_pm)
        if best_pm.get("is_mate") or best_reply is None:
            break
        line.append({
            "move_order": len(line) + 1,
            "uci": best_reply["uci"],
            "san": best_reply["san"],
            "side": player_color if len(line) % 2 == 0 else other,
        })
        node = best_reply["next"]

    return line


# ── Kiểm tra một dãy nước do người dùng nhập ─────────────────

@dataclass
class PlyCheck:
    index: int                      # 1-based
    uci: str
    san: str | None = None
    side: str | None = None         # 'w' | 'b'
    legal: bool = False
    is_player_move: bool = False    # thuộc bên tấn công (bên đi trong FEN)
    forces_mate: bool | None = None  # chỉ xét cho nước của bên tấn công
    error: str | None = None


@dataclass
class LineCheck:
    ok: bool = False
    fen: str = ""
    player_color: str = "w"
    plies: list[PlyCheck] = field(default_factory=list)
    ends_in_mate: bool = False
    mate_in: int | None = None
    declared_mate_in: int | None = None
    expected_plies: int | None = None
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    @property
    def player_moves(self) -> list[PlyCheck]:
        return [p for p in self.plies if p.is_player_move]

    @property
    def opponent_moves(self) -> list[PlyCheck]:
        return [p for p in self.plies if not p.is_player_move]


def _illegal_reason(board: chess.Board, move: chess.Move) -> str:
    """
    Chẩn đoán vì sao nước không hợp lệ. Trường hợp đáng chú ý nhất: quân ở ô
    xuất phát thuộc bên KHÔNG được đi — dấu hiệu danh sách đang lẫn nước hai bên.
    """
    turn = "w" if board.turn == chess.WHITE else "b"
    piece = board.piece_at(move.from_square)
    if piece is None:
        return f"ô {chess.square_name(move.from_square)} không có quân nào"
    piece_color = "w" if piece.color == chess.WHITE else "b"
    if piece_color != turn:
        return (
            f"đây là nước của {_COLOR_NAME_VI[piece_color]} nhưng đang là lượt "
            f"{_COLOR_NAME_VI[turn]} — danh sách có thể đang lẫn nước của hai bên"
        )
    return f"{_COLOR_NAME_VI[turn]} không thể đi nước này ở vị trí hiện tại"


def check_line_legality(fen: str, uci_list: list[str]) -> LineCheck:
    """
    Kiểm tra RẺ, không tìm kiếm: từng nước có parse được, có hợp lệ, thuộc bên
    nào. Đây là phần luôn bắt buộc với mọi loại bài — kể cả bài chiến thuật
    không có mate — nên tách riêng khỏi phần chứng minh mate vốn tốn thời gian.
    """
    result = LineCheck(fen=fen)

    try:
        board = chess.Board(fen)
    except ValueError as exc:
        result.errors.append(f"FEN không đọc được: {exc}")
        return result
    if not board.is_valid():
        result.errors.append("FEN không phải một thế cờ hợp lệ theo luật")
        return result

    attacker = board.turn
    result.player_color = "w" if attacker == chess.WHITE else "b"

    if not uci_list:
        result.errors.append("Chưa nhập nước đi lời giải nào")
        return result

    for idx, raw in enumerate(uci_list, start=1):
        token = (raw or "").strip().lower()
        check = PlyCheck(index=idx, uci=token)
        result.plies.append(check)

        if not token:
            check.error = "token rỗng"
            result.errors.append(f"Nước {idx}: token rỗng")
            break

        check.side = "w" if board.turn == chess.WHITE else "b"
        check.is_player_move = board.turn == attacker

        try:
            move = chess.Move.from_uci(token)
        except ValueError:
            check.error = "không đúng định dạng UCI (ví dụ: e2e4, e7e8q)"
            result.errors.append(f"Nước {idx} ('{token}'): {check.error}")
            break

        if move not in board.legal_moves:
            check.error = _illegal_reason(board, move)
            result.errors.append(f"Nước {idx} ('{token}'): {check.error}")
            break

        check.legal = True
        check.san = board.san(move)
        board.push(move)

    result.ends_in_mate = board.is_checkmate()
    result.ok = not result.errors
    return result


_UNSET = object()


def try_detect_mate_in(
    board: chess.Board,
    max_k: int = MAX_MATE_IN,
    budget: _Budget | None = None,
) -> tuple[int | None, bool]:
    """
    Như detect_mate_in nhưng không ném lỗi: trả (mate_in, undetermined).

    undetermined=True nghĩa là vượt hạn mức — KHÁC hẳn với "không có mate".
    Người gọi phải phân biệt hai trường hợp này: cái đầu không được phép từ
    chối bài, cái sau thì được.
    """
    engine_mate = _detect_mate_with_engine(board, max_k)
    if engine_mate is not None:
        return engine_mate, False
    try:
        return detect_mate_in(board, max_k=max_k, budget=budget), False
    except SolverBudgetExceeded:
        return None, True


def verify_solution_line(
    fen: str,
    uci_list: list[str],
    declared_mate_in: int | None = None,
    max_k: int = MAX_MATE_IN,
    budget: _Budget | None = None,
    require_mate: bool = True,
    known_mate_in: object = _UNSET,
) -> LineCheck:
    """
    Kiểm tra dãy UCI do giáo viên nhập: từng nước có hợp lệ, có đúng lượt, nước
    của bên tấn công có ép được mate, và cả dãy có kết thúc bằng chiếu hết đúng
    số nước đã khai báo.

    require_mate=False: chỉ kiểm tra tính hợp lệ và lượt đi — dùng cho bài chiến
    thuật không có mate cưỡng bức (ví dụ đòn fork thắng quân).
    known_mate_in: truyền vào khi người gọi đã tính sẵn, để khỏi tìm kiếm lại.
    """
    result = check_line_legality(fen, uci_list)
    result.declared_mate_in = declared_mate_in

    try:
        board = chess.Board(fen)
    except ValueError:
        return result   # check_line_legality đã ghi lỗi FEN

    undetermined = False
    if known_mate_in is not _UNSET:
        result.mate_in = known_mate_in  # type: ignore[assignment]
    else:
        search_k = max(max_k, declared_mate_in or 0)
        result.mate_in, undetermined = try_detect_mate_in(
            board.copy(), max_k=search_k, budget=budget,
        )
    if result.mate_in:
        result.expected_plies = result.mate_in * 2 - 1

    # Dãy đã sai ở mức hợp lệ: vẫn trả kèm mate_in để UI gợi ý được dạng đúng
    if not result.ok:
        return result

    if undetermined:
        # Nếu dãy nước hợp lệ và kết thúc bằng chiếu hết thực sự, solver chỉ
        # không đủ thời gian chứng minh bắt buộc — không phải dãy sai.
        # Chỉ ghi cảnh báo, không fail. Bài vẫn được lưu ở trạng thái chưa
        # chứng minh cưỡng bức và giáo viên có thể rà lại.
        if result.ends_in_mate:
            result.warnings.append(
                "Vị trí phức tạp: chưa xác minh được chiếu hết là bắt buộc "
                "trong hạn mức tìm kiếm, nhưng dãy nước đã dẫn tới chiếu hết thực sự."
            )
        else:
            result.errors.append(
                "Không xác định được lời giải trong hạn mức tìm kiếm"
            )
            result.ok = False
            return result

    if not require_mate and not result.mate_in:
        # Bài chiến thuật: hợp lệ là đủ, không đòi chiếu hết
        return result

    # Replay lại để kiểm tra từng nước của bên tấn công có ép được mate
    attacker_move_no = 0
    for check in result.plies:
        move = chess.Move.from_uci(check.uci)
        if check.is_player_move and result.mate_in:
            attacker_move_no += 1
            remaining = result.mate_in - (attacker_move_no - 1)
            if remaining <= 0:
                check.forces_mate = False
                check.error = f"dãy dài hơn mate trong {result.mate_in} nước"
                result.errors.append(f"Nước {check.index} ({check.san}): {check.error}")
            else:
                sub_budget = budget or _Budget()
                try:
                    keys = mating_moves(board, remaining, sub_budget)
                except SolverBudgetExceeded as exc:
                    # Budget nhỏ: không xác nhận được nước ép buộc, nhưng chưa phải là dãy sai
                    check.error = f"không kiểm tra được trong hạn mức: {exc}"
                    result.warnings.append(f"Nước {check.index} ({check.san}): {check.error}")
                    board.push(move)
                    continue
                check.forces_mate = move in keys
                if not check.forces_mate:
                    check.error = f"không ép được chiếu hết trong {remaining} nước còn lại"
                    result.errors.append(f"Nước {check.index} ({check.san}): {check.error}")
        board.push(move)

    if not result.ends_in_mate:
        result.errors.append("Dãy nước không kết thúc bằng chiếu hết (checkmate)")

    if result.ends_in_mate and result.mate_in is None:
        # undetermined: solver timeout → khị tìm, nhưng không phải xác nhận là không có mate
        # undetermined=False + mate_in=None: chứng minh được là không có mate cưỡng bức
        if undetermined:
            # Đã xử lý ở đoạn trước: đã thêm warning vào result.warnings
            pass
        else:
            msg = (
                "Dãy kết thúc bằng chiếu hết nhưng chỉ xảy ra khi đối phương đi sai — "
                "vị trí này không có mate cưỡng bức"
            )
            if declared_mate_in:
                result.errors.append(msg)
            else:
                result.warnings.append(msg)

    if declared_mate_in and result.mate_in and declared_mate_in != result.mate_in:
        result.errors.append(
            f"Bài khai báo mate trong {declared_mate_in} nước nhưng vị trí này là "
            f"mate trong {result.mate_in} nước"
        )

    if result.expected_plies and len(uci_list) > result.expected_plies:
        other = "Đen" if result.player_color == "w" else "Trắng"
        result.errors.append(
            f"Dãy có {len(uci_list)} nước, mate trong {result.mate_in} nước chỉ cần "
            f"tối đa {result.expected_plies} nước "
            f"({result.mate_in} của {_COLOR_NAME_VI[result.player_color]} "
            f"xen {result.mate_in - 1} của {other})"
        )

    result.ok = not result.errors
    return result


# ── API gộp cho tầng service ─────────────────────────────────

@dataclass
class SolveResult:
    fen: str
    player_color: str
    mate_in: int | None = None
    tree: dict | None = None
    main_line: list[dict] = field(default_factory=list)
    verified: bool = False
    error: str | None = None


def solve_puzzle(
    fen: str,
    declared_mate_in: int | None = None,
    max_k: int = MAX_MATE_IN,
    node_budget: int = DEFAULT_NODE_BUDGET,
    deadline_s: float | None = DEFAULT_DEADLINE_S,
    node_cap: int = MAX_TREE_NODES,
) -> SolveResult:
    """
    Giải một thế cờ: phát hiện khoảng cách mate, dựng cây biến thể và rút main
    line. Dùng cho đường tạo bài khi không có lời giải nhập sẵn, và cho backfill.
    """
    try:
        board = chess.Board(fen)
    except ValueError as exc:
        return SolveResult(fen=fen, player_color="w", error=f"FEN không đọc được: {exc}")
    if not board.is_valid():
        return SolveResult(
            fen=fen,
            player_color="w" if board.turn == chess.WHITE else "b",
            error="FEN không phải một thế cờ hợp lệ theo luật",
        )

    out = SolveResult(fen=fen, player_color="w" if board.turn == chess.WHITE else "b")
    budget = _Budget(node_budget, deadline_s)

    search_k = max(max_k, declared_mate_in or 0)
    try:
        out.mate_in = detect_mate_in(board.copy(), max_k=search_k, budget=budget)
    except SolverBudgetExceeded as exc:
        out.error = f"Không xác định được lời giải trong hạn mức tìm kiếm: {exc}"
        return out

    if out.mate_in is None:
        out.error = f"Không tìm thấy mate cưỡng bức trong {search_k} nước"
        return out

    try:
        out.tree = build_solution_tree(board, out.mate_in, budget=budget, node_cap=node_cap)
    except SolverBudgetExceeded as exc:
        out.error = f"Không dựng được cây biến thể: {exc}"
        return out

    out.main_line = extract_main_line(out.tree)
    out.verified = bool(out.main_line)
    if not out.verified:
        out.error = "Cây biến thể rỗng"
    return out


# ── Chấm điểm: duyệt cây ─────────────────────────────────────

def grade_against_tree(tree: dict, player_ucis: list[str]) -> tuple[bool, int]:
    """
    Chấm dãy nước CỦA NGƯỜI CHƠI theo cây. Trả (đã giải xong, số nước đúng).

    Chỉ nhận nước nằm trong `player_moves` của nút hiện tại — mà cây chứa MỌI
    nước ép mate nên mọi lời giải đúng đều được nhận, kể cả biến thể khác main
    line. Nước đáp trả của đối phương được suy từ cây, không cần client gửi lên.
    """
    if not tree or not tree.get("player_moves"):
        return False, 0

    node = tree
    matched = 0
    for raw in player_ucis:
        token = (raw or "").strip().lower()
        move = next(
            (pm for pm in node.get("player_moves", []) if pm["uci"].lower() == token),
            None,
        )
        if move is None:
            return False, matched
        matched += 1
        if move.get("is_mate"):
            return True, matched
        if not move.get("replies"):
            return False, matched
        # Bất kỳ nước chống đỡ nào cũng vẫn mate; main line lấy nhánh dài nhất.
        reply = _main_reply(move)
        if reply is None:
            return False, matched
        node = reply["next"]

    return False, matched


def tree_reply_for(tree_node: dict, player_uci: str) -> dict | None:
    """Nước đáp trả của đối phương sau một nước của người chơi, kèm nút tiếp theo."""
    token = (player_uci or "").strip().lower()
    for pm in tree_node.get("player_moves", []):
        if pm["uci"].lower() != token:
            continue
        if pm.get("is_mate"):
            return None
        return _main_reply(pm)
    return None
