import api from '../lib/api';

export interface Tournament {
  id: string;
  name: string;
  description?: string;
  format: string;
  max_rounds: number;
  time_control?: string;
  status: string;
  created_at: string;
}

export interface TournamentStanding {
  id: string;
  student_id: string;
  points: number;
  wins: number;
  draws: number;
  losses: number;
  buchholz?: number;
}

export interface TournamentGame {
  id: string;
  tournament_id: string;
  round: number;
  white_player_id: string;
  black_player_id: string;
  result: string;
  pgn?: string;
  time_control?: string;
}

export const tournamentService = {
  async getTournaments() {
    const response = await api.get('/tournaments/');
    return response.data;
  },

  async createTournament(data: Partial<Tournament>) {
    const response = await api.post('/tournaments/', data);
    return response.data;
  },

  async getTournament(id: string) {
    const response = await api.get(`/tournaments/${id}`);
    return response.data;
  },

  async registerPlayer(id: string, student_id: string) {
    const response = await api.post(`/tournaments/${id}/register`, { student_id });
    return response.data;
  },

  async startTournament(id: string) {
    const response = await api.post(`/tournaments/${id}/start`);
    return response.data;
  },

  async resetTournament(id: string) {
    const response = await api.post(`/tournaments/${id}/reset`);
    return response.data;
  },
  
  async getStandings(id: string) {
    const response = await api.get(`/tournaments/${id}/standings`);
    return response.data;
  },
  
  async getGames(id: string, round?: number) {
    const response = await api.get(`/tournaments/${id}/games${round ? `?round_num=${round}` : ''}`);
    return response.data;
  }
};
