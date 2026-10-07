import asyncio
import httpx
from app.core.database import async_session_factory
from app.core.security import create_access_token
from app.models.user import User
from sqlalchemy import select
import json

async def main():
    async with async_session_factory() as db:
        res = await db.execute(select(User).where(User.role == 'teacher').limit(1))
        user = res.scalar_one_or_none()
        token = create_access_token(data={"sub": str(user.id)})

    async with httpx.AsyncClient() as client:
        resp = await client.get(
            "http://localhost:8000/api/assignments",
            headers={"Authorization": f"Bearer {token}"}
        )
        print(resp.text)

asyncio.run(main())
