from typing import Optional, List, Dict, Any
from uuid import UUID
from datetime import datetime
from pydantic import BaseModel, Field

from app.models.base import TournamentFormat, TournamentStatus, GameResult


class TournamentBase(BaseModel):
    name: str = Field(..., max_length=300)
    description: Optional[str] = None
    format: str = Field(default=TournamentFormat.SWISS.value)
    max_rounds: int = Field(default=5, ge=1)
    time_control: Optional[str] = None
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None


class TournamentCreate(TournamentBase):
    pass


class TournamentUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    format: Optional[str] = None
    max_rounds: Optional[int] = None
    time_control: Optional[str] = None
    status: Optional[str] = None
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None


class TournamentInDBBase(TournamentBase):
    id: UUID
    center_id: Optional[UUID] = None
    created_by: UUID
    status: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class TournamentRead(TournamentInDBBase):
    pass


class TournamentParticipantBase(BaseModel):
    student_id: UUID


class TournamentParticipantRead(TournamentParticipantBase):
    id: UUID
    tournament_id: UUID
    seed: Optional[int] = None
    registered_at: datetime
    
    class Config:
        from_attributes = True


class TournamentGameRead(BaseModel):
    id: UUID
    tournament_id: UUID
    round: int
    white_player_id: UUID
    black_player_id: UUID
    result: str
    pgn: Optional[str] = None
    time_control: Optional[str] = None
    scheduled_at: Optional[datetime] = None
    played_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class TournamentStandingRead(BaseModel):
    id: UUID
    tournament_id: UUID
    student_id: UUID
    rank: Optional[int] = None
    points: float
    wins: int
    draws: int
    losses: int
    buchholz: Optional[float] = None

    class Config:
        from_attributes = True
