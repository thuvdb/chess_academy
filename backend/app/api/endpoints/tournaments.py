from typing import List
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.api.deps import get_db, get_current_user
from app.models.user import User
from app.models.tournament import Tournament, TournamentParticipant, TournamentStanding, TournamentGame
from app.schemas.tournament import (
    TournamentCreate,
    TournamentRead,
    TournamentParticipantRead,
    TournamentParticipantBase,
    TournamentStandingRead,
    TournamentGameRead
)
from app.services.tournament_service import TournamentService

router = APIRouter()


@router.get("", response_model=List[TournamentRead])
@router.get("/", response_model=List[TournamentRead], include_in_schema=False)
async def list_tournaments(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(select(Tournament).where(Tournament.center_id == current_user.center_id))
    return result.scalars().all()


@router.post("", response_model=TournamentRead, status_code=status.HTTP_201_CREATED)
@router.post("/", response_model=TournamentRead, status_code=status.HTTP_201_CREATED, include_in_schema=False)
async def create_tournament(
    req: TournamentCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if current_user.role not in ["super_admin", "admin", "center_admin", "teacher"]:
        raise HTTPException(status_code=403, detail="Not authorized")
    
    t = Tournament(
        center_id=current_user.center_id,
        created_by=current_user.id,
        name=req.name,
        description=req.description,
        format=req.format,
        max_rounds=req.max_rounds,
        time_control=req.time_control,
        start_date=req.start_date,
        end_date=req.end_date,
    )
    db.add(t)
    await db.commit()
    await db.refresh(t)
    return t


@router.get("/{id}", response_model=TournamentRead)
async def get_tournament(
    id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    service = TournamentService(db)
    t = await service.get_tournament(id)
    if not t or t.center_id != current_user.center_id:
        raise HTTPException(status_code=404, detail="Tournament not found")
    return t


@router.post("/{id}/register", response_model=TournamentParticipantRead)
async def register_player(
    id: UUID,
    req: TournamentParticipantBase,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    # Only students can register themselves, or admin/teacher can register students
    if current_user.role == "student" and current_user.id != req.student_id:
        raise HTTPException(status_code=403, detail="Can only register yourself")
        
    service = TournamentService(db)
    t = await service.get_tournament(id)
    if not t or t.center_id != current_user.center_id:
        raise HTTPException(status_code=404, detail="Tournament not found")
        
    try:
        participant = await service.register_player(id, req.student_id)
        return participant
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/{id}/start")
async def start_tournament(
    id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if current_user.role not in ["super_admin", "admin", "center_admin", "teacher"]:
        raise HTTPException(status_code=403, detail="Not authorized")
        
    service = TournamentService(db)
    try:
        await service.start_tournament(id)
        return {"message": "Tournament started successfully"}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/{id}/reset")
async def reset_tournament(
    id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if current_user.role not in ["super_admin", "admin", "center_admin", "teacher"]:
        raise HTTPException(status_code=403, detail="Not authorized")
        
    service = TournamentService(db)
    try:
        await service.reset_tournament(id)
        return {"message": "Tournament reset successfully"}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/{id}/standings", response_model=List[TournamentStandingRead])
async def get_standings(
    id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(TournamentStanding)
        .where(TournamentStanding.tournament_id == id)
        .order_by(TournamentStanding.points.desc())
    )
    standings = result.scalars().all()
    # Enrich with student name
    enriched = []
    for s in standings:
        data = TournamentStandingRead.model_validate(s)
        if hasattr(s, 'student') and s.student:
            data.student_name = s.student.full_name or s.student.email
        enriched.append(data)
    return enriched


@router.get("/{id}/games", response_model=List[TournamentGameRead])
async def get_games(
    id: UUID,
    round_num: int = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    query = select(TournamentGame).where(TournamentGame.tournament_id == id)
    if round_num:
        query = query.where(TournamentGame.round == round_num)
    
    result = await db.execute(query)
    games = result.scalars().all()
    # Enrich with player names
    enriched = []
    for g in games:
        data = TournamentGameRead.model_validate(g)
        if hasattr(g, 'white_player') and g.white_player:
            data.white_player_name = g.white_player.full_name or g.white_player.email
        if hasattr(g, 'black_player') and g.black_player:
            data.black_player_name = g.black_player.full_name or g.black_player.email
        enriched.append(data)
    return enriched
