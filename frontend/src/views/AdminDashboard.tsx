import React, { useState, useEffect } from 'react';
import { User, AuditLog, ModelBenchmark, HealthStatus } from '../types';
import { adminApi, authApi, meetingApi, BotStatus } from '../api/client';
import {
  Activity,
  Server,
  Cpu,
  HardDrive,
  Users,
  Shield,
  FileCheck,
  Zap,
  Play,
  CheckCircle2,
  AlertCircle,
  Plus,
  RefreshCw,
  Lock,
  Trash2,
  Bot,
  Key,
  Square
} from 'lucide-react';

export const AdminDashboard: React.FC = () => {
  const [health, setHealth] = useState<HealthStatus | null>(null);
  const [benchmarks, setBenchmarks] = useState<ModelBenchmark[]>([]);
  const [users, setUsers] = useState<User[]>([]);
  const [auditLogs, setAuditLogs] = useState<AuditLog[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [isRunningBench, setIsRunningBench] = useState(false);

  // Google Meet Bot state
  const [botStatus, setBotStatus] = useState<BotStatus | null>(null);
  const [isGoogleAuthed, setIsGoogleAuthed] = useState<boolean>(false);
  const [isLaunchingLogin, setIsLaunchingLogin] = useState<boolean>(false);
  const [botFeedback, setBotFeedback] = useState<string | null>(null);

  // New user form modal
  const [showUserModal, setShowUserModal] = useState(false);
  const [newUserEmail, setNewUserEmail] = useState('');
  const [newUserName, setNewUserName] = useState('');
  const [newUserRole, setNewUserRole] = useState('INTERN');
  const [newUserPass, setNewUserPass] = useState('');

  const checkBotAuth = async () => {
    try {
      const [status, auth] = await Promise.all([
        meetingApi.getBotStatus(),
        meetingApi.getGoogleAuthStatus()
      ]);
      setBotStatus(status);
      setIsGoogleAuthed(auth.authenticated);
    } catch (err) {
      // ignore
    }
  };

  const handleLaunchGoogleLogin = async () => {
    try {
      setIsLaunchingLogin(true);
      setBotFeedback(null);
      const res = await meetingApi.launchGoogleLogin();
      setBotFeedback(res.message);
    } catch (err: any) {
      setBotFeedback(err.response?.data?.detail || 'Failed to open Google Sign-In');
    } finally {
      setIsLaunchingLogin(false);
    }
  };

  const handleStopBot = async () => {
    try {
      await meetingApi.stopBot();
      setBotFeedback('Bot process stopped.');
      await checkBotAuth();
    } catch (err: any) {
      setBotFeedback('Failed to stop bot');
    }
  };

  const loadAdminData = async () => {
    try {
      setIsLoading(true);
      const [h, b, u, a] = await Promise.all([
        adminApi.getHealth(),
        adminApi.getBenchmarks(),
        authApi.getUsers(),
        adminApi.getAuditLogs()
      ]);
      setHealth(h);
      setBenchmarks(b);
      setUsers(u);
      setAuditLogs(a);
      await checkBotAuth();
    } catch (err) {
      console.error('Failed to load admin telemetry', err);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    loadAdminData();
    const interval = setInterval(checkBotAuth, 4000);
    return () => clearInterval(interval);
  }, []);

  const handleRunBenchmark = async () => {
    try {
      setIsRunningBench(true);
      await adminApi.runBenchmark();
      await loadAdminData();
    } catch (err) {
      console.error('Benchmark execution failed', err);
    } finally {
      setIsRunningBench(false);
    }
  };

  const handleCreateUser = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      await authApi.createUser({
        email: newUserEmail,
        full_name: newUserName,
        role: newUserRole,
        password: newUserPass
      });
      setShowUserModal(false);
      setNewUserEmail('');
      setNewUserName('');
      setNewUserPass('');
      await loadAdminData();
    } catch (err) {
      console.error('Failed to register user', err);
    }
  };

  const handleDeleteUser = async (userId: string, userName: string) => {
    if (!window.confirm(`Are you sure you want to permanently delete user "${userName}"?`)) return;
    try {
      await authApi.deleteUser(userId);
      await loadAdminData();
    } catch (err: any) {
      alert(err?.response?.data?.detail || 'Failed to delete user');
    }
  };

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8 space-y-8">
      {/* Top Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between pb-6 border-b border-slate-800 gap-4">
        <div>
          <h1 className="text-2xl font-bold text-slate-100">System Administration & Telemetry</h1>
          <p className="text-sm text-slate-400">
            Real-time health status, CPU model benchmarks, role management, and cryptographic audit records.
          </p>
        </div>
        <div className="flex items-center space-x-3">
          <button
            onClick={() => loadAdminData()}
            className="p-2 bg-slate-800 hover:bg-slate-700 border border-slate-700 rounded-xl text-slate-300 transition-colors"
            title="Refresh telemetry"
          >
            <RefreshCw className="w-4 h-4" />
          </button>
          <button
            onClick={handleRunBenchmark}
            disabled={isRunningBench}
            className="flex items-center space-x-2 bg-gradient-to-r from-cyan-600 to-blue-600 hover:from-cyan-500 hover:to-blue-500 disabled:opacity-50 text-white font-semibold text-xs px-4 py-2.5 rounded-xl shadow-lg shadow-cyan-600/20 transition-all"
          >
            <Zap className="w-4 h-4" />
            <span>{isRunningBench ? 'Running Benchmark...' : 'Run Ollama Benchmark'}</span>
          </button>
        </div>
      </div>

      {/* Google Meet Bot & Account Authentication Card */}
      <div className="p-6 bg-slate-900/90 border border-indigo-500/30 rounded-2xl space-y-4">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
          <div className="flex items-center space-x-3">
            <div className="w-10 h-10 rounded-xl bg-indigo-950/80 border border-indigo-700/60 flex items-center justify-center text-indigo-400">
              <Bot className="w-5 h-5" />
            </div>
            <div>
              <h3 className="font-bold text-slate-100 text-base">Google Meet AI Bot Authentication</h3>
              <p className="text-xs text-slate-400">
                Google Meet requires an authenticated Google Account for host-gated meetings. Authenticate your bot profile once to allow seamless joining.
              </p>
            </div>
          </div>
          <div className="flex items-center gap-2 flex-shrink-0">
            {isGoogleAuthed ? (
              <span className="flex items-center gap-1.5 text-xs font-mono text-emerald-400 bg-emerald-950/80 border border-emerald-800 px-3 py-1.5 rounded-xl">
                <CheckCircle2 className="w-4 h-4 text-emerald-400" />
                Google Account Linked
              </span>
            ) : (
              <button
                type="button"
                onClick={handleLaunchGoogleLogin}
                disabled={isLaunchingLogin}
                className="flex items-center space-x-1.5 px-4 py-2 bg-gradient-to-r from-amber-600 to-amber-500 hover:from-amber-500 hover:to-amber-400 text-white font-semibold text-xs rounded-xl shadow-lg shadow-amber-600/20 transition-all"
              >
                <Key className="w-3.5 h-3.5" />
                <span>{isLaunchingLogin ? 'Opening Chrome...' : '🔑 Sign in Bot to Google'}</span>
              </button>
            )}
            {botStatus?.is_running && (
              <button
                type="button"
                onClick={handleStopBot}
                className="flex items-center space-x-1 px-3 py-2 bg-rose-950/60 hover:bg-rose-900/60 border border-rose-700/60 rounded-xl text-rose-300 text-xs font-semibold"
              >
                <Square className="w-3.5 h-3.5 text-rose-400" />
                <span>Stop Active Bot</span>
              </button>
            )}
          </div>
        </div>

        {botFeedback && (
          <div className="text-xs font-medium text-indigo-300 bg-indigo-950/40 border border-indigo-900/50 p-2.5 rounded-xl">
            ℹ️ {botFeedback}
          </div>
        )}

        <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 pt-2 text-xs text-slate-400 border-t border-slate-800">
          <div>
            <span className="text-slate-500 block">Bot Profile Directory:</span>
            <span className="font-mono text-slate-300">storage/bot_browser_profile</span>
          </div>
          <div>
            <span className="text-slate-500 block">Current Bot Status:</span>
            <span className="font-mono text-slate-300">
              {botStatus?.is_running ? `Running (PID: ${botStatus.pid})` : 'Standby / Idle'}
            </span>
          </div>
          <div>
            <span className="text-slate-500 block">CLI One-Time Login Command:</span>
            <span className="font-mono text-indigo-300 bg-slate-950 px-1.5 py-0.5 rounded border border-slate-800">
              .venv\Scripts\python poc/meet_bot.py --login
            </span>
          </div>
        </div>
      </div>

      {/* Services Health Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        <div className="p-5 bg-slate-900/90 border border-slate-800 rounded-2xl space-y-3">
          <div className="flex items-center justify-between">
            <span className="text-xs font-semibold text-slate-400 uppercase tracking-wider">Database Engine</span>
            <Server className="w-4 h-4 text-cyan-400" />
          </div>
          <div className="flex items-center space-x-2">
            <CheckCircle2 className="w-5 h-5 text-emerald-400" />
            <span className="text-lg font-bold text-slate-100">
              {health?.services?.database === 'ok' || health?.services?.database === 'HEALTHY' ? 'Online' : 'Degraded'}
            </span>
          </div>
          <p className="text-xs text-slate-500">PostgreSQL / SQLite with Async Engine</p>
        </div>

        <div className="p-5 bg-slate-900/90 border border-slate-800 rounded-2xl space-y-3">
          <div className="flex items-center justify-between">
            <span className="text-xs font-semibold text-slate-400 uppercase tracking-wider">Local Ollama LLM</span>
            <Cpu className="w-4 h-4 text-cyan-400" />
          </div>
          <div className="flex items-center space-x-2">
            <CheckCircle2 className="w-5 h-5 text-emerald-400" />
            <span className="text-lg font-bold text-slate-100">{health?.metrics?.ollama_model || 'llama3.2:1b'}</span>
          </div>
          <p className="text-xs text-slate-500">Host CPU AVX2 resident quantization</p>
        </div>

        <div className="p-5 bg-slate-900/90 border border-slate-800 rounded-2xl space-y-3">
          <div className="flex items-center justify-between">
            <span className="text-xs font-semibold text-slate-400 uppercase tracking-wider">Speech STT / TTS</span>
            <Activity className="w-4 h-4 text-cyan-400" />
          </div>
          <div className="flex items-center space-x-2">
            <CheckCircle2 className="w-5 h-5 text-emerald-400" />
            <span className="text-lg font-bold text-slate-100">Piper & Whisper</span>
          </div>
          <p className="text-xs text-slate-500">Local Indian-English synthesis</p>
        </div>

        <div className="p-5 bg-slate-900/90 border border-slate-800 rounded-2xl space-y-3">
          <div className="flex items-center justify-between">
            <span className="text-xs font-semibold text-slate-400 uppercase tracking-wider">Secure Storage</span>
            <HardDrive className="w-4 h-4 text-cyan-400" />
          </div>
          <div className="flex items-center space-x-2">
            <CheckCircle2 className="w-5 h-5 text-emerald-400" />
            <span className="text-lg font-bold text-slate-100">Encrypted Local</span>
          </div>
          <p className="text-xs text-slate-500">30-day retention & audit logs</p>
        </div>
      </div>

      {/* Hardware Benchmark Table */}
      <div className="bg-slate-900/90 border border-slate-800 rounded-2xl p-6 space-y-4">
        <div className="flex items-center justify-between">
          <div className="flex items-center space-x-2">
            <Zap className="w-5 h-5 text-cyan-400" />
            <h3 className="font-bold text-slate-100 text-base">Model Hardware Benchmark History</h3>
          </div>
          <span className="text-xs text-slate-400">Measured on Intel Core i3-1215U (Host CPU)</span>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs">
            <thead className="bg-slate-950/80 text-slate-400 uppercase border-b border-slate-800">
              <tr>
                <th className="p-3">Model</th>
                <th className="p-3">Quantization</th>
                <th className="p-3">Tokens / Sec</th>
                <th className="p-3">Latency (s)</th>
                <th className="p-3">Tokens Out</th>
                <th className="p-3">Target</th>
                <th className="p-3">Status</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-800/60 font-mono text-slate-300">
              {benchmarks.length === 0 ? (
                <tr>
                  <td colSpan={7} className="p-6 text-center text-slate-500 font-sans">
                    No benchmarks logged yet. Click "Run Ollama Benchmark" above to test local inference speed.
                  </td>
                </tr>
              ) : (
                benchmarks.map((b) => (
                  <tr key={b.id} className="hover:bg-slate-800/40">
                    <td className="p-3 font-semibold text-slate-100 font-sans">{b.model_name}</td>
                    <td className="p-3">{b.quantization}</td>
                    <td className="p-3 text-cyan-400 font-bold">{b.tokens_per_second.toFixed(2)} t/s</td>
                    <td className="p-3">{b.wall_clock_seconds.toFixed(2)}s</td>
                    <td className="p-3">{b.completion_tokens}</td>
                    <td className="p-3">{b.hardware_target}</td>
                    <td className="p-3 font-sans">
                      {b.success ? (
                        <span className="text-emerald-400 flex items-center gap-1">
                          <CheckCircle2 className="w-3.5 h-3.5" /> Passed
                        </span>
                      ) : (
                        <span className="text-rose-400 flex items-center gap-1">
                          <AlertCircle className="w-3.5 h-3.5" /> Error
                        </span>
                      )}
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>

      {/* Two Column Section: Users & Audit Trail */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
        {/* User Management */}
        <div className="bg-slate-900/90 border border-slate-800 rounded-2xl p-6 space-y-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center space-x-2">
              <Users className="w-5 h-5 text-cyan-400" />
              <h3 className="font-bold text-slate-100 text-base">Users & Access Control ({users.length})</h3>
            </div>
            <button
              onClick={() => setShowUserModal(true)}
              className="flex items-center space-x-1.5 px-3 py-1.5 bg-slate-800 hover:bg-slate-700 border border-slate-700 text-white rounded-lg text-xs font-medium transition-colors"
            >
              <Plus className="w-3.5 h-3.5" />
              <span>Add User</span>
            </button>
          </div>

          <div className="space-y-2">
            {users.map((u) => (
              <div
                key={u.id}
                className="flex items-center justify-between p-3 bg-slate-950/60 border border-slate-800 rounded-xl text-xs"
              >
                <div>
                  <div className="font-semibold text-slate-200">{u.full_name}</div>
                  <div className="text-slate-400 font-mono mt-0.5">{u.email}</div>
                </div>
                <div className="flex items-center space-x-2">
                  <span className="bg-slate-800 text-slate-300 px-2 py-0.5 rounded font-mono font-medium">
                    {u.role}
                  </span>
                  <button
                    onClick={() => handleDeleteUser(u.id, u.full_name)}
                    className="p-1 text-slate-500 hover:text-rose-400 hover:bg-rose-950/50 rounded transition-colors"
                    title={`Delete ${u.full_name}`}
                  >
                    <Trash2 className="w-3.5 h-3.5" />
                  </button>
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Audit Logs Trail */}
        <div className="bg-slate-900/90 border border-slate-800 rounded-2xl p-6 space-y-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center space-x-2">
              <FileCheck className="w-5 h-5 text-cyan-400" />
              <h3 className="font-bold text-slate-100 text-base">Security & Evaluation Audit Trail</h3>
            </div>
            <span className="text-xs text-slate-500 font-mono">Immutable</span>
          </div>

          <div className="space-y-2 max-h-80 overflow-y-auto pr-1">
            {auditLogs.length === 0 ? (
              <p className="text-xs text-slate-500 italic p-4 text-center">No audit logs recorded yet.</p>
            ) : (
              auditLogs.map((log) => (
                <div
                  key={log.id}
                  className="p-3 bg-slate-950/60 border border-slate-800 rounded-xl text-xs space-y-1"
                >
                  <div className="flex items-center justify-between">
                    <span className="font-bold font-mono text-cyan-400">{log.action}</span>
                    <span className="text-[10px] text-slate-500">
                      {new Date(log.created_at).toLocaleTimeString()}
                    </span>
                  </div>
                  <div className="text-slate-300">
                    Actor: <span className="text-slate-400">{log.actor_email}</span> | Resource:{' '}
                    <span className="font-mono text-slate-400">{log.resource_type}</span>
                  </div>
                  {log.details_json && (
                    <div className="text-[11px] font-mono text-slate-500 truncate">{log.details_json}</div>
                  )}
                </div>
              ))
            )}
          </div>
        </div>
      </div>

      {/* MODAL: Create User */}
      {showUserModal && (
        <div className="fixed inset-0 z-50 bg-black/80 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="bg-slate-900 border border-slate-800 rounded-2xl w-full max-w-md p-6 space-y-4">
            <h3 className="text-lg font-bold text-slate-100">Add User to Workspace</h3>
            <form onSubmit={handleCreateUser} className="space-y-3">
              <div>
                <label className="block text-xs font-semibold text-slate-400 uppercase tracking-wider mb-1">
                  Full Name
                </label>
                <input
                  type="text"
                  required
                  value={newUserName}
                  onChange={(e) => setNewUserName(e.target.value)}
                  placeholder="e.g. Maya Sharma"
                  className="w-full bg-slate-950 border border-slate-800 rounded-xl px-4 py-2 text-sm text-slate-100 focus:outline-none focus:border-cyan-500"
                />
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-400 uppercase tracking-wider mb-1">
                  Email Address
                </label>
                <input
                  type="email"
                  required
                  value={newUserEmail}
                  onChange={(e) => setNewUserEmail(e.target.value)}
                  placeholder="name@internal.company"
                  className="w-full bg-slate-950 border border-slate-800 rounded-xl px-4 py-2 text-sm text-slate-100 focus:outline-none focus:border-cyan-500"
                />
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-400 uppercase tracking-wider mb-1">
                  Role
                </label>
                <select
                  value={newUserRole}
                  onChange={(e) => setNewUserRole(e.target.value)}
                  className="w-full bg-slate-950 border border-slate-800 rounded-xl px-4 py-2 text-sm text-slate-100 focus:outline-none focus:border-cyan-500"
                >
                  <option value="INTERN">Intern</option>
                  <option value="ASSIGNER">Task Assigner</option>
                  <option value="ADMIN">Administrator</option>
                </select>
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-400 uppercase tracking-wider mb-1">
                  Initial Password
                </label>
                <input
                  type="password"
                  required
                  value={newUserPass}
                  onChange={(e) => setNewUserPass(e.target.value)}
                  className="w-full bg-slate-950 border border-slate-800 rounded-xl px-4 py-2 text-sm text-slate-100 focus:outline-none focus:border-cyan-500"
                />
              </div>

              <div className="flex justify-end space-x-2 pt-2">
                <button
                  type="button"
                  onClick={() => setShowUserModal(false)}
                  className="px-4 py-2 text-sm text-slate-400 hover:text-slate-200"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className="px-5 py-2 bg-cyan-600 hover:bg-cyan-500 text-white rounded-xl text-sm font-semibold shadow"
                >
                  Create User
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
};
