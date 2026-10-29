import React from 'react';
import { useAuth } from '../context/AuthContext';
import { Shield, LogOut, Video, LayoutDashboard, Briefcase, Settings2, Sparkles, GraduationCap } from 'lucide-react';

interface NavbarProps {
  activeTab: string;
  setActiveTab: (tab: string) => void;
}

export const Navbar: React.FC<NavbarProps> = ({ activeTab, setActiveTab }) => {
  const { user, logout } = useAuth();

  const getRoleBadge = (role?: string) => {
    switch (role) {
      case 'ADMIN':
        return (
          <span className="neo-inset px-2.5 py-0.5 rounded-full text-[11px] font-semibold text-purple-300 border border-purple-500/30">
            Administrator
          </span>
        );
      case 'ASSIGNER':
        return (
          <span className="neo-inset px-2.5 py-0.5 rounded-full text-[11px] font-semibold text-cyan-300 border border-cyan-500/30">
            Task Assigner
          </span>
        );
      case 'INTERN':
        return (
          <span className="neo-inset px-2.5 py-0.5 rounded-full text-[11px] font-semibold text-emerald-300 border border-emerald-500/30">
            Intern
          </span>
        );
      default:
        return null;
    }
  };

  return (
    <header className="sticky top-0 z-40 backdrop-blur-2xl bg-slate-950/75 border-b border-white/[0.08] shadow-[0_4px_30px_rgba(0,0,0,0.5)]">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-18 flex items-center justify-between">
        {/* Left: Brand Logo & Navigation */}
        <div className="flex items-center space-x-8">
          <div
            className="flex items-center space-x-3.5 cursor-pointer group"
            onClick={() => setActiveTab('dashboard')}
          >
            <div className="w-11 h-11 rounded-2xl bg-gradient-to-br from-cyan-500 via-blue-600 to-indigo-600 flex items-center justify-center text-white shadow-lg shadow-cyan-500/25 border border-white/20 transition-transform group-hover:scale-105 active:scale-95">
              <Shield className="w-6 h-6 drop-shadow-md" />
            </div>
            <div>
              <div className="font-extrabold text-base sm:text-lg text-white tracking-tight flex items-center gap-2">
                Task Reviewer AI
              </div>
              <div className="text-[11px] text-slate-400 font-medium tracking-wide">
                Autonomous Reviewer & Meeting AI
              </div>
            </div>
          </div>

          {/* Navigation Tabs */}
          <nav className="hidden md:flex items-center space-x-2 neo-inset p-1 rounded-2xl border border-white/[0.06]">
            {user?.role === 'INTERN' ? (
              <button
                onClick={() => setActiveTab('workspace')}
                className="flex items-center space-x-2 px-4 py-2 rounded-xl text-xs font-bold glass-btn-primary text-white shadow-md"
              >
                <GraduationCap className="w-3.5 h-3.5 text-emerald-400" />
                <span>Intern Tasks Dashboard</span>
              </button>
            ) : (
              <>
                <button
                  onClick={() => setActiveTab('dashboard')}
                  className={`flex items-center space-x-2 px-4 py-2 rounded-xl text-xs font-bold transition-all ${
                    activeTab === 'dashboard'
                      ? 'glass-btn-primary text-white shadow-md'
                      : 'text-slate-400 hover:text-slate-200 hover:bg-white/[0.04]'
                  }`}
                >
                  <LayoutDashboard className="w-3.5 h-3.5" />
                  <span>Executive Dashboard</span>
                </button>

                <button
                  onClick={() => setActiveTab('workspace')}
                  className={`flex items-center space-x-2 px-4 py-2 rounded-xl text-xs font-bold transition-all ${
                    activeTab === 'workspace'
                      ? 'glass-btn-primary text-white shadow-md'
                      : 'text-slate-400 hover:text-slate-200 hover:bg-white/[0.04]'
                  }`}
                >
                  <Briefcase className="w-3.5 h-3.5" />
                  <span>Tasks Workspace</span>
                </button>
              </>
            )}

            {user?.role === 'ADMIN' && (
              <button
                onClick={() => setActiveTab('system')}
                className={`flex items-center space-x-2 px-4 py-2 rounded-xl text-xs font-bold transition-all ${
                  activeTab === 'system'
                    ? 'glass-btn-primary text-white shadow-md'
                    : 'text-slate-400 hover:text-slate-200 hover:bg-white/[0.04]'
                }`}
              >
                <Settings2 className="w-3.5 h-3.5" />
                <span>System & Benchmarks</span>
              </button>
            )}
          </nav>
        </div>

        {/* Right: Meeting Bot Status & User Profile */}
        <div className="flex items-center space-x-4">
          {/* Google Meet Bot Ready indicator */}
          <div className="hidden sm:flex items-center space-x-2 neo-inset px-3.5 py-1.5 rounded-full border border-indigo-500/30 text-indigo-300 text-xs font-semibold">
            <span className="w-2 h-2 rounded-full bg-indigo-400 animate-pulse" />
            <Video className="w-3.5 h-3.5 text-indigo-400" />
            <span>Google Meet Bot Ready</span>
          </div>

          {user && (
            <div className="flex items-center space-x-3.5 pl-3 border-l border-white/[0.08]">
              <div className="flex flex-col text-right">
                <span className="text-xs sm:text-sm font-bold text-slate-100">{user.full_name}</span>
                <div className="flex items-center justify-end mt-0.5">
                  {getRoleBadge(user.role)}
                </div>
              </div>
              <button
                onClick={logout}
                className="p-2.5 rounded-xl neo-btn text-slate-400 hover:text-rose-400 hover:border-rose-500/30 transition-all active:scale-95"
                title="Log out"
              >
                <LogOut className="w-4 h-4" />
              </button>
            </div>
          )}
        </div>
      </div>
    </header>
  );
};
