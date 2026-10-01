import { useAuthStore } from '../store/authStore';
import { BookOpen, Users, Calendar, TrendingUp, GraduationCap } from 'lucide-react';
import { Link } from 'react-router-dom';

const STAT_CARDS = [
  { label: 'My Classes', value: '—', icon: BookOpen, color: 'from-blue-500 to-blue-600', to: '/classes' },
  { label: 'Students', value: '—', icon: Users, color: 'from-purple-500 to-purple-600', to: '/students' },
  { label: 'Schedule', value: '—', icon: Calendar, color: 'from-amber-500 to-orange-500', to: '/schedule' },
  { label: 'Avg ELO', value: '—', icon: TrendingUp, color: 'from-green-500 to-emerald-600', to: '/' },
];

export default function Dashboard() {
  const { user } = useAuthStore();

  return (
    <div className="p-8">
      {/* Welcome Banner */}
      <div className="bg-gradient-to-br from-slate-800 to-slate-900 border border-slate-700/50 rounded-2xl p-8 mb-8 relative overflow-hidden">
        <div className="absolute top-0 right-0 w-64 h-64 bg-amber-500/5 rounded-full -translate-y-1/2 translate-x-1/2 blur-2xl" />
        <div className="relative z-10">
          <div className="flex items-center gap-3 mb-3">
            <div className="w-12 h-12 rounded-2xl bg-gradient-to-br from-amber-400 to-orange-500 flex items-center justify-center shadow-xl shadow-amber-500/30">
              <GraduationCap className="w-6 h-6 text-white" />
            </div>
            <div>
              <p className="text-slate-400 text-sm">Welcome back,</p>
              <h1 className="text-2xl font-bold text-white">{user?.full_name ?? 'Guest'}</h1>
            </div>
          </div>
          <div className="flex items-center gap-2 mt-2">
            <span className="bg-amber-500/15 text-amber-400 border border-amber-500/30 text-xs px-2.5 py-1 rounded-full font-medium capitalize">
              {user?.role}
            </span>
            <span className="text-slate-500 text-xs">ELO: {user?.elo_rating ?? '—'}</span>
          </div>
        </div>
      </div>

      {/* Quick Stats */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 mb-8">
        {STAT_CARDS.map(({ label, value, icon: Icon, color, to }) => (
          <Link
            key={label}
            to={to}
            className="bg-slate-800/50 border border-slate-700/50 rounded-2xl p-5 hover:border-slate-600 transition-all group"
          >
            <div className={`w-10 h-10 rounded-xl bg-gradient-to-br ${color} flex items-center justify-center mb-3 shadow-lg group-hover:scale-110 transition-transform`}>
              <Icon className="w-5 h-5 text-white" />
            </div>
            <p className="text-2xl font-bold text-white">{value}</p>
            <p className="text-slate-400 text-sm mt-1">{label}</p>
          </Link>
        ))}
      </div>

      {/* Quick Links */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <Link
          to="/classes"
          className="bg-slate-800/50 border border-slate-700/50 rounded-2xl p-6 hover:border-amber-500/40 hover:bg-amber-500/5 transition-all group"
        >
          <h3 className="text-white font-semibold mb-1 group-hover:text-amber-400 transition-colors">Manage Classes →</h3>
          <p className="text-slate-400 text-sm">Create, edit classes and manage student enrollments</p>
        </Link>
        <Link
          to="/schedule"
          className="bg-slate-800/50 border border-slate-700/50 rounded-2xl p-6 hover:border-blue-500/40 hover:bg-blue-500/5 transition-all group"
        >
          <h3 className="text-white font-semibold mb-1 group-hover:text-blue-400 transition-colors">View Schedule →</h3>
          <p className="text-slate-400 text-sm">See the weekly timetable for all active classes</p>
        </Link>
      </div>
    </div>
  );
}
