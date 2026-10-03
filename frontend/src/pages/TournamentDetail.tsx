import { useState, useEffect } from 'react';
import { useParams, Link } from 'react-router-dom';
import { tournamentService } from '../services/tournaments';
import type { Tournament, TournamentStanding, TournamentGame } from '../services/tournaments';
import { useAuthStore } from '../store/authStore';
import toast from 'react-hot-toast';

export default function TournamentDetail() {
  const { id } = useParams<{ id: string }>();
  const { user } = useAuthStore();
  const [tournament, setTournament] = useState<Tournament | null>(null);
  const [standings, setStandings] = useState<TournamentStanding[]>([]);
  const [games, setGames] = useState<TournamentGame[]>([]);
  const [loading, setLoading] = useState(true);
  const [activeTab, setActiveTab] = useState<'standings' | 'games'>('standings');

  const isAdmin = user?.role && ['super_admin', 'admin', 'center_admin', 'teacher'].includes(user.role);

  useEffect(() => {
    if (id) fetchData();
  }, [id]);

  const fetchData = async () => {
    if (!id) return;
    try {
      setLoading(true);
      const [tData, sData, gData] = await Promise.all([
        tournamentService.getTournament(id),
        tournamentService.getStandings(id),
        tournamentService.getGames(id),
      ]);
      setTournament(tData);
      setStandings(sData);
      setGames(gData);
    } catch (err) {
      toast.error('Failed to load tournament data');
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return (
      <div className="flex justify-center p-12">
        <div className="w-8 h-8 border-4 border-blue-500 border-t-transparent rounded-full animate-spin" />
      </div>
    );
  }
  if (!tournament) {
    return <div className="p-6 text-white text-center">Tournament not found</div>;
  }

  // Group games by round
  const roundMap = games.reduce((acc, g) => {
    if (!acc[g.round]) acc[g.round] = [];
    acc[g.round].push(g);
    return acc;
  }, {} as Record<number, TournamentGame[]>);
  const rounds = Object.keys(roundMap)
    .map(Number)
    .sort((a, b) => a - b);

  // Find current active round (first round with not_played games)
  const activeRound = rounds.find(r => roundMap[r].some(g => g.result === 'not_played')) ?? rounds[rounds.length - 1];

  const resultBadge = (result: string) => {
    switch (result) {
      case 'white_wins': return <span className="text-xs font-bold text-green-400">1 – 0</span>;
      case 'black_wins': return <span className="text-xs font-bold text-green-400">0 – 1</span>;
      case 'draw': return <span className="text-xs font-bold text-yellow-400">½ – ½</span>;
      default: return <span className="text-xs font-bold text-slate-500">VS</span>;
    }
  };

  return (
    <div className="p-6 max-w-6xl mx-auto text-slate-200">
      {/* Header */}
      <div className="bg-slate-900 border border-slate-700 rounded-2xl p-8 mb-6 shadow-xl relative overflow-hidden">
        <div className="absolute top-0 right-0 w-64 h-64 bg-blue-500/10 rounded-full blur-3xl -translate-y-1/2 translate-x-1/3" />
        <div className="relative z-10">
          <Link
            to="/tournaments"
            className="text-blue-400 hover:text-blue-300 text-sm font-medium mb-4 inline-flex items-center gap-1 transition-colors"
          >
            ← Back to Tournaments
          </Link>
          <div className="flex justify-between items-start">
            <div>
              <h1 className="text-3xl font-bold text-white mb-2">{tournament.name}</h1>
              <p className="text-slate-400 max-w-2xl">{tournament.description}</p>
            </div>
            <div className="flex flex-col items-end gap-2">
              <span className={`px-4 py-1.5 text-sm font-bold tracking-wider uppercase rounded-xl ${
                tournament.status === 'draft' ? 'bg-slate-700 text-slate-300' :
                tournament.status === 'registration' ? 'bg-green-500/20 text-green-400 border border-green-500/30' :
                tournament.status === 'in_progress' ? 'bg-yellow-500/20 text-yellow-400 border border-yellow-500/30' :
                tournament.status === 'completed' ? 'bg-blue-500/20 text-blue-400 border border-blue-500/30' :
                'bg-slate-700 text-slate-300'
              }`}>
                {tournament.status === 'completed' ? '✅ COMPLETED' : tournament.status.toUpperCase().replace(/_/g, ' ')}
              </span>

              {/* Reset button — only admin on in_progress */}
              {isAdmin && tournament.status === 'in_progress' && (
                <button
                  onClick={async () => {
                    if (confirm('Are you sure? All games & standings will be reset.')) {
                      try {
                        await tournamentService.resetTournament(tournament.id);
                        toast.success('Tournament reset to draft');
                        fetchData();
                      } catch {
                        toast.error('Failed to reset tournament');
                      }
                    }
                  }}
                  className="mt-2 text-xs text-red-400 hover:text-red-300 underline font-medium"
                >
                  Cancel / Reset Tournament
                </button>
              )}
            </div>
          </div>
          <div className="flex gap-6 mt-6 text-sm text-slate-300">
            <div>
              <span className="text-slate-500 block text-xs uppercase tracking-wider mb-1">Format</span>
              <span className="font-semibold">{tournament.format}</span>
            </div>
            <div>
              <span className="text-slate-500 block text-xs uppercase tracking-wider mb-1">Rounds</span>
              <span className="font-semibold">{tournament.max_rounds}</span>
            </div>
            <div>
              <span className="text-slate-500 block text-xs uppercase tracking-wider mb-1">Time Control</span>
              <span className="font-semibold">{tournament.time_control}</span>
            </div>
            {activeRound && (
              <div>
                <span className="text-slate-500 block text-xs uppercase tracking-wider mb-1">Current Round</span>
                <span className="font-semibold text-blue-400">{activeRound} / {tournament.max_rounds}</span>
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Tabs */}
      <div className="flex gap-2 mb-6 border-b border-slate-800 pb-px">
        <button
          onClick={() => setActiveTab('standings')}
          className={`px-6 py-2.5 font-medium text-sm rounded-t-lg transition-colors ${
            activeTab === 'standings'
              ? 'bg-slate-800 text-blue-400 border-t border-x border-slate-700'
              : 'text-slate-400 hover:text-slate-200'
          }`}
        >
          Standings
        </button>
        <button
          onClick={() => setActiveTab('games')}
          className={`px-6 py-2.5 font-medium text-sm rounded-t-lg transition-colors ${
            activeTab === 'games'
              ? 'bg-slate-800 text-blue-400 border-t border-x border-slate-700'
              : 'text-slate-400 hover:text-slate-200'
          }`}
        >
          Games & Pairings
        </button>
      </div>

      {/* Tab Content */}
      <div className="bg-slate-800 border border-slate-700 rounded-b-2xl rounded-tr-2xl overflow-hidden shadow-xl min-h-[400px]">
        {/* Standings */}
        {activeTab === 'standings' && (
          <table className="w-full text-left text-sm">
            <thead className="bg-slate-900/50 text-slate-400 uppercase text-xs font-semibold">
              <tr>
                <th className="px-6 py-4 w-16 text-center">Rank</th>
                <th className="px-6 py-4">Player</th>
                <th className="px-6 py-4 text-center">Points</th>
                <th className="px-6 py-4 text-center">W/D/L</th>
                <th className="px-6 py-4 text-center">Buchholz</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-700">
              {standings.map((s, idx) => (
                <tr key={s.id} className="hover:bg-slate-700/30 transition-colors">
                  <td className="px-6 py-4 font-bold text-center text-slate-300">
                    {idx === 0 && standings.length > 1 ? '🥇' : idx === 1 ? '🥈' : idx === 2 ? '🥉' : idx + 1}
                  </td>
                  <td className="px-6 py-4">
                    <div className="font-semibold text-white">
                      {s.student_name || `Player ${s.student_id.substring(0, 8)}…`}
                    </div>
                  </td>
                  <td className="px-6 py-4 text-center font-bold text-blue-400">{s.points}</td>
                  <td className="px-6 py-4 text-center text-slate-400">
                    <span className="text-green-400">{s.wins}</span> / <span className="text-yellow-400">{s.draws}</span> / <span className="text-red-400">{s.losses}</span>
                  </td>
                  <td className="px-6 py-4 text-center text-slate-400">{s.buchholz || '-'}</td>
                </tr>
              ))}
              {standings.length === 0 && (
                <tr>
                  <td colSpan={5} className="px-6 py-12 text-center text-slate-400">
                    No players registered yet.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        )}

        {/* Games & Pairings */}
        {activeTab === 'games' && (
          <div className="p-6">
            {rounds.length === 0 ? (
              <div className="py-12 text-center text-slate-400">No games generated yet.</div>
            ) : (
              rounds.map(roundNum => (
                <div key={roundNum} className="mb-8 last:mb-0">
                  <div className="flex items-center gap-3 mb-4">
                    <h3 className="text-lg font-bold text-white">Round {roundNum}</h3>
                    {roundMap[roundNum].every(g => g.result !== 'not_played') && (
                      <span className="text-xs bg-green-500/20 text-green-400 px-2 py-0.5 rounded-full">✓ Complete</span>
                    )}
                    {roundMap[roundNum].some(g => g.result === 'not_played') && (
                      <span className="text-xs bg-yellow-500/20 text-yellow-400 px-2 py-0.5 rounded-full animate-pulse">● In Progress</span>
                    )}
                  </div>
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    {roundMap[roundNum].map(g => {
                      const whiteName = g.white_player_name || `${g.white_player_id.substring(0, 8)}…`;
                      const blackName = g.black_player_name || `${g.black_player_id.substring(0, 8)}…`;

                      return (
                        <div
                          key={g.id}
                          className="bg-slate-900 border border-slate-700 rounded-xl p-4 flex items-center justify-between hover:border-slate-500 transition-colors group"
                        >
                          <div className="flex-1">
                            <div className="flex items-center gap-3 mb-2">
                              <div className="w-4 h-4 rounded-full bg-white shadow-xs shrink-0" />
                              <span className="text-sm text-slate-200 font-medium">{whiteName}</span>
                              {g.result === 'white_wins' && <span className="text-xs text-green-400 font-bold">WIN</span>}
                            </div>
                            <div className="flex items-center gap-3">
                              <div className="w-4 h-4 rounded-full bg-slate-900 border border-slate-600 shadow-xs shrink-0" />
                              <span className="text-sm text-slate-200 font-medium">{blackName}</span>
                              {g.result === 'black_wins' && <span className="text-xs text-green-400 font-bold">WIN</span>}
                            </div>
                          </div>

                          <div className="flex flex-col items-center gap-2 border-l border-slate-700 pl-4 ml-4 min-w-[80px]">
                            {resultBadge(g.result)}

                            {/* Play Now — only for actual players (not admin), and only for not_played games */}
                            {g.result === 'not_played' && !isAdmin && (
                              <Link
                                to={`/tournaments/${tournament.id}/game/${g.id}`}
                                className="text-xs font-medium text-blue-400 hover:text-blue-300 transition-opacity flex items-center gap-1"
                              >
                                Play Now →
                              </Link>
                            )}

                            {/* Admin: Spectate link */}
                            {g.result === 'not_played' && isAdmin && (
                              <Link
                                to={`/tournaments/${tournament.id}/game/${g.id}`}
                                className="text-xs font-medium text-slate-400 hover:text-slate-300 transition-opacity flex items-center gap-1"
                              >
                                👁 Spectate
                              </Link>
                            )}

                            {g.result !== 'not_played' && (
                              <Link
                                to={`/tournaments/${tournament.id}/game/${g.id}`}
                                className="text-xs text-slate-500 hover:text-slate-300"
                              >
                                View
                              </Link>
                            )}
                          </div>
                        </div>
                      );
                    })}
                  </div>
                </div>
              ))
            )}
          </div>
        )}
      </div>
    </div>
  );
}
