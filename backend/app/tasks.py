"""
Celery tasks for CAMS — placeholder module.
"""
from app.core.celery_app import celery_app


@celery_app.task(name="app.tasks.health_check")
def health_check():
    """Simple health check task."""
    return {"status": "ok"}


@celery_app.task(name="app.tasks.auto_submit_overdue_assignments")
def auto_submit_overdue_assignments():
    """Tác vụ định kỳ kiểm tra và tự động nộp các bài tập đã quá hạn nộp."""
    import asyncio
    return asyncio.run(_auto_submit_overdue_async())


async def _auto_submit_overdue_async() -> dict:
    from datetime import datetime, timezone
    from sqlalchemy import select
    from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
    from sqlalchemy.pool import NullPool
    from app.core.config import settings
    from app.models.assignment import Assignment
    from app.models.base import SubmissionStatus
    from app.models.progress import StudentProgress
    from app.services import assignment_service

    engine = create_async_engine(settings.DATABASE_URL, poolclass=NullPool)
    local_session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    now = datetime.now(timezone.utc)
    submitted_count = 0

    async with local_session_factory() as db:
        stmt = select(Assignment).where(Assignment.due_date.is_not(None), Assignment.due_date < now)
        res = await db.execute(stmt)
        overdue_assignments = res.scalars().all()

        for asm in overdue_assignments:
            prog_stmt = select(StudentProgress.student_id).where(StudentProgress.assignment_id == asm.id).distinct()
            prog_res = await db.execute(prog_stmt)
            student_ids = prog_res.scalars().all()

            for sid in student_ids:
                sub = await assignment_service.get_or_create_submission(db, asm.id, sid)
                if sub.status != SubmissionStatus.SUBMITTED.value:
                    await assignment_service.submit_assignment(db, asm.id, sid)
                    submitted_count += 1

        await db.commit()

    await engine.dispose()
    return {"status": "ok", "auto_submitted": submitted_count}

