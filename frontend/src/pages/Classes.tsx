import { useState, useEffect, useCallback } from 'react';
import { Link } from 'react-router-dom';
import { Plus, Search, Filter, RefreshCw, BookOpen, Users, ChevronRight } from 'lucide-react';
import { getClasses, deleteClass, updateClass, type ClassItem } from '../lib/classApi';
import ClassForm from '../components/ClassForm';
import toast from 'react-hot-toast';
import { useAuthStore } from '../store/authStore';

const LEVELS = ['beginner', 'intermediate', 'advanced', 'tournament'];
const LEVEL_COLORS: Record<string, string> = {
  beginner: 'bg-green-500/15 text-green-400 border border-green-500/30',
  intermediate: 'bg-blue-500/15 text-blue-400 border border-blue-500/30',
  advanced: 'bg-purple-500/15 text-purple-400 border border-purple-500/30',
  tournament: 'bg-amber-500/15 text-amber-400 border border-amber-500/30',
};

export default function Classes() {
  const { user } = useAuthStore();
  const [classes, setClasses] = useState<ClassItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState('');
  const [levelFilter, setLevelFilter] = useState('');
  const [showForm, setShowForm] = useState(false);
  const [editingClass, setEditingClass] = useState<ClassItem | null>(null);

  const fetchClasses = useCallback(async () => {
    setLoading(true);
    try {
      const params: Record<string, unknown> = { limit: 100 };
      if (search) params.search = search;
      if (levelFilter) params.level = levelFilter;
      const { data } = await getClasses(params);
      setClasses(data);
    } catch {
      toast.error('Failed to load classes');
    } finally {
      setLoading(false);
    }
  }, [search, levelFilter]);

  useEffect(() => { fetchClasses(); }, [fetchClasses]);

  const handleDeactivate = async (cls: ClassItem) => {
    if (!confirm(`Deactivate class "${cls.name}"?`)) return;
    try {
      await updateClass(cls.id, { is_active: false });
      toast.success('Class deactivated');
      fetchClasses();
    } catch (err: any) {
      toast.error(err.response?.data?.detail || 'Failed to deactivate class');
    }
  };

  const handleActivate = async (cls: ClassItem) => {
    if (!confirm(`Reactivate class "${cls.name}"?`)) return;
    try {
      await updateClass(cls.id, { is_active: true });
      toast.success('Class activated');
      fetchClasses();
    } catch (err: any) {
      toast.error(err.response?.data?.detail || 'Failed to activate class');
    }
  };

  const handleHardDelete = async (cls: ClassItem) => {
    if (!confirm(`Permanently delete class "${cls.name}"? This action cannot be undone.`)) return;
    try {
      await deleteClass(cls.id);
      toast.success('Class deleted permanently');
      fetchClasses();
    } catch (err: any) {
      toast.error(err.response?.data?.detail || 'Failed to delete class');
    }
  };

  const handleFormClose = (refresh?: boolean) => {
    setShowForm(false);
    setEditingClass(null);
    if (refresh) fetchClasses();
  };

  return (
    <div className="p-8">
      {/* Header */}
      <div className="flex items-center justify-between mb-8">
        <div>
          <h1 className="text-2xl font-bold text-white">Classes</h1>
          <p className="text-slate-400 text-sm mt-1">Manage all chess classes and enrollments</p>
        </div>
        {user?.role !== 'student' && (
          <button
            onClick={() => setShowForm(true)}
            className="flex items-center gap-2 bg-amber-500 hover:bg-amber-400 text-slate-900 font-semibold px-4 py-2.5 rounded-xl transition-all shadow-lg shadow-amber-500/25 hover:shadow-amber-500/40"
          >
            <Plus className="w-4 h-4" />
            New Class
          </button>
        )}
      </div>

      {/* Filters */}
      <div className="flex gap-3 mb-6">
        <div className="relative flex-1 max-w-xs">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400" />
          <input
            type="text"
            placeholder="Search classes..."
            value={search}
            onChange={e => setSearch(e.target.value)}
            className="w-full bg-slate-800 border border-slate-700 text-white placeholder-slate-500 rounded-xl pl-9 pr-4 py-2.5 text-sm focus:outline-none focus:border-amber-500 transition-colors"
          />
        </div>
        <div className="relative">
          <Filter className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400" />
          <select
            value={levelFilter}
            onChange={e => setLevelFilter(e.target.value)}
            className="bg-slate-800 border border-slate-700 text-white rounded-xl pl-9 pr-8 py-2.5 text-sm focus:outline-none focus:border-amber-500 transition-colors appearance-none cursor-pointer"
          >
            <option value="">All Levels</option>
            {LEVELS.map(l => (
              <option key={l} value={l}>{l.charAt(0).toUpperCase() + l.slice(1)}</option>
            ))}
          </select>
        </div>
        <button
          onClick={fetchClasses}
          className="p-2.5 bg-slate-800 border border-slate-700 rounded-xl text-slate-400 hover:text-white hover:border-slate-600 transition-all"
          title="Refresh"
        >
          <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} />
        </button>
      </div>

      {/* Stats Bar */}
      <div className="grid grid-cols-3 gap-4 mb-6">
        {[
          { label: 'Total Classes', value: classes.length, icon: BookOpen, color: 'text-blue-400' },
          { label: 'Active Classes', value: classes.filter(c => c.is_active).length, icon: BookOpen, color: 'text-green-400' },
          { label: 'Total Enrolled', value: classes.reduce((s, c) => s + c.current_students, 0), icon: Users, color: 'text-amber-400' },
        ].map(({ label, value, icon: Icon, color }) => (
          <div key={label} className="bg-slate-800/50 border border-slate-700/50 rounded-xl p-4 flex items-center gap-4">
            <div className={`${color} p-2 bg-slate-800 rounded-lg`}>
              <Icon className="w-5 h-5" />
            </div>
            <div>
              <p className="text-slate-400 text-xs">{label}</p>
              <p className="text-white text-xl font-bold">{value}</p>
            </div>
          </div>
        ))}
      </div>

      {/* Table */}
      {loading ? (
        <div className="flex items-center justify-center h-48 text-slate-400">
          <RefreshCw className="w-6 h-6 animate-spin mr-3" /> Loading...
        </div>
      ) : classes.length === 0 ? (
        <div className="text-center py-16 text-slate-500">
          <BookOpen className="w-12 h-12 mx-auto mb-3 opacity-30" />
          <p className="text-lg font-medium">No classes found</p>
          <p className="text-sm mt-1">Create your first class to get started</p>
        </div>
      ) : (
        <div className="bg-slate-800/50 border border-slate-700/50 rounded-2xl overflow-hidden">
          <table className="w-full">
            <thead>
              <tr className="border-b border-slate-700">
                <th className="text-left px-6 py-4 text-slate-400 text-xs font-semibold uppercase tracking-wider">Class</th>
                <th className="text-left px-6 py-4 text-slate-400 text-xs font-semibold uppercase tracking-wider">Level</th>
                <th className="text-left px-6 py-4 text-slate-400 text-xs font-semibold uppercase tracking-wider">Teacher</th>
                <th className="text-left px-6 py-4 text-slate-400 text-xs font-semibold uppercase tracking-wider">Students</th>
                <th className="text-left px-6 py-4 text-slate-400 text-xs font-semibold uppercase tracking-wider">Status</th>
                <th className="text-right px-6 py-4 text-slate-400 text-xs font-semibold uppercase tracking-wider">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-700/50">
              {classes.map(cls => (
                <tr key={cls.id} className="hover:bg-slate-700/30 transition-colors group">
                  <td className="px-6 py-4">
                    <Link to={`/classes/${cls.id}`} className="text-white font-medium hover:text-amber-400 transition-colors flex items-center gap-1">
                      {cls.name}
                      <ChevronRight className="w-3.5 h-3.5 opacity-0 group-hover:opacity-100 transition-opacity" />
                    </Link>
                  </td>
                  <td className="px-6 py-4">
                    {cls.level ? (
                      <span className={`px-2.5 py-1 rounded-full text-xs font-medium ${LEVEL_COLORS[cls.level] ?? 'bg-slate-700 text-slate-300'}`}>
                        {cls.level.charAt(0).toUpperCase() + cls.level.slice(1)}
                      </span>
                    ) : (
                      <span className="text-slate-500 text-sm">—</span>
                    )}
                  </td>
                  <td className="px-6 py-4 text-slate-300 text-sm">{cls.teacher_name ?? <span className="text-slate-500">Unassigned</span>}</td>
                  <td className="px-6 py-4">
                    <div className="flex items-center gap-2">
                      <div className="flex-1 max-w-20 bg-slate-700 rounded-full h-1.5">
                        <div
                          className="bg-amber-500 h-1.5 rounded-full transition-all"
                          style={{ width: `${Math.min(100, (cls.current_students / cls.max_students) * 100)}%` }}
                        />
                      </div>
                      <span className="text-slate-300 text-sm">{cls.current_students}/{cls.max_students}</span>
                    </div>
                  </td>
                  <td className="px-6 py-4">
                    <span className={`px-2 py-1 rounded-full text-xs font-medium ${cls.is_active ? 'bg-green-500/15 text-green-400 border border-green-500/30' : 'bg-slate-700 text-slate-400 border border-slate-600'}`}>
                      {cls.is_active ? 'Active' : 'Inactive'}
                    </span>
                  </td>
                  <td className="px-6 py-4 text-right">
                    <div className="flex items-center justify-end gap-2">
                      <Link
                        to={`/classes/${cls.id}`}
                        className="text-xs text-slate-400 hover:text-blue-400 px-3 py-1.5 rounded-lg hover:bg-blue-500/10 transition-all"
                      >
                        View
                      </Link>
                      {user?.role !== 'student' && (
                        <>
                          <button
                            onClick={() => { setEditingClass(cls); setShowForm(true); }}
                            className="text-xs text-slate-400 hover:text-amber-400 px-3 py-1.5 rounded-lg hover:bg-amber-500/10 transition-all"
                          >
                            Edit
                          </button>
                          {cls.is_active && (user?.role === 'admin' || user?.role === 'super_admin' || user?.role === 'center_admin' || (user?.role === 'teacher' && cls.teacher_id === user.id)) && (
                            <button
                              onClick={() => handleDeactivate(cls)}
                              className="text-xs text-slate-400 hover:text-amber-400 px-3 py-1.5 rounded-lg hover:bg-amber-500/10 transition-all"
                            >
                              Deactivate
                            </button>
                          )}
                          {!cls.is_active && (user?.role === 'admin' || user?.role === 'super_admin' || user?.role === 'center_admin' || (user?.role === 'teacher' && cls.teacher_id === user.id)) && (
                            <button
                              onClick={() => handleActivate(cls)}
                              className="text-xs text-slate-400 hover:text-green-400 px-3 py-1.5 rounded-lg hover:bg-green-500/10 transition-all"
                            >
                              Activate
                            </button>
                          )}
                          {(user?.role === 'admin' || user?.role === 'super_admin' || user?.role === 'center_admin') && cls.current_students === 0 && (
                            <button
                              onClick={() => handleHardDelete(cls)}
                              className="text-xs text-slate-400 hover:text-red-400 px-3 py-1.5 rounded-lg hover:bg-red-500/10 transition-all"
                            >
                              Delete
                            </button>
                          )}
                        </>
                      )}
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {/* Modal */}
      {showForm && (
        <ClassForm
          initialData={editingClass}
          onClose={handleFormClose}
        />
      )}
    </div>
  );
}
