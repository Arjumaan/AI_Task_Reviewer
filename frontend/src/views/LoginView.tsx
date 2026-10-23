import React, { useState } from 'react';
import { useAuth } from '../context/AuthContext';
import { authApi } from '../api/client';
import { Shield, Lock, Mail, ArrowRight, UserCheck, Briefcase, GraduationCap, UserPlus } from 'lucide-react';

export const LoginView: React.FC = () => {
  const { login } = useAuth();
  const [isRegisterMode, setIsRegisterMode] = useState(false);
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [fullName, setFullName] = useState('');
  const [role, setRole] = useState<'INTERN' | 'ASSIGNER'>('INTERN');
  const [error, setError] = useState<string | null>(null);
  const [successMsg, setSuccessMsg] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setSuccessMsg(null);
    setIsLoading(true);
    try {
      if (isRegisterMode) {
        await authApi.register({
          email: email.trim().toLowerCase(),
          full_name: fullName.trim(),
          password,
          role
        });
        setSuccessMsg('Account registered successfully! Signing in...');
        await login(email.trim().toLowerCase(), password);
      } else {
        await login(email.trim().toLowerCase(), password);
      }
    } catch (err: any) {
      const msg = err?.response?.data?.detail || err?.message || 'Operation failed. Please try again.';
      setError(typeof msg === 'string' ? msg : JSON.stringify(msg));
    } finally {
      setIsLoading(false);
    }
  };

  const quickLogin = async (userEmail: string) => {
    setEmail(userEmail);
    setPassword('SecretPass123!');
    setIsLoading(true);
    setError(null);
    setSuccessMsg(null);
    try {
      await login(userEmail, 'SecretPass123!');
    } catch (err: any) {
      setError(err?.response?.data?.detail || 'Quick login failed. Ensure seed data is initialized.');
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-slate-950 flex flex-col justify-center py-12 sm:px-6 lg:px-8">
      <div className="sm:mx-auto sm:w-full sm:max-w-md text-center">
        <div className="mx-auto w-14 h-14 rounded-2xl bg-gradient-to-tr from-cyan-500 to-blue-600 flex items-center justify-center text-white shadow-xl shadow-cyan-500/20 mb-4">
          <Shield className="w-8 h-8" />
        </div>
        <h2 className="text-3xl font-extrabold text-slate-100 tracking-tight">Task Reviewer AI</h2>
        <p className="mt-2 text-sm text-slate-400">
          Autonomous Intern Task Briefing, Evidence Evaluation & Revision System
        </p>
      </div>

      <div className="mt-8 sm:mx-auto sm:w-full sm:max-w-md">
        <div className="bg-slate-900 py-8 px-6 shadow-2xl border border-slate-800 rounded-2xl sm:px-10 space-y-6">
          <div className="flex border-b border-slate-800 pb-3">
            <button
              type="button"
              onClick={() => { setIsRegisterMode(false); setError(null); }}
              className={`flex-1 pb-2 text-sm font-semibold border-b-2 transition-colors ${
                !isRegisterMode
                  ? 'border-cyan-500 text-cyan-400'
                  : 'border-transparent text-slate-400 hover:text-slate-200'
              }`}
            >
              Sign In
            </button>
            <button
              type="button"
              onClick={() => { setIsRegisterMode(true); setError(null); }}
              className={`flex-1 pb-2 text-sm font-semibold border-b-2 transition-colors ${
                isRegisterMode
                  ? 'border-cyan-500 text-cyan-400'
                  : 'border-transparent text-slate-400 hover:text-slate-200'
              }`}
            >
              Register New Intern
            </button>
          </div>

          {error && (
            <div className="p-3 bg-rose-950/60 border border-rose-800 text-rose-300 text-sm rounded-xl">
              {error}
            </div>
          )}

          {successMsg && (
            <div className="p-3 bg-emerald-950/60 border border-emerald-800 text-emerald-300 text-sm rounded-xl">
              {successMsg}
            </div>
          )}

          <form onSubmit={handleSubmit} className="space-y-4">
            {isRegisterMode && (
              <>
                <div>
                  <label className="block text-xs font-semibold uppercase text-slate-400 tracking-wider mb-1">
                    Full Name & Title
                  </label>
                  <input
                    type="text"
                    required
                    value={fullName}
                    onChange={(e) => setFullName(e.target.value)}
                    placeholder="e.g. Priyanshu Patel (AI/ML Intern)"
                    className="w-full bg-slate-950 border border-slate-800 rounded-xl px-4 py-2.5 text-sm text-slate-200 placeholder-slate-600 focus:outline-none focus:border-cyan-500 transition-colors"
                  />
                </div>

                <div>
                  <label className="block text-xs font-semibold uppercase text-slate-400 tracking-wider mb-1">
                    Account Role
                  </label>
                  <select
                    value={role}
                    onChange={(e) => setRole(e.target.value as any)}
                    className="w-full bg-slate-950 border border-slate-800 rounded-xl px-4 py-2.5 text-sm text-slate-200 focus:outline-none focus:border-cyan-500 transition-colors"
                  >
                    <option value="INTERN">Intern (Learner & Reviewee)</option>
                    <option value="ASSIGNER">Assigner (Tech Lead / Task Creator)</option>
                  </select>
                </div>
              </>
            )}

            <div>
              <label className="block text-xs font-semibold uppercase text-slate-400 tracking-wider mb-1">
                Email Address
              </label>
              <div className="relative">
                <Mail className="w-5 h-5 absolute left-3 top-3 text-slate-500" />
                <input
                  type="email"
                  required
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  placeholder="user@internal.company"
                  className="w-full bg-slate-950 border border-slate-800 rounded-xl pl-10 pr-4 py-2.5 text-sm text-slate-200 placeholder-slate-600 focus:outline-none focus:border-cyan-500 transition-colors"
                />
              </div>
            </div>

            <div>
              <label className="block text-xs font-semibold uppercase text-slate-400 tracking-wider mb-1">
                Password
              </label>
              <div className="relative">
                <Lock className="w-5 h-5 absolute left-3 top-3 text-slate-500" />
                <input
                  type="password"
                  required
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  placeholder="••••••••••••"
                  className="w-full bg-slate-950 border border-slate-800 rounded-xl pl-10 pr-4 py-2.5 text-sm text-slate-200 placeholder-slate-600 focus:outline-none focus:border-cyan-500 transition-colors"
                />
              </div>
            </div>

            <button
              type="submit"
              disabled={isLoading}
              className="w-full flex items-center justify-center space-x-2 bg-gradient-to-r from-cyan-600 to-blue-600 hover:from-cyan-500 hover:to-blue-500 text-white font-semibold py-2.5 rounded-xl shadow-lg shadow-cyan-600/30 transition-all disabled:opacity-50"
            >
              <span>{isLoading ? 'Processing...' : isRegisterMode ? 'Create Account & Sign In' : 'Sign In'}</span>
              <ArrowRight className="w-4 h-4" />
            </button>
          </form>

          {/* Quick Demo Login Section */}
          <div className="pt-4 border-t border-slate-800 space-y-3">
            <span className="text-xs font-semibold uppercase text-slate-400 tracking-wider block text-center">
              1-Click Instant Login (Pre-Configured Accounts)
            </span>

            {/* Core Role Quick Logins */}
            <div className="grid grid-cols-2 gap-2">
              <button
                type="button"
                onClick={() => quickLogin('assigner@internal.company')}
                className="flex items-center space-x-2.5 p-2.5 bg-slate-800/90 hover:bg-slate-700 border border-slate-700/80 rounded-xl text-left transition-all"
              >
                <Briefcase className="w-4 h-4 text-blue-400 flex-shrink-0" />
                <div>
                  <div className="text-xs font-bold text-slate-100">Assigner</div>
                  <div className="text-[10px] text-slate-400 font-mono">assigner@internal</div>
                </div>
              </button>

              <button
                type="button"
                onClick={() => quickLogin('admin@internal.company')}
                className="flex items-center space-x-2.5 p-2.5 bg-slate-800/90 hover:bg-slate-700 border border-slate-700/80 rounded-xl text-left transition-all"
              >
                <UserCheck className="w-4 h-4 text-purple-400 flex-shrink-0" />
                <div>
                  <div className="text-xs font-bold text-slate-100">Admin</div>
                  <div className="text-[10px] text-slate-400 font-mono">admin@internal</div>
                </div>
              </button>
            </div>

            {/* Interns Roster */}
            <div className="space-y-1.5 pt-1">
              <span className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider block">
                Intern Accounts:
              </span>
              <div className="grid grid-cols-2 gap-2">
                <button
                  type="button"
                  onClick={() => quickLogin('intern@internal.company')}
                  className="flex items-center space-x-2 p-2 bg-slate-800/60 hover:bg-slate-800 border border-slate-800 rounded-lg text-left transition-all"
                >
                  <GraduationCap className="w-3.5 h-3.5 text-emerald-400 flex-shrink-0" />
                  <div className="truncate">
                    <div className="text-xs font-medium text-slate-200 truncate">Aarav Sharma</div>
                    <div className="text-[9px] text-slate-500 font-mono truncate">intern@internal</div>
                  </div>
                </button>

                <button
                  type="button"
                  onClick={() => quickLogin('ananya@internal.company')}
                  className="flex items-center space-x-2 p-2 bg-slate-800/60 hover:bg-slate-800 border border-slate-800 rounded-lg text-left transition-all"
                >
                  <GraduationCap className="w-3.5 h-3.5 text-cyan-400 flex-shrink-0" />
                  <div className="truncate">
                    <div className="text-xs font-medium text-slate-200 truncate">Ananya Sen</div>
                    <div className="text-[9px] text-slate-500 font-mono truncate">ananya@internal</div>
                  </div>
                </button>

                <button
                  type="button"
                  onClick={() => quickLogin('priyanshu@internal.company')}
                  className="flex items-center space-x-2 p-2 bg-slate-800/60 hover:bg-slate-800 border border-slate-800 rounded-lg text-left transition-all"
                >
                  <GraduationCap className="w-3.5 h-3.5 text-blue-400 flex-shrink-0" />
                  <div className="truncate">
                    <div className="text-xs font-medium text-slate-200 truncate">Priyanshu Patel</div>
                    <div className="text-[9px] text-slate-500 font-mono truncate">priyanshu@internal</div>
                  </div>
                </button>

                <button
                  type="button"
                  onClick={() => quickLogin('rohan@internal.company')}
                  className="flex items-center space-x-2 p-2 bg-slate-800/60 hover:bg-slate-800 border border-slate-800 rounded-lg text-left transition-all"
                >
                  <GraduationCap className="w-3.5 h-3.5 text-amber-400 flex-shrink-0" />
                  <div className="truncate">
                    <div className="text-xs font-medium text-slate-200 truncate">Rohan Verma</div>
                    <div className="text-[9px] text-slate-500 font-mono truncate">rohan@internal</div>
                  </div>
                </button>
              </div>
            </div>

            <div className="text-[11px] text-slate-500 text-center font-mono pt-1">
              Default password for all accounts: <span className="text-cyan-400 font-bold">SecretPass123!</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};
