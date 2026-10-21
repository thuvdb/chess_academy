import { useState } from 'react';
import { Outlet } from 'react-router-dom';
import Sidebar from './Sidebar';
import { GraduationCap, Menu } from 'lucide-react';

export default function AppLayout() {
  const [isMobileOpen, setIsMobileOpen] = useState(false);
  const [isCollapsed, setIsCollapsed] = useState(() => {
    return localStorage.getItem('cams_sidebar_collapsed') === 'true';
  });

  const toggleCollapse = () => {
    setIsCollapsed(prev => {
      const next = !prev;
      localStorage.setItem('cams_sidebar_collapsed', String(next));
      return next;
    });
  };

  const closeMobile = () => setIsMobileOpen(false);
  const openMobile = () => setIsMobileOpen(true);

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 flex flex-col md:flex-row">
      {/* Mobile Top Bar */}
      <header className="md:hidden sticky top-0 z-40 flex items-center justify-between px-4 py-3 bg-slate-900 border-b border-slate-800 shadow-md">
        <div className="flex items-center gap-2.5">
          <div className="w-8 h-8 rounded-lg bg-linear-to-br from-amber-400 to-orange-500 flex items-center justify-center shadow-md shrink-0">
            <GraduationCap className="w-4 h-4 text-white" />
          </div>
          <div>
            <p className="text-white font-bold text-sm leading-none">CAMS</p>
            <p className="text-slate-400 text-[10px] mt-0.5">Chess Academy</p>
          </div>
        </div>
        <button
          type="button"
          onClick={openMobile}
          className="p-2 rounded-lg text-slate-300 hover:text-white hover:bg-slate-800 transition-colors focus:outline-hidden"
          aria-label="Mở menu điều hướng"
        >
          <Menu className="w-6 h-6" />
        </button>
      </header>

      {/* Sidebar (Responsive Mobile Drawer + Desktop Collapsible) */}
      <Sidebar
        isMobileOpen={isMobileOpen}
        onCloseMobile={closeMobile}
        isCollapsed={isCollapsed}
        onToggleCollapse={toggleCollapse}
      />

      {/* Main Content Area */}
      <main
        className={`flex-1 min-h-[calc(100dvh-57px)] md:min-h-screen w-full transition-all duration-300 ease-in-out ${
          isCollapsed ? 'md:ml-20' : 'md:ml-64'
        }`}
      >
        <Outlet />
      </main>
    </div>
  );
}
