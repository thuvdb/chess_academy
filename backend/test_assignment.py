import asyncio
from app.core.database import async_session_maker
from app.services import assignment_service

async def main():
    async with async_session_maker() as db:
        res = await assignment_service.list_assignments(db, limit=1)
        for a in res:
            print("assignment id:", a.id)
            print("class_:", a.class_.name if a.class_ else None)

asyncio.run(main())
