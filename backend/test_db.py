import asyncio
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from app.core.database import async_session_factory
from app.models.assignment import Assignment
from app.schemas.assignment import AssignmentRead

async def main():
    async with async_session_factory() as db:
        stmt = select(Assignment).options(selectinload(Assignment.class_)).limit(1)
        res = await db.execute(stmt)
        a = res.scalar_one_or_none()
        if a:
            print("assignment id:", a.id)
            print("class_ loaded:", a.class_ is not None)
            if a.class_:
                print("class_.name:", a.class_.name)
            
            # test pydantic
            schema = AssignmentRead.model_validate(a)
            print("JSON:", schema.model_dump_json())
        else:
            print("no assignment")

asyncio.run(main())
