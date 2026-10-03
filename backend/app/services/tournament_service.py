import math
import random
from typing import List, Optional
from uuid import UUID
from datetime import datetime, timezone

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
        Swiss pairing: pair players with similar scores.
        Round 1 = random. Round 2+ = sort by points and pair adjacent.
        """
        result = await self.db.execute(
            select(TournamentStanding)
            .where(TournamentStanding.tournament_id == tournament_id)
            .order_by(TournamentStanding.points.desc())
        )
        standings = result.scalars().all()
        players = [s.student_id for s in standings]

        if round_num == 1:
            random.shuffle(players)
        # else: already sorted by points desc (Swiss pairing)

        # Check for existing games in this round to avoid duplicates
        existing = await self.db.execute(
            select(TournamentGame).where(
                TournamentGame.tournament_id == tournament_id,
                TournamentGame.round == round_num,
            )
        )
        if existing.scalars().first():
            return []  # Round already generated

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

    async def record_game_result(self, game_id: UUID, chess_result: str):
        """
        Save game result and update standings.
        chess_result: '1-0' (white wins), '0-1' (black wins), '1/2-1/2' (draw)
        """
        result = await self.db.execute(
            select(TournamentGame).where(TournamentGame.id == game_id)
        )
        game = result.scalars().first()
        if not game:
            return
        if game.result != GameResult.NOT_PLAYED.value:
            return  # Already recorded

        # Map chess result to enum
        if chess_result == "1-0":
            game.result = GameResult.WHITE_WINS.value
        elif chess_result == "0-1":
            game.result = GameResult.BLACK_WINS.value
        else:
            game.result = GameResult.DRAW.value
        game.played_at = datetime.now(timezone.utc)

        # Update white player standing
        white_standing = await self._get_standing(game.tournament_id, game.white_player_id)
        black_standing = await self._get_standing(game.tournament_id, game.black_player_id)

        if chess_result == "1-0":
            if white_standing:
                white_standing.points = float(white_standing.points) + 1.0
                white_standing.wins += 1
            if black_standing:
                black_standing.losses += 1
        elif chess_result == "0-1":
            if black_standing:
                black_standing.points = float(black_standing.points) + 1.0
                black_standing.wins += 1
            if white_standing:
                white_standing.losses += 1
        else:  # draw
            if white_standing:
                white_standing.points = float(white_standing.points) + 0.5
                white_standing.draws += 1
            if black_standing:
                black_standing.points = float(black_standing.points) + 0.5
                black_standing.draws += 1

        await self.db.commit()

        # Check if round is complete and advance
        await self.check_and_advance_round(game.tournament_id, game.round)

    async def _get_standing(self, tournament_id: UUID, student_id: UUID):
        result = await self.db.execute(
            select(TournamentStanding).where(
                TournamentStanding.tournament_id == tournament_id,
                TournamentStanding.student_id == student_id,
            )
        )
        return result.scalars().first()

    async def check_and_advance_round(self, tournament_id: UUID, current_round: int):
        """If all games in current round are finished, generate next round or complete tournament."""
        tournament = await self.get_tournament(tournament_id)
        if not tournament:
            return

        # Check if all games in current round are done
        result = await self.db.execute(
            select(TournamentGame).where(
                TournamentGame.tournament_id == tournament_id,
                TournamentGame.round == current_round,
            )
        )
        games = result.scalars().all()
        all_done = all(g.result != GameResult.NOT_PLAYED.value for g in games)

        if not all_done:
            return

        # Check if we've reached max_rounds
        if current_round >= tournament.max_rounds:
            tournament.status = TournamentStatus.COMPLETED.value
            await self.db.commit()
            return

        # Generate next round
        next_round = current_round + 1
        await self.generate_pairings(tournament_id, round_num=next_round)

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
