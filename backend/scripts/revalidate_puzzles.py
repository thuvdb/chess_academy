"""
Backfill: chứng minh lại lời giải cho toàn bộ bài đã có trong thư viện.

Bài cũ lưu lời giải dạng mảng phẳng trộn lẫn nước hai bên và chưa từng được
kiểm chứng. Script này chạy mate solver cho từng bài, dựng cây biến thể, ghi
`side` cho main line và gắn cờ xác thực. Bài không chứng minh được CHỈ bị gắn
cờ `solution_verified=false` kèm lý do — không xoá, để assignment đang tham
chiếu không bị vỡ.

Chạy:
    python scripts/revalidate_puzzles.py --dry-run
    python scripts/revalidate_puzzles.py --limit 50
    python scripts/revalidate_puzzles.py
"""

import argparse
import asyncio
import os
import sys
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.core.database import async_session_factory
from app.models.puzzle import Puzzle, PuzzleSolution
from app.schemas.puzzle import PuzzleSolutionCreate
from app.services.puzzle_service import (
    _apply_solution,
    _fallback_solution_rows,
    build_solution,
)


async def revalidate(dry_run: bool, limit: int | None, deadline_s: float, max_k: int) -> int:
    verified = failed = reclassified = 0
    failures: list[tuple[str, str]] = []

    async with async_session_factory() as db:
        stmt = select(Puzzle).options(selectinload(Puzzle.solutions)).order_by(Puzzle.created_at)
        if limit:
            stmt = stmt.limit(limit)
        puzzles = list((await db.execute(stmt)).scalars().all())

    print(f"Tìm thấy {len(puzzles)} bài tập cần rà soát\n")

    for idx, snapshot in enumerate(puzzles, start=1):
        pid = snapshot.id
        title = (snapshot.title or "")[:52]
        old_type = snapshot.puzzle_type
        supplied = [
            PuzzleSolutionCreate(
                move_order=s.move_order,
                move_uci=s.move_uci,
                move_san=s.move_san or "",
            )
            for s in sorted(snapshot.solutions, key=lambda s: s.move_order)
        ] or None

        t0 = time.perf_counter()
        build = await build_solution(
            fen=snapshot.fen,
            puzzle_type=old_type or "tactic",
            supplied=supplied,
            strict=False,          # backfill không bao giờ ném lỗi
            deadline_s=deadline_s,
            max_k=max_k,           # tìm sâu hơn đường request vì chạy nền
        )
        dt = time.perf_counter() - t0

        if build.verified:
            verified += 1
            tag = f"mate in {build.mate_in}"
            if build.puzzle_type != old_type:
                reclassified += 1
                tag += f", {old_type} -> {build.puzzle_type}"
            status = f"OK   ({tag})"
        else:
            failed += 1
            failures.append((title, build.error or "không rõ"))
            status = f"FAIL ({build.error})"

        print(f"[{idx}/{len(puzzles)}] {title:54s} {status}  {dt:.1f}s")

        if dry_run:
            continue

        # Ghi từng bài trong transaction riêng: một bài hỏng không kéo đổ cả lượt chạy
        async with async_session_factory() as db:
            try:
                res = await db.execute(
                    select(Puzzle).options(selectinload(Puzzle.solutions)).where(Puzzle.id == pid)
                )
                puzzle = res.scalar_one_or_none()
                if puzzle is None:
                    continue

                old_rows = await db.execute(
                    select(PuzzleSolution).where(PuzzleSolution.puzzle_id == pid)
                )
                for row in old_rows.scalars().all():
                    await db.delete(row)
                await db.flush()

                for row in _apply_solution(puzzle, build):
                    db.add(row)
                if not build.verified:
                    for row in _fallback_solution_rows(puzzle, supplied):
                        db.add(row)
                await db.commit()
            except Exception as exc:  # noqa: BLE001
                await db.rollback()
                print(f"    !! Không ghi được {pid}: {exc}")

    print()
    print("=" * 64)
    print(f"Đã chứng minh được : {verified}")
    print(f"Cần giáo viên rà lại: {failed}")
    print(f"Được phân loại lại  : {reclassified}")
    if dry_run:
        print("\n(dry-run — chưa ghi gì vào database)")
    if failures:
        print("\nCác bài cần rà lại:")
        for title, err in failures[:30]:
            print(f"  • {title}: {err}")
        if len(failures) > 30:
            print(f"  … và {len(failures) - 30} bài nữa")
    print("=" * 64)
    return failed


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--dry-run", action="store_true", help="chỉ báo cáo, không ghi DB")
    ap.add_argument("--limit", type=int, default=None, help="chỉ xử lý N bài đầu")
    ap.add_argument(
        "--deadline", type=float, default=120.0,
        help="giới hạn giây cho mỗi bài (mặc định 120; mate-in-4 có thể mất ~40s)",
    )
    ap.add_argument(
        "--max-mate", type=int, default=4,
        help="độ sâu tìm mate tối đa (mặc định 4; đường request chỉ tìm tới 3)",
    )
    args = ap.parse_args()
    asyncio.run(revalidate(args.dry_run, args.limit, args.deadline, args.max_mate))


if __name__ == "__main__":
    main()
