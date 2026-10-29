import React, { useState } from 'react';
import { useAuth } from '../context/AuthContext';
import { authApi } from '../api/client';
import {
  Shield,
  Lock,
  Mail,
  ArrowRight,
  Briefcase,
  GraduationCap,
  UserPlus,
  Eye,
  EyeOff,
  Sparkles,
  CheckCircle2
} from 'lucide-react';

type PortalMode = 'assigner' | 'intern' | 'register';

export const LoginView: React.FC = () => {
  const { login } = useAuth();
  const [portal, setPortal] = useState<PortalMode>('assigner');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [fullName, setFullName] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [successMsg, setSuccessMsg] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(false);

  const switchPortal = (newPortal: PortalMode) => {
    setPortal(newPortal);
    setError(null);
    setSuccessMsg(null);
    setEmail('');
    setPassword('');
    setFullName('');
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setSuccessMsg(null);
    setIsLoading(true);

    try {
      if (portal === 'register') {
        await authApi.register({
          email: email.trim().toLowerCase(),
          full_name: fullName.trim(),
          password,
          role: 'INTERN'
        });
        setSuccessMsg('Intern registered successfully! Signing in to workspace...');
        await login(email.trim().toLowerCase(), password);
      } else {
        await login(email.trim().toLowerCase(), password);
      }
    } catch (err: any) {
      const msg = err?.response?.data?.detail || err?.message || 'Authentication failed. Please check your credentials.';
      setError(typeof msg === 'string' ? msg : JSON.stringify(msg));
    } finally {
      setIsLoading(false);
    }
  };

  // Safe pre-fill helpers for evaluation without showing password in plaintext
  const handlePrefillAssignerDemo = () => {
    setEmail('assigner@internal.company');
    setPassword('SecretPass123!');
  };

  const handlePrefillInternDemo = () => {
    setEmail('intern@internal.company');
    setPassword('SecretPass123!');
  };

  return (
    <div className="min-h-screen flex flex-col justify-center py-12 px-4 sm:px-6 lg:px-8 relative overflow-hidden bg-slate-950">
      {/* Background ambient lighting */}
      <div className="absolute -top-40 -left-40 w-96 h-96 rounded-full bg-cyan-500/10 blur-3xl pointer-events-none" />
      <div className="absolute -bottom-40 -right-40 w-96 h-96 rounded-full bg-indigo-500/10 blur-3xl pointer-events-none" />
      <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[600px] h-[600px] rounded-full bg-blue-600/5 blur-3xl pointer-events-none" />

      {/* Brand Header */}
      <div className="sm:mx-auto sm:w-full sm:max-w-md text-center relative z-10">
        <div className="mx-auto w-16 h-16 rounded-2xl bg-gradient-to-tr from-cyan-500 via-blue-600 to-indigo-600 flex items-center justify-center text-white shadow-xl shadow-cyan-500/30 border border-white/20 mb-4 transition-transform hover:scale-105">
          <Shield className="w-9 h-9 drop-shadow-md" />
        </div>
        <h1 className="text-3xl font-black text-white tracking-tight">Task Reviewer AI</h1>
        <p className="mt-2 text-xs sm:text-sm text-slate-400">
          Autonomous Task Briefing, Evidence Evaluation & Voice Review Platform
        </p>
      </div>

      {/* Main Login Card */}
      <div className="mt-8 sm:mx-auto sm:w-full sm:max-w-md relative z-10">
        <div className="glass-card neo-surface py-7 px-6 sm:px-9 rounded-3xl space-y-6">
          {/* Portal Switcher Tabs */}
          <div className="grid grid-cols-3 p-1 rounded-2xl neo-inset border border-white/[0.06] text-xs font-bold">
            <button
              type="button"
              onClick={() => switchPortal('assigner')}
              className={`flex items-center justify-center space-x-1.5 py-2.5 rounded-xl transition-all ${
                portal === 'assigner'
                  ? 'glass-btn-primary text-white shadow-md'
                  : 'text-slate-400 hover:text-slate-200'
              }`}
            >
              <Briefcase className="w-3.5 h-3.5 flex-shrink-0" />
              <span>Assigner</span>
            </button>

            <button
              type="button"
              onClick={() => switchPortal('intern')}
              className={`flex items-center justify-center space-x-1.5 py-2.5 rounded-xl transition-all ${
                portal === 'intern'
                  ? 'glass-btn-primary text-white shadow-md'
                  : 'text-slate-400 hover:text-slate-200'
              }`}
            >
              <GraduationCap className="w-3.5 h-3.5 flex-shrink-0" />
              <span>Intern</span>
            </button>

            <button
              type="button"
              onClick={() => switchPortal('register')}
              className={`flex items-center justify-center space-x-1.5 py-2.5 rounded-xl transition-all ${
                portal === 'register'
                  ? 'glass-btn-primary text-white shadow-md'
                  : 'text-slate-400 hover:text-slate-200'
              }`}
            >
              <UserPlus className="w-3.5 h-3.5 flex-shrink-0" />
              <span>Register</span>
            </button>
          </div>

          {/* Portal Context Banner */}
          <div className="space-y-1">
            <div className="flex items-center space-x-2">
              <span className={`text-[10px] font-bold uppercase tracking-wider px-2 py-0.5 rounded-full neo-inset ${
                portal === 'assigner'
                  ? 'text-cyan-400 border border-cyan-500/30'
                  : portal === 'intern'
                  ? 'text-emerald-400 border border-emerald-500/30'
                  : 'text-purple-400 border border-purple-500/30'
              }`}>
                {portal === 'assigner' ? 'Leadership Portal' : portal === 'intern' ? 'Intern Portal' : 'New Intern Registration'}
              </span>
            </div>
            <h2 className="text-lg font-bold text-slate-100">
              {portal === 'assigner' && 'Assigner & Reviewer Login'}
              {portal === 'intern' && 'Intern Workspace Login'}
              {portal === 'register' && 'Register New Intern'}
            </h2>
            <p className="text-xs text-slate-400">
              {portal === 'assigner' && 'Sign in to create tasks, dispatch Google Meet AI bots, and inspect deliverables.'}
              {portal === 'intern' && 'Sign in to view your task briefs, schedule voice reviews, and submit code.'}
              {portal === 'register' && 'Create your intern account to receive task assignments and start evaluations.'}
            </p>
          </div>

          {/* Alerts */}
          {error && (
            <div className="p-3 bg-rose-950/70 border border-rose-800 text-rose-300 text-xs rounded-xl">
              {error}
            </div>
          )}

          {successMsg && (
            <div className="p-3 bg-emerald-950/70 border border-emerald-800 text-emerald-300 text-xs rounded-xl flex items-center space-x-2">
              <CheckCircle2 className="w-4 h-4 text-emerald-400 flex-shrink-0" />
              <span>{successMsg}</span>
            </div>
          )}

          {/* Form */}
          <form onSubmit={handleSubmit} className="space-y-4">
            {portal === 'register' && (
              <div>
                <label className="block text-xs font-semibold uppercase text-slate-400 tracking-wider mb-1">
                  Full Name & Title
                </label>
                <input
                  type="text"
                  required
                  value={fullName}
                  onChange={(e) => setFullName(e.target.value)}
                  placeholder="e.g. Maya Sharma (AI/ML Intern)"
                  className="w-full neo-inset rounded-xl px-4 py-2.5 text-sm text-slate-200 placeholder-slate-500 focus:outline-none focus:border-cyan-400/50 transition-colors"
                />
              </div>
            )}

            <div>
              <label className="block text-xs font-semibold uppercase text-slate-400 tracking-wider mb-1">
                {portal === 'intern' ? 'Intern Email Address' : portal === 'assigner' ? 'Work / Staff Email' : 'Email Address'}
              </label>
              <div className="relative">
                <Mail className="w-5 h-5 absolute left-3 top-3 text-slate-500" />
                <input
                  type="email"
                  required
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  placeholder={portal === 'assigner' ? 'lead@internal.company' : 'intern@internal.company'}
                  className="w-full neo-inset rounded-xl pl-10 pr-4 py-2.5 text-sm text-slate-200 placeholder-slate-500 focus:outline-none focus:border-cyan-400/50 transition-colors"
                />
              </div>
            </div>

            <div>
              <div className="flex items-center justify-between mb-1">
                <label className="block text-xs font-semibold uppercase text-slate-400 tracking-wider">
                  Password
                </label>
                <button
                  type="button"
                  onClick={() => setShowPassword(!showPassword)}
                  className="text-[11px] text-slate-400 hover:text-slate-200 flex items-center space-x-1"
                >
                  {showPassword ? <EyeOff className="w-3.5 h-3.5" /> : <Eye className="w-3.5 h-3.5" />}
                  <span>{showPassword ? 'Hide' : 'Show'}</span>
                </button>
              </div>
              <div className="relative">
                <Lock className="w-5 h-5 absolute left-3 top-3 text-slate-500" />
                <input
                  type={showPassword ? 'text' : 'password'}
                  required
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  placeholder="••••••••••••"
                  className="w-full neo-inset rounded-xl pl-10 pr-10 py-2.5 text-sm text-slate-200 placeholder-slate-500 focus:outline-none focus:border-cyan-400/50 transition-colors"
                />
              </div>
            </div>

            <button
              type="submit"
              disabled={isLoading}
              className="w-full flex items-center justify-center space-x-2 glass-btn-primary text-white font-bold py-3 rounded-xl shadow-lg shadow-cyan-500/25 transition-all disabled:opacity-50 active:scale-95"
            >
              <span>
                {isLoading
                  ? 'Processing...'
                  : portal === 'register'
                  ? 'Complete Registration'
                  : portal === 'assigner'
                  ? 'Sign In to Assigner Portal'
                  : 'Sign In to Intern Workspace'}
              </span>
              <ArrowRight className="w-4 h-4" />
            </button>
          </form>

          {/* Quick Demo Fill Helpers (Programmatic, zero exposed passwords or profiles) */}
          <div className="pt-3 border-t border-white/[0.08] flex items-center justify-between text-xs text-slate-400">
            {portal === 'assigner' ? (
              <>
                <span>Testing credentials?</span>
                <button
                  type="button"
                  onClick={handlePrefillAssignerDemo}
                  className="text-cyan-400 hover:text-cyan-300 font-semibold transition-colors"
                >
                  Fill Assigner Demo
                </button>
              </>
            ) : portal === 'intern' ? (
              <>
                <button
                  type="button"
                  onClick={() => switchPortal('register')}
                  className="text-slate-400 hover:text-slate-200 transition-colors"
                >
                  Need an account? <span className="text-emerald-400 font-semibold">Register here</span>
                </button>
                <button
                  type="button"
                  onClick={handlePrefillInternDemo}
                  className="text-cyan-400 hover:text-cyan-300 font-semibold transition-colors"
                >
                  Fill Demo Intern
                </button>
              </>
            ) : (
              <div className="w-full text-center">
                <button
                  type="button"
                  onClick={() => switchPortal('intern')}
                  className="text-slate-400 hover:text-slate-200 transition-colors"
                >
                  Already registered? <span className="text-cyan-400 font-semibold">Back to Intern Login</span>
                </button>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};
