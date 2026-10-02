import { useState } from 'react';
import { tournamentService } from '../services/tournaments';
import toast from 'react-hot-toast';

export default function CreateTournamentModal({ 
  onClose, 
  onSuccess 
}: { 
  onClose: () => void, 
  onSuccess: () => void 
}) {
  const [formData, setFormData] = useState({
    name: '',
    description: '',
    format: 'swiss',
    max_rounds: 5,
    time_control: '10+5',
  });
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    try {
      await tournamentService.createTournament(formData);
      toast.success('Tournament created successfully');
      onSuccess();
    } catch (err: any) {
      toast.error(err.response?.data?.detail || 'Failed to create tournament');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm p-4">
      <div className="bg-slate-900 border border-slate-700 rounded-2xl w-full max-w-md overflow-hidden shadow-2xl relative">
        <button 
          onClick={onClose}
          className="absolute top-4 right-4 text-slate-500 hover:text-white transition-colors"
        >
          ✕
        </button>
        
        <div className="p-6">
          <h3 className="text-xl font-bold text-white mb-6">Create Tournament</h3>
          
          <form onSubmit={handleSubmit} className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-slate-400 mb-1">Name</label>
              <input
                required
                type="text"
                value={formData.name}
                onChange={e => setFormData({...formData, name: e.target.value})}
                className="w-full bg-slate-800 border border-slate-700 rounded-xl px-4 py-2 text-white focus:outline-hidden focus:border-blue-500 transition-colors"
                placeholder="e.g. Monthly Blitz Open"
              />
            </div>
            
            <div>
              <label className="block text-sm font-medium text-slate-400 mb-1">Description</label>
              <textarea
                value={formData.description}
                onChange={e => setFormData({...formData, description: e.target.value})}
                className="w-full bg-slate-800 border border-slate-700 rounded-xl px-4 py-2 text-white focus:outline-hidden focus:border-blue-500 transition-colors"
                placeholder="Optional description"
                rows={3}
              />
            </div>
            
            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-medium text-slate-400 mb-1">Format</label>
                <select
                  value={formData.format}
                  onChange={e => setFormData({...formData, format: e.target.value})}
                  className="w-full bg-slate-800 border border-slate-700 rounded-xl px-4 py-2 text-white focus:outline-hidden focus:border-blue-500 transition-colors"
                >
                  <option value="swiss">Swiss</option>
                  <option value="round_robin">Round Robin</option>
                </select>
              </div>
              
              <div>
                <label className="block text-sm font-medium text-slate-400 mb-1">Max Rounds</label>
                <input
                  type="number"
                  min="1"
                  max="20"
                  value={formData.max_rounds}
                  onChange={e => setFormData({...formData, max_rounds: parseInt(e.target.value)})}
                  className="w-full bg-slate-800 border border-slate-700 rounded-xl px-4 py-2 text-white focus:outline-hidden focus:border-blue-500 transition-colors"
                />
              </div>
            </div>
            
            <div>
              <label className="block text-sm font-medium text-slate-400 mb-1">Time Control</label>
              <input
                required
                type="text"
                value={formData.time_control}
                onChange={e => setFormData({...formData, time_control: e.target.value})}
                className="w-full bg-slate-800 border border-slate-700 rounded-xl px-4 py-2 text-white focus:outline-hidden focus:border-blue-500 transition-colors"
                placeholder="e.g. 10+5"
              />
            </div>
            
            <button
              disabled={loading}
              type="submit"
              className="w-full mt-6 py-2.5 bg-blue-600 hover:bg-blue-500 disabled:opacity-50 text-white rounded-xl font-medium transition-colors shadow-lg shadow-blue-500/20"
            >
              {loading ? 'Creating...' : 'Create Tournament'}
            </button>
          </form>
        </div>
      </div>
    </div>
  );
}
