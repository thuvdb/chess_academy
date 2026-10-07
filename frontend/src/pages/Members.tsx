import React, { useState, useEffect } from 'react';
import { toast } from 'react-hot-toast';
import api from '../lib/api';
import { Search, Users, Shield, User } from 'lucide-react';
import { useAuthStore } from '../store/authStore';

interface Member {
  id: string;
  email: string;
  full_name: string;
  username: string | null;
  role: string;
  center_id: string | null;
  avatar_url: string | null;
}

const Members = () => {
  const { user } = useAuthStore();
  const [members, setMembers] = useState<Member[]>([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState('');

  const fetchMembers = async (searchQuery = '') => {
    try {
      setLoading(true);
      const { data } = await api.get(`/users/members?search=${searchQuery}&limit=100`);
      setMembers(data);
    } catch (error) {
      toast.error('Failed to load members');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchMembers();
  }, []);

  const handleSearch = (e: React.FormEvent) => {
    e.preventDefault();
    fetchMembers(search);
  };

  if (user?.role !== 'super_admin' && user?.role !== 'admin') {
    return (
      <div className="flex items-center justify-center h-64">
        <p className="text-slate-400">You do not have permission to view this page.</p>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4">
        <div>
          <h1 className="text-2xl font-bold text-white flex items-center gap-2">
            <Users className="w-6 h-6 text-blue-500" />
            Members Directory
          </h1>
          <p className="text-slate-400 mt-1">
            {user.role === 'super_admin' 
              ? 'View all registered members across all centers.'
              : 'View all members registered to your center.'}
          </p>
        </div>

        <form onSubmit={handleSearch} className="relative w-full sm:w-72">
          <input 
            type="text"
            placeholder="Search name, username, email..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="w-full bg-slate-800 border border-slate-700 rounded-lg pl-10 pr-4 py-2 text-white focus:outline-none focus:border-blue-500"
          />
          <Search className="w-5 h-5 text-slate-400 absolute left-3 top-2.5" />
        </form>
      </div>

      <div className="bg-slate-800 rounded-xl border border-slate-700 overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full text-left text-sm text-slate-300">
            <thead className="bg-slate-900/50 text-slate-400 text-xs uppercase border-b border-slate-700">
              <tr>
                <th className="px-6 py-4 font-medium">Member</th>
                <th className="px-6 py-4 font-medium">Contact</th>
                <th className="px-6 py-4 font-medium">Role</th>
                {user.role === 'super_admin' && <th className="px-6 py-4 font-medium">Center ID</th>}
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-700/50">
              {loading ? (
                <tr>
                  <td colSpan={5} className="px-6 py-8 text-center text-slate-400">Loading members...</td>
                </tr>
              ) : members.length === 0 ? (
                <tr>
                  <td colSpan={5} className="px-6 py-8 text-center text-slate-400">No members found.</td>
                </tr>
              ) : (
                members.map((member) => (
                  <tr key={member.id} className="hover:bg-slate-700/30 transition-colors">
                    <td className="px-6 py-4">
                      <div className="flex items-center gap-3">
                        {member.avatar_url ? (
                          <img src={member.avatar_url} alt="Avatar" className="w-10 h-10 rounded-full object-cover" />
                        ) : (
                          <div className="w-10 h-10 rounded-full bg-slate-700 flex items-center justify-center">
                            <User className="w-5 h-5 text-slate-400" />
                          </div>
                        )}
                        <div>
                          <div className="font-medium text-white">{member.full_name}</div>
                          {member.username && <div className="text-xs text-slate-400">@{member.username}</div>}
                        </div>
                      </div>
                    </td>
                    <td className="px-6 py-4">
                      <div className="text-slate-300">{member.email}</div>
                    </td>
                    <td className="px-6 py-4">
                      <span className={`inline-flex items-center gap-1 px-2.5 py-1 rounded-full text-xs font-medium
                        ${member.role === 'super_admin' ? 'bg-purple-500/10 text-purple-400 border border-purple-500/20' : 
                          member.role === 'admin' ? 'bg-red-500/10 text-red-400 border border-red-500/20' : 
                          member.role === 'teacher' ? 'bg-blue-500/10 text-blue-400 border border-blue-500/20' :
                          'bg-slate-500/10 text-slate-400 border border-slate-500/20'}`}>
                        {member.role === 'super_admin' || member.role === 'admin' ? <Shield className="w-3 h-3" /> : null}
                        {member.role}
                      </span>
                    </td>
                    {user.role === 'super_admin' && (
                      <td className="px-6 py-4">
                        <span className="text-xs text-slate-500 font-mono">{member.center_id?.split('-')[0] || 'N/A'}...</span>
                      </td>
                    )}
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
};

export default Members;
