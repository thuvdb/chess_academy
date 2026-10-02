import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuthStore } from '../store/authStore';
import { tournamentService } from '../services/tournaments';
import type { Tournament } from '../services/tournaments';
import toast from 'react-hot-toast';
import CreateTournamentModal from '../components/CreateTournamentModal';

export default function Tournaments() {
  const navigate = useNavigate();
  const { user } = useAuthStore();
  const [tournaments, setTournaments] = useState<Tournament[]>([]);
  const [loading, setLoading] = useState(true);
  const [showModal, setShowModal] = useState(false);
  
  const isAdminOrTeacher = user?.role === 'super_admin' || user?.role === 'admin' || user?.role === 'center_admin' || user?.role === 'teacher';

  useEffect(() => {
    fetchTournaments();
  }, []);

  const fetchTournaments = async () => {
    try {
      const data = await tournamentService.getTournaments();
      setTournaments(data);
    } catch (err) {
      toast.error('Failed to load tournaments');
    } finally {
      setLoading(false);
    }
  };

  const handleRegister = async (tournamentId: string) => {
    if (!user) return;
    try {
      await tournamentService.registerPlayer(tournamentId, user.id);
      toast.success('Successfully registered for tournament');
    } catch (err: any) {
      toast.error(err.response?.data?.detail || 'Failed to register');
    }
  };

  const handleStartTournament = async (tournamentId: string) => {
    try {
      await tournamentService.startTournament(tournamentId);
      toast.success('Tournament started successfully');
      fetchTournaments();
    } catch (err: any) {
      toast.error(err.response?.data?.detail || 'Failed to start tournament');
    }
  };

  return (
    <div className="p-6 max-w-6xl mx-auto text-slate-200">
      <div className="flex justify-between items-center mb-8">
        <div>
          <h1 className="text-3xl font-bold bg-clip-text text-transparent bg-linear-to-r from-blue-400 to-indigo-400">
            Tournaments
          </h1>
          <p className="text-slate-400 mt-2">Manage and join chess tournaments</p>
        </div>
        {isAdminOrTeacher && (
          <button 
            onClick={() => setShowModal(true)}
            className="px-4 py-2 bg-blue-600 hover:bg-blue-500 text-white rounded-xl font-medium transition-colors shadow-lg shadow-blue-500/20"
          >
            + New Tournament
          </button>
        )}
      </div>

      {loading ? (
        <div className="flex justify-center p-12">
          <div className="w-8 h-8 border-4 border-blue-500 border-t-transparent rounded-full animate-spin"></div>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {tournaments.map((t) => (
            <div key={t.id} className="bg-slate-800 border border-slate-700 rounded-2xl overflow-hidden shadow-xl p-6 flex flex-col relative group hover:border-slate-600 transition-colors">
              
              <div className="absolute top-4 right-4">
                <span className={`px-2.5 py-1 text-[10px] font-bold tracking-wider uppercase rounded-full ${
                  t.status === 'draft' ? 'bg-slate-700 text-slate-300' :
                  t.status === 'registration' ? 'bg-green-500/20 text-green-400 border border-green-500/30' :
                  t.status === 'in_progress' ? 'bg-yellow-500/20 text-yellow-400 border border-yellow-500/30' :
                  'bg-blue-500/20 text-blue-400'
                }`}>
                  {t.status}
                </span>
              </div>

              <h3 className="text-xl font-bold text-white mb-1 pr-20">{t.name}</h3>
              <p className="text-sm text-slate-400 mb-4 line-clamp-2">{t.description || 'No description provided.'}</p>
              
              <div className="space-y-2 mb-6 text-sm text-slate-300">
                <div className="flex justify-between border-b border-slate-700/50 pb-2">
                  <span className="text-slate-500">Format</span>
                  <span className="font-medium">{t.format.toUpperCase()}</span>
                </div>
                <div className="flex justify-between border-b border-slate-700/50 pb-2">
                  <span className="text-slate-500">Rounds</span>
                  <span className="font-medium">{t.max_rounds}</span>
                </div>
                <div className="flex justify-between border-b border-slate-700/50 pb-2">
                  <span className="text-slate-500">Time Control</span>
                  <span className="font-medium">{t.time_control || 'N/A'}</span>
                </div>
              </div>

              <div className="mt-auto flex gap-2">
                {!isAdminOrTeacher && t.status === 'draft' && (
                  <button 
                    onClick={() => handleRegister(t.id)}
                    className="flex-1 py-2 bg-slate-700 hover:bg-slate-600 text-white rounded-lg font-medium transition-colors"
                  >
                    Register
                  </button>
                )}
                {isAdminOrTeacher && t.status === 'draft' && (
                  <button 
                    onClick={() => handleStartTournament(t.id)}
                    className="flex-1 py-2 bg-green-600 hover:bg-green-500 text-white rounded-lg font-medium transition-colors"
                  >
                    Start Tournament
                  </button>
                )}
                <button 
                  onClick={() => navigate(`/tournaments/${t.id}`)}
                  className="flex-1 py-2 bg-blue-600 hover:bg-blue-500 text-white rounded-lg font-medium transition-colors"
                >
                  View Details
                </button>
              </div>
            </div>
          ))}
          {tournaments.length === 0 && (
            <div className="col-span-full p-12 text-center text-slate-400 border border-dashed border-slate-700 rounded-2xl">
              No tournaments available.
            </div>
          )}
        </div>
      )}

      {showModal && (
        <CreateTournamentModal 
          onClose={() => setShowModal(false)} 
          onSuccess={() => {
            setShowModal(false);
            fetchTournaments();
          }} 
        />
      )}
    </div>
  );
}
