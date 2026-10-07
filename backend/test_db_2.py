import asyncio
from sqlmodel import select
from app.db.session import engine
from app.models.user import User

async def main():
    async with engine.connect() as conn:
        result = await conn.execute(select(User.email, User.role))
        print(result.fetchall())

if __name__ == "__main__":
    asyncio.run(main())
