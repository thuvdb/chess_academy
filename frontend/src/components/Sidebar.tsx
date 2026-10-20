import { useEffect } from 'react';
import { NavLink, useNavigate, useLocation } from 'react-router-dom';
import { useAuthStore } from '../store/authStore';
import { resolveMediaUrl } from '../config';
import {
  GraduationCap,
  LayoutDashboard,
  BookOpen,
  Calendar,
  LogOut,
  ChevronRight,
  ChevronLeft,
  ScanSearch,
  Swords,
  Trophy,
  ClipboardList,
  Users,
  User,
  UserCog,
  Settings,
  X,
  Bot,
} from 'lucide-react';

interface NavItem {
  to: string;
  label: string;
  icon: any;
  roles?: string[];
}

interface SidebarProps {
  isMobileOpen?: boolean;
  onCloseMobile?: () => void;
  isCollapsed?: boolean;
  onToggleCollapse?: () => void;
}

const ROLE_LABELS: Record<string, string> = {
  super_admin: 'Super Admin',
  center_admin: 'Admin trung tâm',
  admin: 'Admin trung tâm',
  teacher: 'Giáo viên',
  student: 'Học sinh',
  parent: 'Phụ huynh',
};

const navItems: NavItem[] = [
  { to: '/', label: 'Tổng quan', icon: LayoutDashboard },
  { to: '/classes', label: 'Lớp học', icon: BookOpen },
  { to: '/schedule', label: 'Lịch học', icon: Calendar },
  { to: '/scanner', label: 'Quét AI bàn cờ', icon: ScanSearch, roles: ['super_admin', 'admin', 'center_admin', 'teacher'] },
  { to: '/puzzles', label: 'Kho bài tập cờ', icon: Swords },
  { to: '/practice', label: 'Luyện tập', icon: Swords },
  { to: '/ai-tutor', label: 'Hỏi đáp AI', icon: Bot },
  { to: '/assignments', label: 'Bài tập về nhà', icon: ClipboardList },
  { to: '/leaderboard', label: 'Bảng xếp hạng', icon: Trophy },
  { to: '/fee-plans', label: 'Gói học phí', icon: ClipboardList, roles: ['super_admin', 'admin', 'center_admin'] },
  { to: '/invoices', label: 'Học phí & Hóa đơn', icon: ClipboardList },
  { to: '/tournaments', label: 'Giải đấu', icon: Trophy },
  { to: '/members', label: 'Quản lý thành viên', icon: Users, roles: ['super_admin', 'admin', 'center_admin'] },
  { to: '/profile', label: 'Hồ sơ cá nhân', icon: User },
  { to: '/settings', label: 'Cài đặt', icon: Settings },
];

export default function Sidebar({
  isMobileOpen = false,
  onCloseMobile = () => {},
  isCollapsed = false,
  onToggleCollapse = () => {},
}: SidebarProps) {
  const { user, logout } = useAuthStore();
  const navigate = useNavigate();
  const location = useLocation();

  const handleLogout = () => {
    logout();
    navigate('/login');
  };

  // Tự động đóng mobile drawer khi chuyển route
  useEffect(() => {
    if (isMobileOpen) {
      onCloseMobile();
    }
  }, [location.pathname]);

  // Đóng mobile drawer khi nhấn Escape
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape' && isMobileOpen) {
        onCloseMobile();
      }
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [isMobileOpen, onCloseMobile]);

  // Khóa cuộn trang khi mở drawer trên mobile
  useEffect(() => {
    if (isMobileOpen) {
      document.body.style.overflow = 'hidden';
    } else {
      document.body.style.overflow = '';
    }
    return () => {
      document.body.style.overflow = '';
    };
  }, [isMobileOpen]);

  const visibleNavItems = navItems.filter((item) => {
    if (!item.roles) return true;
    return user?.role ? item.roles.includes(user.role) : false;
  });

  return (
    <>
      {/* ========================================================
          1. MOBILE DRAWER (< 768px / md:hidden)
          ======================================================== */}
      <div className="md:hidden">
        {/* Backdrop */}
        {isMobileOpen && (
          <div
            className="fixed inset-0 bg-black/50 z-50 transition-opacity backdrop-blur-xs"
            onClick={onCloseMobile}
            aria-hidden="true"
          />
        )}

        {/* Sliding Drawer */}
        <aside
          className={`fixed inset-y-0 left-0 z-50 w-72 max-w-[85vw] bg-slate-900 border-r border-slate-800 flex flex-col shadow-2xl transition-all duration-300 ease-in-out ${
            isMobileOpen
              ? 'translate-x-0 opacity-100 visible'
              : '-translate-x-full opacity-0 invisible pointer-events-none'
          }`}
          aria-label="Mobile Navigation"
        >
          {/* Header Mobile Drawer */}
          <div className="flex items-center justify-between px-5 py-4 border-b border-slate-800">
            <div className="flex items-center gap-3">
              <div className="w-9 h-9 rounded-xl bg-linear-to-br from-amber-400 to-orange-500 flex items-center justify-center shadow-lg shrink-0">
                <GraduationCap className="w-5 h-5 text-white" />
              </div>
              <div>
                <p className="text-white font-bold text-sm leading-none">CAMS</p>
                <p className="text-slate-400 text-xs mt-0.5">Chess Academy</p>
              </div>
            </div>
            <button
              type="button"
              onClick={onCloseMobile}
              className="p-1.5 rounded-lg text-slate-400 hover:text-white hover:bg-slate-800 transition-colors focus:outline-hidden"
              aria-label="Đóng menu"
            >
              <X className="w-5 h-5" />
            </button>
          </div>

          {/* Navigation Links */}
          <nav className="flex-1 px-3 py-4 space-y-1 overflow-y-auto">
            {visibleNavItems.map(({ to, label, icon: Icon }) => (
              <NavLink
                key={to}
                to={to}
                end={to === '/'}
                onClick={onCloseMobile}
                className={({ isActive }) =>
                  `flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-all group ${
                    isActive
                      ? 'bg-amber-500/15 text-amber-400 border border-amber-500/30'
                      : 'text-slate-400 hover:text-slate-100 hover:bg-slate-800'
                  }`
                }
              >
                {({ isActive }) => (
                  <>
                    <Icon className={`w-4 h-4 shrink-0 ${isActive ? 'text-amber-400' : ''}`} />
                    <span className="flex-1 truncate">{label}</span>
                    {isActive && <ChevronRight className="w-3.5 h-3.5 text-amber-400 shrink-0" />}
                  </>
                )}
              </NavLink>
            ))}
          </nav>

          {/* User Profile & Logout */}
          <div className="px-3 pb-4 border-t border-slate-800 pt-4">
            <div
              onClick={() => {
                onCloseMobile();
                navigate('/profile');
              }}
              title="Hồ sơ cá nhân"
              className="flex items-center gap-3 px-3 py-2.5 rounded-lg bg-slate-800/80 border border-slate-700/50 mb-2 cursor-pointer hover:bg-slate-800 hover:border-slate-600 transition-all"
            >
              <div className="w-8 h-8 rounded-full bg-linear-to-br from-amber-500 to-orange-600 flex items-center justify-center text-white text-xs font-bold shrink-0 shadow-sm">
                {user?.avatar_url ? (
                  <img src={resolveMediaUrl(user.avatar_url)} className="w-8 h-8 rounded-full object-cover" alt="avatar" />
                ) : (
                  user?.full_name?.charAt(0)?.toUpperCase() ?? 'U'
                )}
              </div>
              <div className="flex-1 min-w-0">
                <p className="text-white text-xs font-semibold truncate">{user?.full_name}</p>
                <div className="flex items-center gap-1.5 mt-0.5">
                  <span className="text-slate-400 text-[10px] font-medium">
                    {(user?.role && ROLE_LABELS[user.role]) || user?.role?.replace('_', ' ')}
                  </span>
                  <span className="text-slate-600 text-[9px]">•</span>
                  <span className="text-amber-400/90 text-[10px] font-semibold truncate max-w-[85px]">
                    {user?.role === 'super_admin' ? 'Toàn hệ thống' : user?.center_name || 'Trung tâm'}
                  </span>
                </div>
              </div>
              <UserCog className="w-4 h-4 text-slate-400 shrink-0" />
            </div>
            <button
              type="button"
              onClick={() => {
                onCloseMobile();
                handleLogout();
              }}
              className="w-full flex items-center gap-2 px-3 py-2 text-slate-400 hover:text-red-400 hover:bg-red-500/10 rounded-lg transition-all text-xs font-medium"
            >
              <LogOut className="w-4 h-4" />
              Đăng xuất
            </button>
          </div>
        </aside>
      </div>

      {/* ========================================================
          2. DESKTOP SIDEBAR (>= 768px / hidden md:flex)
          ======================================================== */}
      <aside
        className={`hidden md:flex fixed top-0 left-0 h-full bg-slate-900 flex-col border-r border-slate-800 z-30 transition-all duration-300 ease-in-out ${
          isCollapsed ? 'w-20' : 'w-64'
        }`}
        aria-label="Desktop Navigation"
      >
        {/* Desktop Header */}
        <div
          className={`flex items-center border-b border-slate-800 transition-all duration-300 ${
            isCollapsed ? 'justify-center flex-col gap-2 py-4 px-2' : 'justify-between px-5 py-4'
          }`}
        >
          {isCollapsed ? (
            <>
              <div
                className="w-10 h-10 rounded-xl bg-linear-to-br from-amber-400 to-orange-500 flex items-center justify-center shadow-lg cursor-pointer hover:opacity-90 transition-opacity"
                title="CAMS Chess Academy (Nhấn để mở rộng)"
                onClick={onToggleCollapse}
              >
                <GraduationCap className="w-5 h-5 text-white" />
              </div>
              <button
                type="button"
                onClick={onToggleCollapse}
                className="p-1.5 rounded-lg text-slate-400 hover:text-amber-400 hover:bg-slate-800 transition-colors focus:outline-hidden"
                title="Mở rộng thanh bên"
                aria-label="Mở rộng thanh bên"
              >
                <ChevronRight className="w-5 h-5" />
              </button>
            </>
          ) : (
            <>
              <div className="flex items-center gap-3 min-w-0">
                <div className="w-9 h-9 rounded-xl bg-linear-to-br from-amber-400 to-orange-500 flex items-center justify-center shadow-lg shrink-0">
                  <GraduationCap className="w-5 h-5 text-white" />
                </div>
                <div className="min-w-0">
                  <p className="text-white font-bold text-sm leading-none">CAMS</p>
                  <p className="text-slate-400 text-xs mt-0.5 truncate">Chess Academy</p>
                </div>
              </div>
              <button
                type="button"
                onClick={onToggleCollapse}
                className="p-1.5 rounded-lg text-slate-400 hover:text-white hover:bg-slate-800 transition-colors shrink-0 focus:outline-hidden"
                title="Thu gọn thanh bên"
                aria-label="Thu gọn thanh bên"
              >
                <ChevronLeft className="w-5 h-5" />
              </button>
            </>
          )}
        </div>

        {/* Desktop Nav Items */}
        <nav className={`flex-1 overflow-y-auto ${isCollapsed ? 'px-2 py-3 space-y-1.5' : 'px-3 py-4 space-y-1'}`}>
          {visibleNavItems.map(({ to, label, icon: Icon }) => (
            <NavLink
              key={to}
              to={to}
              end={to === '/'}
              title={isCollapsed ? label : undefined}
              className={({ isActive }) =>
                `flex items-center rounded-lg font-medium transition-all group ${
                  isCollapsed ? 'justify-center p-2.5 text-sm' : 'gap-3 px-3 py-2.5 text-sm'
                } ${
                  isActive
                    ? 'bg-amber-500/15 text-amber-400 border border-amber-500/30'
                    : 'text-slate-400 hover:text-slate-100 hover:bg-slate-800'
                }`
              }
            >
              {({ isActive }) => (
                <>
                  <Icon
                    className={`${isCollapsed ? 'w-5 h-5' : 'w-4 h-4'} shrink-0 ${
                      isActive ? 'text-amber-400' : ''
                    }`}
                  />
                  {!isCollapsed && (
                    <>
                      <span className="flex-1 truncate">{label}</span>
                      {isActive && <ChevronRight className="w-3.5 h-3.5 text-amber-400 shrink-0" />}
                    </>
                  )}
                </>
              )}
            </NavLink>
          ))}
        </nav>

        {/* Desktop User + Logout */}
        <div
          className={`border-t border-slate-800 ${
            isCollapsed ? 'px-2 py-3 flex flex-col items-center gap-2' : 'px-3 pb-4 pt-4'
          }`}
        >
          {isCollapsed ? (
            <>
              <div
                onClick={() => navigate('/profile')}
                title={`Hồ sơ cá nhân: ${user?.full_name || 'Người dùng'}`}
                className="w-10 h-10 rounded-full bg-linear-to-br from-amber-500 to-orange-600 flex items-center justify-center text-white text-xs font-bold cursor-pointer hover:ring-2 hover:ring-amber-400 transition-all shadow-sm shrink-0"
              >
                {user?.avatar_url ? (
                  <img src={resolveMediaUrl(user.avatar_url)} className="w-10 h-10 rounded-full object-cover" alt="avatar" />
                ) : (
                  user?.full_name?.charAt(0)?.toUpperCase() ?? 'U'
                )}
              </div>
              <button
                type="button"
                onClick={handleLogout}
                title="Đăng xuất"
                className="p-2 text-slate-400 hover:text-red-400 hover:bg-red-500/10 rounded-lg transition-all focus:outline-hidden"
                aria-label="Đăng xuất"
              >
                <LogOut className="w-5 h-5" />
              </button>
            </>
          ) : (
            <>
              <div
                onClick={() => navigate('/profile')}
                title="Hồ sơ cá nhân"
                className="flex items-center gap-3 px-3 py-2.5 rounded-lg bg-slate-800/80 border border-slate-700/50 mb-2 cursor-pointer hover:bg-slate-800 hover:border-slate-600 transition-all"
              >
                <div className="w-8 h-8 rounded-full bg-linear-to-br from-amber-500 to-orange-600 flex items-center justify-center text-white text-xs font-bold shrink-0 shadow-sm">
                  {user?.avatar_url ? (
                    <img src={resolveMediaUrl(user.avatar_url)} className="w-8 h-8 rounded-full object-cover" alt="avatar" />
                  ) : (
                    user?.full_name?.charAt(0)?.toUpperCase() ?? 'U'
                  )}
                </div>
                <div className="flex-1 min-w-0">
                  <p className="text-white text-xs font-semibold truncate">{user?.full_name}</p>
                  <div className="flex items-center gap-1.5 mt-0.5">
                    <span className="text-slate-400 text-[10px] font-medium">
                      {(user?.role && ROLE_LABELS[user.role]) || user?.role?.replace('_', ' ')}
                    </span>
                    <span className="text-slate-600 text-[9px]">•</span>
                    <span className="text-amber-400/90 text-[10px] font-semibold truncate max-w-[85px]">
                      {user?.role === 'super_admin' ? 'Toàn hệ thống' : user?.center_name || 'Trung tâm'}
                    </span>
                  </div>
                </div>
                <UserCog className="w-4 h-4 text-slate-400 shrink-0" />
              </div>
              <button
                type="button"
                onClick={handleLogout}
                className="w-full flex items-center gap-2 px-3 py-2 text-slate-400 hover:text-red-400 hover:bg-red-500/10 rounded-lg transition-all text-xs font-medium focus:outline-hidden"
              >
                <LogOut className="w-4 h-4" />
                Đăng xuất
              </button>
            </>
          )}
        </div>
      </aside>
    </>
  );
}
