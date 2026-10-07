import asyncio
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text
import sys

async def main():
    engine = create_async_engine("postgresql+asyncpg://cams_user:cams_password@localhost:5432/cams_db")
    async with engine.connect() as conn:
        result = await conn.execute(text("SELECT p.fen, s.move_order, s.move_uci, s.is_best_move FROM puzzles p JOIN puzzle_solutions s ON p.id = s.puzzle_id ORDER BY p.id LIMIT 10"))
        for row in result.fetchall():
            print(f"FEN: {row[0]}, order: {row[1]}, uci: {row[2]}, best: {row[3]}")

if __name__ == "__main__":
    asyncio.run(main())
