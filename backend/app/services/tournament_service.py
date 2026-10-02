import math
import random
from typing import List, Optional
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.models.tournament import (
    Tournament,
    TournamentParticipant,
    TournamentGame,
    TournamentStanding,
)
from app.models.base import TournamentStatus, GameResult


class TournamentService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_tournament(self, tournament_id: UUID) -> Optional[Tournament]:
        result = await self.db.execute(
            select(Tournament).where(Tournament.id == tournament_id)
        )
        return result.scalars().first()

    async def register_player(self, tournament_id: UUID, student_id: UUID) -> TournamentParticipant:
        # Check if already registered
        result = await self.db.execute(
            select(TournamentParticipant).where(
                TournamentParticipant.tournament_id == tournament_id,
                TournamentParticipant.student_id == student_id,
            )
        )
        existing = result.scalars().first()
        if existing:
            raise ValueError("Player already registered for this tournament")

        participant = TournamentParticipant(
            tournament_id=tournament_id,
            student_id=student_id,
        )
        self.db.add(participant)
        
        # Add to standings with 0 points
        standing = TournamentStanding(
            tournament_id=tournament_id,
            student_id=student_id,
            points=0.0,
            wins=0,
            draws=0,
            losses=0,
        )
        self.db.add(standing)
        
        await self.db.commit()
        await self.db.refresh(participant)
        return participant

    async def start_tournament(self, tournament_id: UUID):
        tournament = await self.get_tournament(tournament_id)
        if not tournament:
            raise ValueError("Tournament not found")
        if tournament.status != TournamentStatus.DRAFT.value:
            raise ValueError("Tournament is not in DRAFT status")

        # Update status
        tournament.status = TournamentStatus.IN_PROGRESS.value
        await self.db.commit()
        
        # Generate round 1 pairings
        await self.generate_pairings(tournament_id, round_num=1)

    async def generate_pairings(self, tournament_id: UUID, round_num: int):
        """
        MVP Pairing: Simple random pairing for Round 1.
        (Future: Implement full Swiss or Round Robin algorithm based on standings)
        """
        # Fetch standings to get active players
        result = await self.db.execute(
            select(TournamentStanding).where(TournamentStanding.tournament_id == tournament_id)
        )
        standings = result.scalars().all()
        players = [s.student_id for s in standings]
        
        # Shuffle for MVP random pairing
        random.shuffle(players)
        
        games = []
        for i in range(0, len(players) - 1, 2):
            game = TournamentGame(
                tournament_id=tournament_id,
                round=round_num,
                white_player_id=players[i],
                black_player_id=players[i + 1],
                result=GameResult.NOT_PLAYED.value,
            )
            self.db.add(game)
            games.append(game)
            
        await self.db.commit()
        return games

    async def reset_tournament(self, tournament_id: UUID):
        tournament = await self.get_tournament(tournament_id)
        if not tournament:
            raise ValueError("Tournament not found")
        
        # Delete all games
        result = await self.db.execute(
            select(TournamentGame).where(TournamentGame.tournament_id == tournament_id)
        )
        games = result.scalars().all()
        for g in games:
            await self.db.delete(g)
            
        # Reset standings
        result = await self.db.execute(
            select(TournamentStanding).where(TournamentStanding.tournament_id == tournament_id)
        )
        standings = result.scalars().all()
        for s in standings:
            s.points = 0.0
            s.wins = 0
            s.draws = 0
            s.losses = 0
            
        # Reset status
        tournament.status = TournamentStatus.DRAFT.value
        await self.db.commit()
