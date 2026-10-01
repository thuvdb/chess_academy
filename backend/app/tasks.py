"""
Celery tasks for CAMS — placeholder module.
"""
from app.core.celery_app import celery_app


@celery_app.task(name="app.tasks.health_check")
def health_check():
    """Simple health check task."""
    return {"status": "ok"}
