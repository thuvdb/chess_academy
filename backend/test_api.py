import asyncio
import httpx
from app.core.config import settings
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

    api_base = f"{settings.API_PUBLIC_URL.rstrip('/')}/api"
    async with httpx.AsyncClient() as client:
        resp = await client.get(
            f"{api_base}/assignments",
            headers={"Authorization": f"Bearer {token}"}
        )
        print(resp.text)

asyncio.run(main())
