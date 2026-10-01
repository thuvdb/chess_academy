"""
Leaderboard API — Sprint 4
Endpoints for student rankings and statistics.
"""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.core.database import get_db
from app.models.user import User
from app.schemas.progress import LeaderboardEntry
from app.services import progress_service

router = APIRouter()


@router.get("", response_model=list[LeaderboardEntry])
async def get_leaderboard(
    limit: int = Query(50, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get academy leaderboard ranked by points and rating."""
    return await progress_service.get_leaderboard(
        db=db,
        center_id=current_user.center_id,
        limit=limit,
    )
