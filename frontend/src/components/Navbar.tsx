import React from 'react';
import { useAuth } from '../context/AuthContext';
import { Shield, User as UserIcon, LogOut, Mic, Activity, CheckCircle2 } from 'lucide-react';

interface NavbarProps {
  onOpenVoiceRoom: () => void;
  activeTab: string;
  setActiveTab: (tab: string) => void;
}

export const Navbar: React.FC<NavbarProps> = ({ onOpenVoiceRoom, activeTab, setActiveTab }) => {
  const { user, logout } = useAuth();

  const getRoleBadge = (role?: string) => {
    switch (role) {
      case 'ADMIN':
        return <span className="bg-purple-900/60 text-purple-300 border border-purple-500/30 text-xs px-2.5 py-0.5 rounded-full font-medium">Administrator</span>;
      case 'ASSIGNER':
        return <span className="bg-blue-900/60 text-blue-300 border border-blue-500/30 text-xs px-2.5 py-0.5 rounded-full font-medium">Task Assigner</span>;
      case 'INTERN':
        return <span className="bg-emerald-900/60 text-emerald-300 border border-emerald-500/30 text-xs px-2.5 py-0.5 rounded-full font-medium">Intern</span>;
      default:
        return null;
    }
  };

  return (
    <header className="bg-slate-900 border-b border-slate-800 sticky top-0 z-40">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-16 flex items-center justify-between">
        <div className="flex items-center space-x-6">
          <div className="flex items-center space-x-3 cursor-pointer" onClick={() => setActiveTab('dashboard')}>
            <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-cyan-500 to-blue-600 flex items-center justify-center text-white shadow-lg shadow-cyan-500/20">
              <Shield className="w-5 h-5" />
            </div>
            <div>
              <div className="font-bold text-lg text-slate-100 flex items-center gap-2">
                Task Reviewer AI
                <span className="text-[10px] bg-slate-800 text-cyan-400 border border-cyan-800/50 px-1.5 py-0.5 rounded font-mono">LOCAL FOSS</span>
              </div>
              <div className="text-xs text-slate-400">Autonomous Reviewer & Voice Briefing</div>
            </div>
          </div>

          <nav className="hidden md:flex items-center space-x-1">
            <button
              onClick={() => setActiveTab('dashboard')}
              className={`px-3 py-1.5 rounded-lg text-sm font-medium transition-colors ${
                activeTab === 'dashboard'
                  ? 'bg-slate-800 text-cyan-400'
                  : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800/50'
              }`}
            >
              Dashboard
            </button>
            {user?.role === 'ADMIN' && (
              <button
                onClick={() => setActiveTab('system')}
                className={`px-3 py-1.5 rounded-lg text-sm font-medium transition-colors ${
                  activeTab === 'system'
                    ? 'bg-slate-800 text-cyan-400'
                    : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800/50'
                }`}
              >
                System & Benchmarks
              </button>
            )}
          </nav>
        </div>

        <div className="flex items-center space-x-4">
          <button
            onClick={onOpenVoiceRoom}
            className="flex items-center space-x-2 bg-gradient-to-r from-cyan-600 to-blue-600 hover:from-cyan-500 hover:to-blue-500 text-white text-xs font-semibold px-3 py-2 rounded-lg shadow-md transition-all active:scale-95"
            title="Open local Web Audio Voice Room"
          >
            <Mic className="w-4 h-4 animate-pulse" />
            <span>Interactive Voice Room</span>
          </button>

          <div className="hidden sm:flex items-center space-x-2 text-xs bg-slate-800/60 border border-slate-700/50 px-3 py-1.5 rounded-lg text-slate-300">
            <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400" />
            <span>Ollama 1B Ready</span>
          </div>

          {user && (
            <div className="flex items-center space-x-3 pl-2 border-l border-slate-800">
              <div className="flex flex-col text-right">
                <span className="text-sm font-medium text-slate-200">{user.full_name}</span>
                <div className="flex items-center justify-end space-x-1 mt-0.5">
                  {getRoleBadge(user.role)}
                </div>
              </div>
              <button
                onClick={logout}
                className="p-2 text-slate-400 hover:text-rose-400 hover:bg-slate-800 rounded-lg transition-colors"
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
