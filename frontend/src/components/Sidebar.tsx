import { NavLink, useNavigate } from 'react-router-dom';
import { useAuthStore } from '../store/authStore';
import {
  GraduationCap,
  LayoutDashboard,
  BookOpen,
  Calendar,
  LogOut,
  ChevronRight,
  ScanSearch,
  Swords,
  Trophy,
  ClipboardList,
} from 'lucide-react';

const navItems = [
  { to: '/', label: 'Dashboard', icon: LayoutDashboard },
  { to: '/classes', label: 'Classes', icon: BookOpen },
  { to: '/schedule', label: 'Schedule', icon: Calendar },
  { to: '/scanner', label: 'AI Scanner', icon: ScanSearch },
  { to: '/puzzles', label: 'Puzzle Bank', icon: Swords },
  { to: '/practice', label: 'Luyện tập', icon: Swords },
  { to: '/assignments', label: 'Bài tập về nhà', icon: ClipboardList },
  { to: '/leaderboard', label: 'Bảng xếp hạng', icon: Trophy },
];

export default function Sidebar() {
  const { user, logout } = useAuthStore();
  const navigate = useNavigate();

  const handleLogout = () => {
    logout();
    navigate('/login');
  };

  return (
    <aside className="fixed top-0 left-0 h-full w-64 bg-slate-900 flex flex-col border-r border-slate-800 z-30">
      {/* Logo */}
      <div className="flex items-center gap-3 px-6 py-5 border-b border-slate-800">
        <div className="w-9 h-9 rounded-xl bg-gradient-to-br from-amber-400 to-orange-500 flex items-center justify-center shadow-lg">
          <GraduationCap className="w-5 h-5 text-white" />
        </div>
        <div>
          <p className="text-white font-bold text-sm leading-none">CAMS</p>
          <p className="text-slate-400 text-xs mt-0.5">Chess Academy</p>
        </div>
      </div>

      {/* Nav */}
      <nav className="flex-1 px-3 py-4 space-y-1 overflow-y-auto">
        {navItems.map(({ to, label, icon: Icon }) => (
          <NavLink
            key={to}
            to={to}
            end={to === '/'}
            className={({ isActive }) =>
              `flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-all group
               ${isActive
                 ? 'bg-amber-500/15 text-amber-400 border border-amber-500/30'
                 : 'text-slate-400 hover:text-slate-100 hover:bg-slate-800'
               }`
            }
          >
            {({ isActive }) => (
              <>
                <Icon className={`w-4 h-4 flex-shrink-0 ${isActive ? 'text-amber-400' : ''}`} />
                <span className="flex-1">{label}</span>
                {isActive && <ChevronRight className="w-3.5 h-3.5 text-amber-400" />}
              </>
            )}
          </NavLink>
        ))}
      </nav>

      {/* User + Logout */}
      <div className="px-3 pb-4 border-t border-slate-800 pt-4">
        <div className="flex items-center gap-3 px-3 py-2 rounded-lg bg-slate-800 mb-2">
          <div className="w-8 h-8 rounded-full bg-gradient-to-br from-blue-500 to-purple-600 flex items-center justify-center text-white text-xs font-bold flex-shrink-0">
            {user?.full_name?.charAt(0)?.toUpperCase() ?? 'U'}
          </div>
          <div className="flex-1 min-w-0">
            <p className="text-white text-xs font-semibold truncate">{user?.full_name}</p>
            <p className="text-slate-400 text-xs capitalize">{user?.role}</p>
          </div>
        </div>
        <button
          onClick={handleLogout}
          className="w-full flex items-center gap-2 px-3 py-2 text-slate-400 hover:text-red-400 hover:bg-red-500/10 rounded-lg transition-all text-sm"
        >
          <LogOut className="w-4 h-4" />
          Sign Out
        </button>
      </div>
    </aside>
  );
}
