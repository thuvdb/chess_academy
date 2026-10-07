import asyncio
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from app.models.assignment import Assignment
from app.models.class_ import Class
from sqlalchemy import select
from sqlalchemy.orm import selectinload

async def test_db():
    engine = create_async_engine("postgresql+asyncpg://cams_user:cams_password@localhost:5432/cams_db")
    async_session = async_sessionmaker(engine, expire_on_commit=False)
    
    async with async_session() as db:
        stmt = select(Assignment).options(selectinload(Assignment.class_))
        result = await db.execute(stmt)
        assignments = result.scalars().all()
        for a in assignments:
            print(f"Assignment ID: {a.id}, Title: {a.title}, Class ID: {a.class_id}")
            if a.class_:
                print(f"   -> Class loaded: {a.class_.name}")
            else:
                print(f"   -> Class NOT LOADED (None)")
                
asyncio.run(test_db())
