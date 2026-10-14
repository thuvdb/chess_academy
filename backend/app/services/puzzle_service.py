"""
Puzzle Service — Sprint 4
Handles Puzzle CRUD, solution management, FEN validation, and Puzzle Rating calculation.

Lời giải được chứng minh bằng app/services/mate_solver.py trước khi bài được
nhận vào thư viện: từng nước phải hợp lệ, đúng lượt, và cả dãy phải dẫn tới
chiếu hết đúng số nước. Kết quả lưu thành cây biến thể (Puzzle.solution_tree)
tách riêng nước của hai bên, thay cho mảng phẳng trộn lẫn trước đây.
"""

import logging
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional

import anyio
import chess
from sqlalchemy import desc, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.base import PuzzleDifficulty, PuzzleSource, PuzzleType, ReviewStatus
from app.models.puzzle import Puzzle, PuzzleSolution
from app.models.scan import ScanResult
from app.schemas.puzzle import (
    CreatePuzzleFromScanRequest,
    PuzzleCreate,
    PuzzleSolutionCreate,
    PuzzleUpdate,
)
from app.services import mate_solver

logger = logging.getLogger(__name__)


# ── Rating Calculation ───────────────────────────────────────

def calculate_new_puzzle_rating(
    user_rating: int, puzzle_rating: int, solved: bool
) -> tuple[int, int]:
    """
    K-factor formula per Sprint 4 spec:
      - K = 32 if rating < 1200
      - K = 24 if rating < 2000
      - K = 16 if rating >= 2000
    Lưu ý: Puzzle Rating KHÔNG phải ELO. ELO chỉ thay đổi qua Tournament.
    """
    if user_rating < 1200:
        k = 32
    elif user_rating < 2000:
        k = 24
    else:
        k = 16

    expected_user = 1.0 / (1.0 + 10.0 ** ((puzzle_rating - user_rating) / 400.0))
    actual_user = 1.0 if solved else 0.0

    delta_user = round(k * (actual_user - expected_user))
    new_user_rating = max(100, user_rating + delta_user)

    # Adjust puzzle rating inversely (K_puzzle = 16)
    k_puzzle = 16
    expected_puzzle = 1.0 - expected_user
    actual_puzzle = 1.0 - actual_user
    delta_puzzle = round(k_puzzle * (actual_puzzle - expected_puzzle))
    new_puzzle_rating = max(100, puzzle_rating + delta_puzzle)

    return new_user_rating, new_puzzle_rating


# ── FEN Validation ───────────────────────────────────────────

def validate_puzzle_fen(fen: str) -> tuple[bool, str | None]:
    """Validates if FEN can be parsed and is legal."""
    try:
        board = chess.Board(fen)
        if not board.is_valid():
            return False, "Invalid board position according to chess rules"
        return True, None
    except ValueError as exc:
        return False, str(exc)


DIFFICULTY_MAP = {
    "beginner": "easy",
    "easy": "easy",
    "intermediate": "medium",
    "medium": "medium",
    "advanced": "hard",
    "hard": "hard",
    "master": "expert",
    "expert": "expert",
}

PUZZLE_TYPE_MAP = {
    "tactics": "tactic",
    "tactic": "tactic",
    "endgame": "endgame",
    "opening": "opening",
    "strategy": "strategy",
    "custom": "custom",
    "mate_in_1": "mate_in_1",
    "mate_in_2": "mate_in_2",
    "mate_in_3": "mate_in_3",
    "mate_in_4": "mate_in_4",
    # alias gạch ngang (do _infer_puzzle_type_from_filename trả về 'mate-in-N')
    "mate-in-1": "mate_in_1",
    "mate-in-2": "mate_in_2",
    "mate-in-3": "mate_in_3",
    "mate-in-4": "mate_in_4",
    "fork": "tactic",
    "pin": "tactic",
}

SOURCE_MAP = {
    "manual_fen": "manual_fen",
    "manual_pgn": "manual_pgn",
    "ai_scanned": "ai_scanned",
    "book_scan": "ai_scanned",
    "imported": "imported",
}

MATE_TYPE_TO_N = {
    "mate_in_1": 1, "mate_in_2": 2, "mate_in_3": 3, "mate_in_4": 4,
    # alias gạch ngang
    "mate-in-1": 1, "mate-in-2": 2, "mate-in-3": 3, "mate-in-4": 4,
}
# Ánh xạ ngược: số nước → chuẩn gạch dưới (để lưu vào DB nhất quán)
MATE_N_TO_TYPE = {1: "mate_in_1", 2: "mate_in_2", 3: "mate_in_3", 4: "mate_in_4"}


def declared_mate_in(puzzle_type: str | None) -> int | None:
    """Số nước mate mà nhãn bài khai báo, hoặc None nếu không phải bài mate."""
    return MATE_TYPE_TO_N.get((puzzle_type or "").lower())


# ── Solution Verification ────────────────────────────────────

@dataclass
class SolutionBuild:
    """Kết quả dựng lời giải cho một bài, đã qua chứng minh."""
    main_line: list[dict] = field(default_factory=list)
    tree: dict | None = None
    mate_in: int | None = None
    puzzle_type: str = "tactic"
    verified: bool = False
    error: str | None = None


def format_line_errors(check: mate_solver.LineCheck) -> str:
    """Thông báo lỗi cho giáo viên, nêu rõ sai ở nước nào."""
    lines = ["Lời giải không hợp lệ:"]
    lines += [f"• {e}" for e in check.errors]
    if check.mate_in:
        side = "Trắng" if check.player_color == "w" else "Đen"
        other = "Đen" if check.player_color == "w" else "Trắng"
        lines.append(
            f"• Vị trí này là mate trong {check.mate_in} nước, nên dãy lời giải cần "
            f"{check.mate_in} nước của {side} xen {check.mate_in - 1} nước của "
            f"{other} — tối đa {check.mate_in * 2 - 1} nước."
        )
    return "\n".join(lines)


def _line_from_tree(tree: dict) -> list[dict]:
    return mate_solver.extract_main_line(tree)


def _solve_sync(
    fen: str,
    puzzle_type: str,
    supplied_ucis: list[str],
    deadline_s: float,
    max_k: int = mate_solver.MAX_MATE_IN,
) -> SolutionBuild:
    """
    Phần tính toán nặng, chạy trong thread riêng. Không chạm DB.

    Phân biệt ba kết cục:
      • Dãy nước SAI (không hợp lệ, sai lượt, không dẫn tới mate đã khai báo)
        → ValueError → HTTP 400. Bài không vào được thư viện.
      • Chứng minh được → verified, dựng cây biến thể.
      • Chưa kết luận được trong hạn mức (mate sâu) hoặc không có mate cưỡng bức
        → lưu ở trạng thái chưa chứng minh, KHÔNG chặn. Bài chiến thuật thắng
        quân rơi vào nhánh này.
    """
    decl = declared_mate_in(puzzle_type)
    out = SolutionBuild(puzzle_type=puzzle_type)
    budget = mate_solver._Budget(
        mate_solver.DEFAULT_NODE_BUDGET, deadline_s=deadline_s,
    )

    # 1. Tính hợp lệ của từng nước — rẻ, không cần tìm kiếm, và luôn bắt buộc
    legality = (
        mate_solver.check_line_legality(fen, supplied_ucis) if supplied_ucis else None
    )

    # 2. Tìm mate cưỡng bức (có thể vượt hạn mức với mate sâu)
    search_k = max(max_k, decl or 0)
    out.mate_in, undetermined = mate_solver.try_detect_mate_in(
        chess.Board(fen), max_k=search_k, budget=budget,
    )
    if undetermined:
        out.error = (
            "Chưa xác minh được trong hạn mức tìm kiếm nhanh. "
            "Chạy scripts/revalidate_puzzles.py để xác minh nền."
        )

    # 3. Dãy nước sai ở mức hợp lệ → chặn, kèm gợi ý số nước đúng
    if legality is not None and not legality.ok:
        legality.mate_in = out.mate_in
        if out.mate_in:
            legality.expected_plies = out.mate_in * 2 - 1
        raise ValueError(format_line_errors(legality))

    # 4. Không có mate cưỡng bức
    if out.mate_in is None:
        if decl and not undetermined:
            # Nhãn nói là bài mate nhưng chứng minh được là không có
            raise ValueError(
                f"Bài khai báo chiếu hết sau {decl} nước nhưng vị trí này không có "
                f"mate cưỡng bức trong {search_k} nước. Hãy kiểm tra lại FEN hoặc "
                f"đổi thể loại bài."
            )
        out.error = out.error or (
            "Không tìm thấy mate cưỡng bức; bài được lưu nhưng lời giải chưa được chứng minh"
        )
        return out

    # 5. Có mate — kiểm tra đầy đủ dãy nước người dùng nhập
    if supplied_ucis:
        check = mate_solver.verify_solution_line(
            fen, supplied_ucis,
            declared_mate_in=decl,
            budget=budget,
            known_mate_in=out.mate_in,
        )
        if not check.ok:
            raise ValueError(format_line_errors(check))

    # Tự phân loại lại khi nhãn không khớp thực tế (ví dụ bài quét PDF bị gắn "tactic")
    out.puzzle_type = MATE_N_TO_TYPE.get(out.mate_in, puzzle_type)

    try:
        out.tree = mate_solver.build_solution_tree(
            chess.Board(fen), out.mate_in, budget=budget,
        )
    except mate_solver.SolverBudgetExceeded as exc:
        out.error = f"Không dựng được cây biến thể: {exc}"
        return out

    out.main_line = _line_from_tree(out.tree)
    out.verified = bool(out.main_line)
    if not out.verified:
        out.error = "Cây biến thể rỗng"
    return out


async def build_solution(
    fen: str,
    puzzle_type: str,
    supplied: list[PuzzleSolutionCreate] | None = None,
    strict: bool = True,
    deadline_s: float = mate_solver.DEFAULT_DEADLINE_S,
    max_k: int = mate_solver.MAX_MATE_IN,
) -> SolutionBuild:
    """
    Chứng minh lời giải cho một bài.

    strict=True  (form nhập tay): dãy nước sai → ValueError → HTTP 400.
    strict=False (quét PDF hàng loạt): không chặn, chỉ gắn cờ chưa chứng minh
                 để một bàn hỏng không làm fail cả batch.
    max_k: độ sâu tìm mate. Mặc định 3 cho đường request (mate-in-4 tốn hàng
           chục giây); script backfill nâng lên qua tham số.
    """
    supplied_ucis = [
        (s.move_uci or "").strip()
        for s in sorted(supplied or [], key=lambda s: s.move_order)
        if (s.move_uci or "").strip()
    ]
    try:
        return await anyio.to_thread.run_sync(
            _solve_sync, fen, puzzle_type, supplied_ucis, deadline_s, max_k,
        )
    except ValueError as exc:
        if strict:
            raise
        return SolutionBuild(
            puzzle_type=puzzle_type,
            error=f"Lời giải không chứng minh được: {exc}",
        )
    except Exception as exc:  # noqa: BLE001 - không để solver làm hỏng request
        logger.warning("Solver thất bại cho FEN %s: %s", fen, exc)
        if strict:
            raise ValueError(f"Không kiểm tra được lời giải: {exc}")
        return SolutionBuild(puzzle_type=puzzle_type, error=f"Solver lỗi: {exc}")


async def verify_line(
    fen: str,
    moves_uci: list[str],
    puzzle_type: str | None = None,
) -> mate_solver.LineCheck:
    """
    Kiểm tra một dãy UCI mà không ghi gì — dùng cho endpoint validate-solution.

    Phải khớp đúng luật mà _solve_sync áp dụng khi lưu, nếu không form sẽ báo
    một đằng còn backend nhận một nẻo: chỉ bài gắn nhãn mate mới bắt buộc dãy
    nước kết thúc bằng chiếu hết.
    """
    decl = declared_mate_in(puzzle_type)
    tokens = [(m or "").strip() for m in moves_uci if (m or "").strip()]
    # Tìm đủ sâu theo số nước đã khai báo — nếu bài mate-in-4 mà chỉ tìm 3 nước
    # thì solver sẽ báo undetermined dù dãy nước hợp lệ.
    search_k = max(mate_solver.MAX_MATE_IN, decl or 0)
    return await anyio.to_thread.run_sync(
        lambda: mate_solver.verify_solution_line(
            fen,
            tokens,
            declared_mate_in=decl,
            max_k=search_k,
            require_mate=decl is not None,
            budget=mate_solver._Budget(
                mate_solver.DEFAULT_NODE_BUDGET,
                deadline_s=mate_solver.DEFAULT_DEADLINE_S,
            ),
        )
    )


def _apply_solution(puzzle: Puzzle, build: SolutionBuild) -> list[PuzzleSolution]:
    """Ghi kết quả chứng minh lên puzzle và dựng các dòng main line."""
    puzzle.solution_tree = build.tree
    puzzle.mate_in = build.mate_in
    puzzle.solution_verified = build.verified
    puzzle.verification_error = build.error
    puzzle.solution_verified_at = datetime.now(timezone.utc) if build.verified else None
    if build.verified:
        puzzle.puzzle_type = build.puzzle_type

    rows: list[PuzzleSolution] = []
    for mv in build.main_line:
        rows.append(PuzzleSolution(
            puzzle_id=puzzle.id,
            move_order=mv["move_order"],
            move_uci=mv["uci"],
            move_san=mv["san"],
            side=mv["side"],
            is_best_move=True,
            explanation=_explain(mv, build),
        ))
    return rows


def _explain(mv: dict, build: SolutionBuild) -> str:
    """Chú thích nêu rõ nước này của bên nào — không còn gộp chung vô danh."""
    is_player = mv["side"] == (build.tree or {}).get("player_color", "w")
    move_no = (mv["move_order"] + 1) // 2
    who = "Trắng" if mv["side"] == "w" else "Đen"
    if is_player:
        return f"Nước {move_no} của {who}: {mv['san']}"
    return f"Đáp trả của {who}: {mv['san']}"



# ── CRUD Operations ──────────────────────────────────────────

async def create_puzzle(
    db: AsyncSession,
    created_by: uuid.UUID,
    data: PuzzleCreate,
    strict: bool = True,
) -> Puzzle:
    valid, err = validate_puzzle_fen(data.fen)
    if not valid:
        raise ValueError(f"Invalid FEN: {err}")

    diff = DIFFICULTY_MAP.get((data.difficulty or "").lower(), "easy")
    p_type = PUZZLE_TYPE_MAP.get((data.puzzle_type or "").lower(), "tactic")
    src = SOURCE_MAP.get((data.source or "").lower(), "manual_fen")

    # Chứng minh lời giải TRƯỚC khi ghi bất cứ thứ gì: strict=True thì dãy nước
    # sai sẽ ném ValueError ở đây và bài không vào được thư viện.
    build = await build_solution(
        fen=data.fen,
        puzzle_type=p_type,
        supplied=data.solutions,
        strict=strict,
    )

    puzzle = Puzzle(
        center_id=data.center_id,
        created_by=created_by,
        title=data.title,
        description=data.description,
        fen=data.fen,
        pgn=data.pgn,
        difficulty=diff,
        puzzle_type=p_type,
        source=src,
        tags=data.tags,
        rating=data.rating,
        board_image_url=data.board_image_url,
    )
    db.add(puzzle)
    await db.flush()

    for row in _apply_solution(puzzle, build):
        db.add(row)

    if not build.verified:
        # Bài không chứng minh được mate: giữ lời giải người dùng nhập (nếu có)
        # hoặc thử Stockfish, nhưng vẫn đánh dấu chưa xác thực.
        for row in _fallback_solution_rows(puzzle, data.solutions):
            db.add(row)
        logger.info(
            "Puzzle %s lưu ở trạng thái chưa chứng minh: %s", puzzle.id, build.error,
        )

    await db.flush()
    await db.refresh(puzzle)
    return puzzle


def _fallback_solution_rows(
    puzzle: Puzzle,
    supplied: list[PuzzleSolutionCreate] | None,
) -> list[PuzzleSolution]:
    """
    Lời giải cho bài KHÔNG phải mate (hoặc chưa chứng minh được). Vẫn replay
    trên bàn cờ để điền `side` và SAN đúng, nên dù chưa xác thực thì hai bên
    cũng không còn bị trộn vô danh.
    """
    ucis = [
        (s.move_uci or "").strip()
        for s in sorted(supplied or [], key=lambda s: s.move_order)
        if (s.move_uci or "").strip()
    ]
    if not ucis:
        try:
            from app.services.stockfish_service import generate_puzzle_solutions
            auto = generate_puzzle_solutions(puzzle.fen)
            ucis = [s["move_uci"] for s in auto]
        except Exception as exc:  # noqa: BLE001 - Stockfish không có khi chạy local
            logger.warning("Không sinh được lời giải dự phòng: %s", exc)
            return []

    rows: list[PuzzleSolution] = []
    try:
        board = chess.Board(puzzle.fen)
    except ValueError:
        return []

    for order, uci in enumerate(ucis, start=1):
        try:
            move = chess.Move.from_uci(uci.lower())
        except ValueError:
            break
        if move not in board.legal_moves:
            break
        side = "w" if board.turn == chess.WHITE else "b"
        san = board.san(move)
        board.push(move)
        rows.append(PuzzleSolution(
            puzzle_id=puzzle.id,
            move_order=order,
            move_uci=uci.lower(),
            move_san=san,
            side=side,
            is_best_move=True,
            explanation=f"{'Trắng' if side == 'w' else 'Đen'}: {san}",
        ))
    return rows


async def get_puzzle(
    db: AsyncSession, puzzle_id: uuid.UUID
) -> Puzzle | None:
    stmt = (
        select(Puzzle)
        .options(selectinload(Puzzle.solutions))
        .where(Puzzle.id == puzzle_id)
    )
    result = await db.execute(stmt)
    puzzle = result.scalar_one_or_none()

    # Backfill chậm cho bài cũ chưa có cây biến thể. Chỉ thử ĐÚNG MỘT LẦN cho
    # mỗi bài: khi không xác minh được, verification_error được ghi lại và lần
    # mở sau sẽ bỏ qua, nếu không mỗi lượt GET đều tốn vài giây vô ích.
    # Dùng scripts/revalidate_puzzles.py để backfill hàng loạt thay vì dựa vào đây.
    should_try = (
        puzzle is not None
        and puzzle.solution_tree is None
        and not puzzle.solution_verified
        and not puzzle.verification_error
    )
    if should_try:
        try:
            build = await build_solution(
                fen=puzzle.fen,
                puzzle_type=puzzle.puzzle_type or "tactic",
                supplied=[
                    PuzzleSolutionCreate(
                        move_order=s.move_order,
                        move_uci=s.move_uci,
                        move_san=s.move_san,
                    )
                    for s in sorted(puzzle.solutions, key=lambda s: s.move_order)
                ] or None,
                strict=False,
                deadline_s=4.0,
            )
            if build.verified:
                for old in list(puzzle.solutions):
                    await db.delete(old)
                await db.flush()
                for row in _apply_solution(puzzle, build):
                    db.add(row)
                await db.commit()
                res_reload = await db.execute(stmt)
                puzzle = res_reload.scalar_one_or_none()
            elif build.error:
                puzzle.verification_error = build.error
                await db.commit()
                await db.refresh(puzzle)
        except Exception as exc:  # noqa: BLE001
            await db.rollback()
            logger.warning("Backfill cây biến thể thất bại cho %s: %s", puzzle_id, exc)
    return puzzle


async def list_puzzles(
    db: AsyncSession,
    difficulty: Optional[str] = None,
    puzzle_type: Optional[str] = None,
    search: Optional[str] = None,
    center_id: Optional[uuid.UUID] = None,
    skip: int = 0,
    limit: int = 50,
    verified_only: bool = False,
) -> list[Puzzle]:
    stmt = select(Puzzle).options(selectinload(Puzzle.solutions))

    if verified_only:
        # Học sinh chỉ thấy bài đã chứng minh được lời giải
        stmt = stmt.where(Puzzle.solution_verified.is_(True))
    if difficulty:
        norm_diff = DIFFICULTY_MAP.get(difficulty.lower(), difficulty.lower())
        stmt = stmt.where(Puzzle.difficulty == norm_diff)
    if puzzle_type:
        norm_type = PUZZLE_TYPE_MAP.get(puzzle_type.lower(), puzzle_type.lower())
        stmt = stmt.where(Puzzle.puzzle_type == norm_type)
    if center_id:
        stmt = stmt.where(or_(Puzzle.center_id == center_id, Puzzle.center_id.is_(None)))
    if search:
        search_fmt = f"%{search}%"
        stmt = stmt.where(
            or_(
                Puzzle.title.ilike(search_fmt),
                Puzzle.description.ilike(search_fmt),
            )
        )

    stmt = stmt.order_by(desc(Puzzle.created_at)).offset(skip).limit(limit)
    result = await db.execute(stmt)
    return list(result.scalars().all())


async def update_puzzle(
    db: AsyncSession,
    puzzle: Puzzle,
    data: PuzzleUpdate,
) -> Puzzle:
    if data.fen is not None:
        valid, err = validate_puzzle_fen(data.fen)
        if not valid:
            raise ValueError(f"Invalid FEN: {err}")
        puzzle.fen = data.fen

    if data.title is not None:
        puzzle.title = data.title
    if data.description is not None:
        puzzle.description = data.description
    if data.pgn is not None:
        puzzle.pgn = data.pgn
    if data.difficulty is not None:
        puzzle.difficulty = DIFFICULTY_MAP.get(data.difficulty.lower(), "easy")
    if data.puzzle_type is not None:
        puzzle.puzzle_type = PUZZLE_TYPE_MAP.get(data.puzzle_type.lower(), "tactic")
    if data.tags is not None:
        puzzle.tags = data.tags
    if data.rating is not None:
        puzzle.rating = data.rating
    if data.board_image_url is not None:
        puzzle.board_image_url = data.board_image_url

    # Đổi FEN, đổi lời giải hay đổi nhãn mate đều làm lời giải cũ hết hiệu lực
    needs_resolve = (
        data.fen is not None
        or data.solutions is not None
        or data.puzzle_type is not None
    )
    if needs_resolve:
        supplied = data.solutions
        if supplied is None:
            # Chỉ đổi nhãn: chứng minh lại main line đang lưu
            supplied = [
                PuzzleSolutionCreate(
                    move_order=s.move_order,
                    move_uci=s.move_uci,
                    move_san=s.move_san,
                )
                for s in sorted(puzzle.solutions, key=lambda s: s.move_order)
            ] or None

        build = await build_solution(
            fen=puzzle.fen,
            puzzle_type=puzzle.puzzle_type or "tactic",
            supplied=supplied,
            strict=True,
        )

        existing_stmt = select(PuzzleSolution).where(PuzzleSolution.puzzle_id == puzzle.id)
        existing = await db.execute(existing_stmt)
        for old in existing.scalars().all():
            await db.delete(old)
        await db.flush()

        for row in _apply_solution(puzzle, build):
            db.add(row)
        if not build.verified:
            for row in _fallback_solution_rows(puzzle, supplied):
                db.add(row)

    await db.flush()
    await db.refresh(puzzle)
    return puzzle


async def delete_puzzle(db: AsyncSession, puzzle: Puzzle) -> None:
    # Delete solutions
    stmt = select(PuzzleSolution).where(PuzzleSolution.puzzle_id == puzzle.id)
    solutions = await db.execute(stmt)
    for s in solutions.scalars().all():
        await db.delete(s)

    await db.delete(puzzle)
    await db.flush()


async def create_puzzle_from_scan(
    db: AsyncSession,
    user_id: uuid.UUID,
    req: CreatePuzzleFromScanRequest,
    center_id: Optional[uuid.UUID] = None,
    strict: bool = False,
) -> Puzzle:
    """
    Converts an approved ScanResult into a Puzzle.

    strict=False mặc định: một bàn cờ quét hỏng không được làm fail cả batch
    PDF — bài vẫn được lưu nhưng gắn cờ chưa chứng minh để giáo viên rà lại.
    """
    scan_stmt = select(ScanResult).where(ScanResult.id == req.scan_result_id)
    res = await db.execute(scan_stmt)
    scan_res = res.scalar_one_or_none()
    if not scan_res:
        raise ValueError("Scan result not found")

    # If already created, return existing
    if scan_res.puzzle_id:
        existing = await get_puzzle(db, scan_res.puzzle_id)
        if existing:
            return existing

    target_fen = scan_res.fen_final or scan_res.fen_candidate
    if not target_fen:
        raise ValueError("Scan result has no FEN")

    inferred_type = req.puzzle_type
    if not inferred_type or inferred_type == "tactic":
        from app.models.scan import ScanJob
        job = await db.get(ScanJob, scan_res.job_id)
        if job and job.file_name:
            from app.api.endpoints.scan import _infer_puzzle_type_from_filename
            inferred_type = _infer_puzzle_type_from_filename(job.file_name)

    puzzle_data = PuzzleCreate(
        title=req.title,
        description=req.description,
        fen=target_fen,
        difficulty=req.difficulty,
        puzzle_type=inferred_type or "tactic",
        source=PuzzleSource.AI_SCANNED.value,
        tags=req.tags,
        board_image_url=scan_res.board_image_url,
        solutions=req.solutions,
        center_id=center_id,
    )

    puzzle = await create_puzzle(db, created_by=user_id, data=puzzle_data, strict=strict)

    # Link back to scan result
    scan_res.puzzle_id = puzzle.id
    scan_res.review_status = ReviewStatus.APPROVED.value
    await db.flush()

    return puzzle
