import { useState, useEffect } from 'react';
import { useParams, Link } from 'react-router-dom';
import { tournamentService } from '../services/tournaments';
import type { Tournament, TournamentStanding, TournamentGame } from '../services/tournaments';
import toast from 'react-hot-toast';

export default function TournamentDetail() {
  const { id } = useParams<{ id: string }>();
  const [tournament, setTournament] = useState<Tournament | null>(null);
  const [standings, setStandings] = useState<TournamentStanding[]>([]);
  const [games, setGames] = useState<TournamentGame[]>([]);
  const [loading, setLoading] = useState(true);
  const [activeTab, setActiveTab] = useState<'standings' | 'games'>('standings');

  useEffect(() => {
    if (id) {
      fetchData();
    }
  }, [id]);

  const fetchData = async () => {
    if (!id) return;
    try {
      setLoading(true);
      const [tData, sData, gData] = await Promise.all([
        tournamentService.getTournament(id),
        tournamentService.getStandings(id),
        tournamentService.getGames(id)
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
        <div className="w-8 h-8 border-4 border-blue-500 border-t-transparent rounded-full animate-spin"></div>
      </div>
    );
  }

  if (!tournament) {
    return <div className="p-6 text-white text-center">Tournament not found</div>;
  }

  return (
    <div className="p-6 max-w-6xl mx-auto text-slate-200">
      {/* Header */}
      <div className="bg-slate-900 border border-slate-700 rounded-2xl p-8 mb-6 shadow-xl relative overflow-hidden">
        <div className="absolute top-0 right-0 w-64 h-64 bg-blue-500/10 rounded-full blur-3xl -translate-y-1/2 translate-x-1/3"></div>
        <div className="relative z-10">
          <Link to="/tournaments" className="text-blue-400 hover:text-blue-300 text-sm font-medium mb-4 inline-flex items-center gap-1 transition-colors">
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
                'bg-blue-500/20 text-blue-400'
              }`}>
                {tournament.status}
              </span>
              
              {tournament.status === 'in_progress' && (
                <button
                  onClick={async () => {
                    if (confirm('Are you sure you want to cancel this tournament? All games and standings will be reset!')) {
                      try {
                        await tournamentService.resetTournament(tournament.id);
                        toast.success('Tournament has been reset to draft status');
                        fetchData();
                      } catch (e) {
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
            <div><span className="text-slate-500 block text-xs uppercase tracking-wider mb-1">Format</span><span className="font-semibold">{tournament.format}</span></div>
            <div><span className="text-slate-500 block text-xs uppercase tracking-wider mb-1">Rounds</span><span className="font-semibold">{tournament.max_rounds}</span></div>
            <div><span className="text-slate-500 block text-xs uppercase tracking-wider mb-1">Time Control</span><span className="font-semibold">{tournament.time_control}</span></div>
          </div>
        </div>
      </div>

      {/* Tabs */}
      <div className="flex gap-2 mb-6 border-b border-slate-800 pb-px">
        <button
          onClick={() => setActiveTab('standings')}
          className={`px-6 py-2.5 font-medium text-sm rounded-t-lg transition-colors ${activeTab === 'standings' ? 'bg-slate-800 text-blue-400 border-t border-x border-slate-700' : 'text-slate-400 hover:text-slate-200'}`}
        >
          Standings
        </button>
        <button
          onClick={() => setActiveTab('games')}
          className={`px-6 py-2.5 font-medium text-sm rounded-t-lg transition-colors ${activeTab === 'games' ? 'bg-slate-800 text-blue-400 border-t border-x border-slate-700' : 'text-slate-400 hover:text-slate-200'}`}
        >
          Games & Pairings
        </button>
      </div>

      {/* Tab Content */}
      <div className="bg-slate-800 border border-slate-700 rounded-b-2xl rounded-tr-2xl overflow-hidden shadow-xl min-h-[400px]">
        {activeTab === 'standings' && (
          <table className="w-full text-left text-sm">
            <thead className="bg-slate-900/50 text-slate-400 uppercase text-xs font-semibold">
              <tr>
                <th className="px-6 py-4 w-16 text-center">Rank</th>
                <th className="px-6 py-4">Player ID (Temp)</th>
                <th className="px-6 py-4 text-center">Points</th>
                <th className="px-6 py-4 text-center">W/D/L</th>
                <th className="px-6 py-4 text-center">Buchholz</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-700">
              {standings.map((s, idx) => (
                <tr key={s.id} className="hover:bg-slate-700/30 transition-colors">
                  <td className="px-6 py-4 font-bold text-center text-slate-300">{idx + 1}</td>
                  <td className="px-6 py-4 font-mono text-xs text-slate-400">{s.student_id.substring(0, 13)}...</td>
                  <td className="px-6 py-4 text-center font-bold text-blue-400">{s.points}</td>
                  <td className="px-6 py-4 text-center text-slate-400">{s.wins} / {s.draws} / {s.losses}</td>
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

        {activeTab === 'games' && (
          <div className="p-6 grid grid-cols-1 md:grid-cols-2 gap-4">
            {games.map(g => (
              <div key={g.id} className="bg-slate-900 border border-slate-700 rounded-xl p-4 flex items-center justify-between hover:border-slate-500 transition-colors group">
                <div className="flex-1">
                  <div className="text-xs text-slate-500 mb-2 font-semibold tracking-wider">ROUND {g.round}</div>
                  <div className="flex items-center gap-3">
                    <div className="w-4 h-4 rounded-full bg-white shadow-xs"></div>
                    <span className="font-mono text-xs text-slate-300">{g.white_player_id.substring(0, 8)}</span>
                  </div>
                  <div className="flex items-center gap-3 mt-2">
                    <div className="w-4 h-4 rounded-full bg-slate-900 border border-slate-600 shadow-xs"></div>
                    <span className="font-mono text-xs text-slate-300">{g.black_player_id.substring(0, 8)}</span>
                  </div>
                </div>
                
                <div className="flex flex-col items-end gap-3 border-l border-slate-700 pl-4 ml-4">
                  <span className={`px-2 py-1 text-xs font-bold rounded-lg ${
                    g.result === 'not_played' ? 'bg-slate-800 text-slate-400' : 
                    'bg-green-500/20 text-green-400'
                  }`}>
                    {g.result === 'not_played' ? 'VS' : g.result.replace('_', ' ').toUpperCase()}
                  </span>
                  
                  {g.result === 'not_played' && (
                    <Link to={`/tournaments/${tournament.id}/game/${g.id}`} className="text-xs font-medium text-blue-400 hover:text-blue-300 opacity-0 group-hover:opacity-100 transition-opacity flex items-center gap-1">
                      Play Now →
                    </Link>
                  )}
                  {g.result !== 'not_played' && (
                    <button className="text-xs font-medium text-slate-400 hover:text-white transition-colors">
                      View PGN
                    </button>
                  )}
                </div>
              </div>
            ))}
            {games.length === 0 && (
              <div className="col-span-full py-12 text-center text-slate-400">
                No games generated yet.
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
