import React, { useState, useEffect } from 'react';
import { useAuth } from '../context/AuthContext';
import { Task, Meeting, User } from '../types';
import { taskApi, meetingApi, authApi, BotStatus } from '../api/client';
import {
  Layers,
  CheckCircle2,
  Clock,
  Video,
  Bot,
  Users,
  ArrowRight,
  TrendingUp,
  Sparkles,
  ExternalLink,
  Play,
  Square,
  Volume2,
  Calendar,
  FileText,
  ShieldCheck,
  ChevronRight,
  Activity,
  AlertTriangle,
  RefreshCw,
  Trash2,
  GraduationCap,
  UserPlus
} from 'lucide-react';

interface DedicatedDashboardProps {
  onNavigateToWorkspace: (taskId?: string) => void;
}

export const DedicatedDashboard: React.FC<DedicatedDashboardProps> = ({ onNavigateToWorkspace }) => {
  const { user } = useAuth();
  const [tasks, setTasks] = useState<Task[]>([]);
  const [meetings, setMeetings] = useState<Meeting[]>([]);
  const [interns, setInterns] = useState<User[]>([]);
  const [botStatus, setBotStatus] = useState<BotStatus | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  // Quick Dispatch Bot State
  const [quickMeetUrl, setQuickMeetUrl] = useState('https://meet.google.com/meet/rqp-ctfg-nri');
  const [selectedTaskId, setSelectedTaskId] = useState<string>('');
  const [isSpeakingMode, setIsSpeakingMode] = useState(true);
  const [isDispatching, setIsDispatching] = useState(false);
  const [dispatchFeedback, setDispatchFeedback] = useState<string | null>(null);

  // Selected Meeting Modal for Transcripts
  const [selectedMeeting, setSelectedMeeting] = useState<Meeting | null>(null);

  // Intern Roster & Deletion Modal state
  const [showInternRosterModal, setShowInternRosterModal] = useState(false);
  const [deletingInternId, setDeletingInternId] = useState<string | null>(null);
  const [rosterFeedback, setRosterFeedback] = useState<string | null>(null);
  const [rosterError, setRosterError] = useState<string | null>(null);

  const handleDeleteIntern = async (internId: string, internName: string) => {
    if (!window.confirm(`Are you sure you want to permanently delete intern "${internName}"? Any tasks assigned to them will be unassigned.`)) {
      return;
    }
    setDeletingInternId(internId);
    setRosterError(null);
    setRosterFeedback(null);
    try {
      const res = await authApi.deleteUser(internId);
      setRosterFeedback(res.message || `Intern "${internName}" removed successfully.`);
      await loadDashboardData();
    } catch (err: any) {
      const msg = err?.response?.data?.detail || err?.message || 'Failed to delete intern';
      setRosterError(typeof msg === 'string' ? msg : JSON.stringify(msg));
    } finally {
      setDeletingInternId(null);
    }
  };

  const loadDashboardData = async () => {
    try {
      setIsLoading(true);
      const [tasksData, meetingsData, botStatusData, usersData] = await Promise.all([
        taskApi.list().catch(() => []),
        meetingApi.listAll().catch(() => []),
        meetingApi.getBotStatus().catch(() => null),
        authApi.getUsers().catch(() => [])
      ]);
      setTasks(tasksData);
      setMeetings(meetingsData);
      setBotStatus(botStatusData);
      setInterns(usersData.filter((u) => u.role === 'INTERN'));
    } catch (err) {
      console.error('Failed to load dashboard data', err);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    loadDashboardData();
    const interval = setInterval(async () => {
      try {
        const s = await meetingApi.getBotStatus();
        setBotStatus(s);
      } catch (e) {
        // ignore
      }
    }, 4000);
    return () => clearInterval(interval);
  }, []);

  const handleQuickDispatchBot = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!quickMeetUrl.trim()) return;
    try {
      setIsDispatching(true);
      setDispatchFeedback(null);
      const res = await meetingApi.launchDirectBot(quickMeetUrl.trim(), isSpeakingMode, selectedTaskId || undefined);
      setDispatchFeedback(res.message);
      setQuickMeetUrl('');
      const updatedStatus = await meetingApi.getBotStatus();
      setBotStatus(updatedStatus);
    } catch (err: any) {
      setDispatchFeedback(err?.response?.data?.detail || 'Failed to dispatch bot');
    } finally {
      setIsDispatching(false);
    }
  };

  const handleStopBot = async () => {
    try {
      await meetingApi.stopBot();
      const s = await meetingApi.getBotStatus();
      setBotStatus(s);
      setDispatchFeedback('Bot dismissed from meeting.');
    } catch (err) {
      console.error('Failed to stop bot', err);
    }
  };

  // Metrics Calculations
  const totalTasks = tasks.length;
  const passedTasks = tasks.filter((t) => t.status === 'PASSED').length;
  const inProgressTasks = tasks.filter((t) => ['IN_PROGRESS', 'UNDER_REVIEW', 'BRIEFING_COMPLETED'].includes(t.status)).length;
  const scheduledTasks = tasks.filter((t) => t.status === 'BRIEFING_SCHEDULED').length;
  const passRate = totalTasks > 0 ? Math.round((passedTasks / totalTasks) * 100) : 100;

  const totalMeetings = meetings.length;
  const completedMeetings = meetings.filter((m) => m.status === 'COMPLETED').length;

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8 space-y-8 animate-fadeIn">
      {/* Top Hero Banner - Glassmorphic with Neon Accent */}
      <div className="relative overflow-hidden rounded-3xl glass-card neo-surface p-6 sm:p-8">
        <div className="absolute -top-24 -right-24 w-80 h-80 rounded-full bg-cyan-500/10 blur-3xl pointer-events-none" />
        <div className="absolute -bottom-24 -left-24 w-80 h-80 rounded-full bg-indigo-500/10 blur-3xl pointer-events-none" />

        <div className="relative z-10 flex flex-col md:flex-row md:items-center justify-between gap-6">
          <div className="space-y-2">
            <div className="flex items-center space-x-2 text-xs font-semibold uppercase tracking-wider text-cyan-400">
              <Sparkles className="w-4 h-4 animate-pulse" />
              <span>Executive Command Overview</span>
            </div>
            <h1 className="text-2xl sm:text-3xl font-extrabold text-white tracking-tight">
              Welcome back, <span className="bg-clip-text text-transparent bg-gradient-to-r from-cyan-400 via-blue-400 to-indigo-300">{user?.full_name}</span>
            </h1>
            <p className="text-sm text-slate-300 max-w-2xl leading-relaxed">
              Supervise AI task reviews, review automated Google Meet briefings, and inspect rubric evaluations in real time.
            </p>
          </div>

          <div className="flex flex-wrap items-center gap-3">
            <button
              onClick={() => onNavigateToWorkspace()}
              className="flex items-center space-x-2 px-5 py-2.5 rounded-xl text-sm font-bold text-white glass-btn-primary shadow-lg shadow-cyan-500/20 active:scale-95 transition-all"
            >
              <span>Manage Tasks in Workspace</span>
              <ArrowRight className="w-4 h-4" />
            </button>
            <button
              onClick={loadDashboardData}
              disabled={isLoading}
              className="p-2.5 rounded-xl neo-btn text-slate-300 hover:text-white transition-colors"
              title="Refresh Data"
            >
              <RefreshCw className={`w-4 h-4 ${isLoading ? 'animate-spin text-cyan-400' : ''}`} />
            </button>
          </div>
        </div>
      </div>

      {/* 4 Neomorphic KPI Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-5">
        {/* KPI 1: Active Tasks */}
        <div className="glass-card-interactive neo-surface rounded-2xl p-5 relative overflow-hidden">
          <div className="flex items-center justify-between">
            <span className="text-xs font-semibold uppercase tracking-wider text-slate-400">Total Tasks</span>
            <div className="w-9 h-9 rounded-xl bg-cyan-500/10 border border-cyan-500/20 flex items-center justify-center text-cyan-400">
              <Layers className="w-5 h-5" />
            </div>
          </div>
          <div className="mt-4 flex items-baseline justify-between">
            <span className="text-3xl font-black text-white">{totalTasks}</span>
            <span className="text-xs font-medium text-cyan-400 neo-inset px-2 py-0.5 rounded-full">
              {inProgressTasks} In Progress
            </span>
          </div>
          <div className="mt-3 pt-3 border-t border-white/[0.06] flex items-center justify-between text-[11px] text-slate-400">
            <span>Scheduled: <strong className="text-slate-200">{scheduledTasks}</strong></span>
            <span>Completed: <strong className="text-emerald-400">{passedTasks}</strong></span>
          </div>
        </div>

        {/* KPI 2: Pass Rate */}
        <div className="glass-card-interactive neo-surface rounded-2xl p-5 relative overflow-hidden">
          <div className="flex items-center justify-between">
            <span className="text-xs font-semibold uppercase tracking-wider text-slate-400">Objective Pass Rate</span>
            <div className="w-9 h-9 rounded-xl bg-emerald-500/10 border border-emerald-500/20 flex items-center justify-center text-emerald-400">
              <CheckCircle2 className="w-5 h-5" />
            </div>
          </div>
          <div className="mt-4 flex items-baseline justify-between">
            <span className="text-3xl font-black text-emerald-400">{passRate}%</span>
            <span className="text-xs font-medium text-emerald-400 neo-inset px-2 py-0.5 rounded-full flex items-center gap-1">
              <TrendingUp className="w-3 h-3" /> Deterministic
            </span>
          </div>
          <div className="mt-3 pt-3 border-t border-white/[0.06] flex items-center justify-between text-[11px] text-slate-400">
            <span>Pass Threshold: <strong className="text-slate-200">100% Tests</strong></span>
            <span>Rubric Weight: <strong className="text-slate-200">Enforced</strong></span>
          </div>
        </div>

        {/* KPI 3: Google Meet Sessions */}
        <div className="glass-card-interactive neo-surface rounded-2xl p-5 relative overflow-hidden">
          <div className="flex items-center justify-between">
            <span className="text-xs font-semibold uppercase tracking-wider text-slate-400">Google Meet Sessions</span>
            <div className="w-9 h-9 rounded-xl bg-indigo-500/10 border border-indigo-500/20 flex items-center justify-center text-indigo-400">
              <Video className="w-5 h-5" />
            </div>
          </div>
          <div className="mt-4 flex items-baseline justify-between">
            <span className="text-3xl font-black text-indigo-300">{totalMeetings}</span>
            <span className="text-xs font-medium text-indigo-400 neo-inset px-2 py-0.5 rounded-full">
              {completedMeetings} Completed
            </span>
          </div>
          <div className="mt-3 pt-3 border-t border-white/[0.06] flex items-center justify-between text-[11px] text-slate-400">
            <span>AI Diarized: <strong className="text-slate-200">Automated</strong></span>
            <span>Recording: <strong className="text-slate-200">MP4 Synced</strong></span>
          </div>
        </div>

        {/* KPI 4: Active Interns */}
        <div
          onClick={() => setShowInternRosterModal(true)}
          className="glass-card-interactive neo-surface rounded-2xl p-5 relative overflow-hidden cursor-pointer group"
          title="Click to view and manage intern roster"
        >
          <div className="flex items-center justify-between">
            <span className="text-xs font-semibold uppercase tracking-wider text-slate-400 group-hover:text-purple-400 transition-colors">
              Intern Roster (Manage)
            </span>
            <div className="w-9 h-9 rounded-xl bg-purple-500/10 border border-purple-500/20 flex items-center justify-center text-purple-400 group-hover:scale-110 transition-transform">
              <Users className="w-5 h-5" />
            </div>
          </div>
          <div className="mt-4 flex items-baseline justify-between">
            <span className="text-3xl font-black text-purple-300">{interns.length}</span>
            <span className="text-xs font-medium text-purple-400 neo-inset px-2 py-0.5 rounded-full">
              Active Interns
            </span>
          </div>
          <div className="mt-3 pt-3 border-t border-white/[0.06] flex items-center justify-between text-[11px] text-slate-400">
            <span>Click to: <strong className="text-purple-300">View & Delete</strong></span>
            <span>Total: <strong className="text-emerald-400">{interns.length} Registered</strong></span>
          </div>
        </div>
      </div>

      {/* Middle Section: Google Meet AI Bot Command Hub */}
      <div className="glass-card neo-surface rounded-3xl p-6 sm:p-7 space-y-6">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-4 border-b border-white/[0.08]">
          <div className="flex items-center space-x-3">
            <div className="w-11 h-11 rounded-2xl bg-gradient-to-br from-indigo-500 to-purple-600 flex items-center justify-center text-white shadow-lg shadow-indigo-500/25">
              <Bot className="w-6 h-6" />
            </div>
            <div>
              <h2 className="text-lg font-bold text-white flex items-center gap-2.5">
                Google Meet Autonomous AI Agent
                <span className="text-[11px] font-mono px-2 py-0.5 rounded-full bg-indigo-950/80 border border-indigo-500/40 text-indigo-300">
                  Subha Neural Voice
                </span>
              </h2>
              <p className="text-xs text-slate-400">
                Directly dispatches into any Google Meet link or code. Speaks aloud, answers questions, and records speaker-diarized transcripts.
              </p>
            </div>
          </div>

          <div className="flex items-center gap-2">
            {botStatus?.is_running ? (
              <div className="flex items-center space-x-2 neo-inset px-3.5 py-1.5 rounded-full border border-emerald-500/30 text-emerald-400 text-xs font-mono">
                <span className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse" />
                <span>
                  {botStatus.status === 'in_call_recording'
                    ? 'In-Call (Speaking & Recording)'
                    : botStatus.status === 'joining'
                    ? 'Joining Google Meet...'
                    : `Bot Active (${botStatus.status || 'Active'})`}
                </span>
                {botStatus.meet_url && (
                  <a
                    href={botStatus.meet_url}
                    target="_blank"
                    rel="noreferrer"
                    className="ml-1 text-cyan-400 hover:text-cyan-300"
                    title="Open Meeting in Browser"
                  >
                    <ExternalLink className="w-3.5 h-3.5" />
                  </a>
                )}
              </div>
            ) : (
              <div className="flex items-center space-x-2 neo-inset px-3 py-1.5 rounded-full border border-slate-700/60 text-slate-400 text-xs font-mono">
                <span className="w-2 h-2 rounded-full bg-slate-500" />
                <span>Agent Standby</span>
              </div>
            )}

            {botStatus?.is_running && (
              <button
                onClick={handleStopBot}
                className="flex items-center space-x-1.5 px-3 py-1.5 rounded-xl bg-rose-950/80 hover:bg-rose-900 border border-rose-700/60 text-rose-200 text-xs font-bold transition-colors"
              >
                <Square className="w-3.5 h-3.5 text-rose-400" />
                <span>Dismiss Bot</span>
              </button>
            )}
          </div>
        </div>

        {/* Quick Launch Form */}
        <form onSubmit={handleQuickDispatchBot} className="space-y-4">
          <div className="flex flex-col sm:flex-row items-stretch gap-3">
            <div className="relative flex-1">
              <input
                type="text"
                placeholder="Enter Google Meet link or code (e.g. rqp-ctfg-nri or https://meet.google.com/rqp-ctfg-nri)"
                value={quickMeetUrl}
                onChange={(e) => setQuickMeetUrl(e.target.value)}
                className="w-full neo-inset rounded-xl px-4 py-3 text-sm text-white placeholder-slate-500 focus:outline-none focus:border-cyan-400/50 font-mono transition-colors"
              />
            </div>

            <div className="sm:w-64">
              <select
                value={selectedTaskId}
                onChange={(e) => setSelectedTaskId(e.target.value)}
                className="w-full h-full neo-inset rounded-xl px-3 py-3 text-xs text-slate-200 bg-slate-900/90 focus:outline-none focus:border-cyan-400/50 transition-colors border border-white/[0.08]"
                title="Select Task to Ground Subha's Knowledge with Uploaded Documents"
              >
                <option value="">Attach Task Knowledge (Optional)</option>
                {tasks.map((t) => (
                  <option key={t.id} value={t.id}>
                    {t.title.length > 32 ? t.title.substring(0, 32) + '...' : t.title}
                  </option>
                ))}
              </select>
            </div>

            <label className="flex items-center gap-2 cursor-pointer text-xs font-semibold select-none neo-surface px-4 py-3 rounded-xl border border-white/[0.08] hover:border-indigo-500/50 transition-colors">
              <input
                type="checkbox"
                checked={isSpeakingMode}
                onChange={(e) => setIsSpeakingMode(e.target.checked)}
                className="w-4 h-4 rounded text-indigo-600 focus:ring-indigo-500 bg-slate-900 border-slate-700 cursor-pointer"
              />
              <span className={isSpeakingMode ? 'text-indigo-300 font-bold flex items-center gap-1.5' : 'text-slate-400 flex items-center gap-1.5'}>
                <Volume2 className={`w-4 h-4 ${isSpeakingMode ? 'text-indigo-400' : 'text-slate-500'}`} />
                {isSpeakingMode ? 'Interactive Speaking Bot' : 'Silent Recording Bot'}
              </span>
            </label>

            <button
              type="submit"
              disabled={isDispatching || !quickMeetUrl.trim()}
              className="flex items-center justify-center space-x-2 px-6 py-3 rounded-xl text-sm font-bold text-white glass-btn-primary shadow-lg shadow-indigo-500/20 disabled:opacity-50 transition-all active:scale-95"
            >
              <Bot className="w-4 h-4" />
              <span>{isDispatching ? 'Dispatching...' : 'Dispatch Bot into Call'}</span>
            </button>
          </div>

          {dispatchFeedback && (
            <div className="p-3 rounded-xl neo-inset border border-cyan-500/30 text-xs text-cyan-300 flex items-center gap-2">
              <CheckCircle2 className="w-4 h-4 text-cyan-400 flex-shrink-0" />
              <span>{dispatchFeedback}</span>
            </div>
          )}
        </form>
      </div>

      {/* Two Column Grid: Task Portfolio & Recent Meetings */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
        {/* Left Column: Task Portfolio Overview */}
        <div className="glass-card neo-surface rounded-3xl p-6 space-y-5">
          <div className="flex items-center justify-between pb-3 border-b border-white/[0.08]">
            <div className="flex items-center space-x-2">
              <Layers className="w-4 h-4 text-cyan-400" />
              <h3 className="text-sm font-bold uppercase tracking-wider text-white">Active Task Portfolio</h3>
            </div>
            <button
              onClick={() => onNavigateToWorkspace()}
              className="text-xs text-cyan-400 hover:text-cyan-300 flex items-center gap-1 font-semibold"
            >
              <span>View All</span>
              <ChevronRight className="w-3.5 h-3.5" />
            </button>
          </div>

          {tasks.length === 0 ? (
            <div className="p-8 text-center text-sm text-slate-500 italic">No tasks created yet. Click "Manage Tasks in Workspace" to get started.</div>
          ) : (
            <div className="space-y-3">
              {tasks.slice(0, 5).map((task) => {
                const isPassed = task.status === 'PASSED';
                const isInProgress = ['IN_PROGRESS', 'UNDER_REVIEW'].includes(task.status);
                const isScheduled = task.status === 'BRIEFING_SCHEDULED';

                return (
                  <div
                    key={task.id}
                    onClick={() => onNavigateToWorkspace(task.id)}
                    className="p-4 rounded-2xl glass-card-interactive cursor-pointer flex items-center justify-between gap-4 group"
                  >
                    <div className="space-y-1 min-w-0 flex-1">
                      <div className="flex items-center space-x-2">
                        <h4 className="text-sm font-bold text-slate-100 group-hover:text-cyan-400 transition-colors truncate">
                          {task.title}
                        </h4>
                      </div>
                      <div className="flex items-center gap-3 text-xs text-slate-400">
                        <span>Intern: <strong className="text-slate-300">{task.intern?.full_name || 'Unassigned'}</strong></span>
                        <span>•</span>
                        <span>Docs: {task.documents?.length || 0}</span>
                      </div>
                    </div>

                    <div className="flex items-center space-x-3 flex-shrink-0">
                      <span
                        className={`text-[11px] font-semibold px-2.5 py-1 rounded-full neo-inset ${
                          isPassed
                            ? 'text-emerald-400 border border-emerald-500/30'
                            : isInProgress
                            ? 'text-amber-300 border border-amber-500/30'
                            : isScheduled
                            ? 'text-cyan-300 border border-cyan-500/30'
                            : 'text-slate-400 border border-slate-700/50'
                        }`}
                      >
                        {task.status.replace(/_/g, ' ')}
                      </span>
                      <ChevronRight className="w-4 h-4 text-slate-500 group-hover:text-cyan-400 transition-colors" />
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </div>

        {/* Right Column: Google Meet Records & Transcripts */}
        <div className="glass-card neo-surface rounded-3xl p-6 space-y-5">
          <div className="flex items-center justify-between pb-3 border-b border-white/[0.08]">
            <div className="flex items-center space-x-2">
              <Video className="w-4 h-4 text-indigo-400" />
              <h3 className="text-sm font-bold uppercase tracking-wider text-white">Google Meet Sessions</h3>
            </div>
            <span className="text-xs text-slate-400 font-mono">{meetings.length} Total</span>
          </div>

          {meetings.length === 0 ? (
            <div className="p-8 text-center text-sm text-slate-500 italic">No meeting sessions recorded yet.</div>
          ) : (
            <div className="space-y-3">
              {meetings.slice(0, 5).map((m) => (
                <div
                  key={m.id}
                  onClick={() => setSelectedMeeting(m)}
                  className="p-4 rounded-2xl glass-card-interactive cursor-pointer flex items-center justify-between gap-4 group"
                >
                  <div className="space-y-1 min-w-0 flex-1">
                    <div className="flex items-center space-x-2">
                      <h4 className="text-sm font-bold text-slate-100 group-hover:text-indigo-400 transition-colors truncate">
                        {m.meeting_type} Session
                      </h4>
                      <span className="text-[10px] font-mono text-slate-400">
                        {new Date(m.scheduled_start_utc).toLocaleDateString([], { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' })}
                      </span>
                    </div>
                    <div className="flex items-center gap-3 text-xs text-slate-400 font-mono truncate">
                      <span>{m.google_meet_url}</span>
                    </div>
                  </div>

                  <div className="flex items-center space-x-3 flex-shrink-0">
                    <span
                      className={`text-[11px] font-semibold px-2.5 py-1 rounded-full neo-inset ${
                        m.status === 'COMPLETED'
                          ? 'text-emerald-400 border border-emerald-500/30'
                          : m.status === 'IN_PROGRESS'
                          ? 'text-cyan-300 border border-cyan-500/30'
                          : 'text-slate-400 border border-slate-700/50'
                      }`}
                    >
                      {m.status}
                    </span>
                    <ChevronRight className="w-4 h-4 text-slate-500 group-hover:text-indigo-400 transition-colors" />
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>

      {/* Meeting Detail Modal for Transcripts & Recording */}
      {selectedMeeting && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/70 backdrop-blur-md animate-fadeIn">
          <div className="glass-card neo-surface rounded-3xl max-w-2xl w-full p-6 sm:p-7 space-y-5 max-h-[85vh] overflow-y-auto">
            <div className="flex items-center justify-between pb-3 border-b border-white/[0.08]">
              <div className="flex items-center space-x-3">
                <div className="w-10 h-10 rounded-xl bg-indigo-500/10 border border-indigo-500/20 flex items-center justify-center text-indigo-400">
                  <Video className="w-5 h-5" />
                </div>
                <div>
                  <h3 className="text-base font-bold text-white">
                    {selectedMeeting.meeting_type} Session Details
                  </h3>
                  <p className="text-xs text-slate-400 font-mono">{selectedMeeting.google_meet_url}</p>
                </div>
              </div>
              <button
                onClick={() => setSelectedMeeting(null)}
                className="p-1.5 rounded-lg neo-btn text-slate-400 hover:text-white"
              >
                ✕
              </button>
            </div>

            <div className="space-y-4">
              <div className="grid grid-cols-2 gap-3 text-xs">
                <div className="neo-inset p-3 rounded-xl space-y-1">
                  <span className="text-slate-400 block font-semibold">Status:</span>
                  <span className="text-slate-200 font-bold">{selectedMeeting.status}</span>
                </div>
                <div className="neo-inset p-3 rounded-xl space-y-1">
                  <span className="text-slate-400 block font-semibold">Scheduled Start:</span>
                  <span className="text-slate-200 font-bold">
                    {new Date(selectedMeeting.scheduled_start_utc).toLocaleString()}
                  </span>
                </div>
              </div>

              <div>
                <h4 className="text-xs font-bold uppercase tracking-wider text-slate-400 mb-2">
                  Diarized Transcripts ({selectedMeeting.transcripts?.length || 0})
                </h4>
                {selectedMeeting.transcripts && selectedMeeting.transcripts.length > 0 ? (
                  <div className="space-y-2 max-h-64 overflow-y-auto pr-1">
                    {selectedMeeting.transcripts.map((t) => (
                      <div key={t.id} className="neo-inset p-3 rounded-xl text-xs space-y-1">
                        <div className="flex items-center justify-between text-indigo-400 font-bold">
                          <span>{t.speaker_label}</span>
                          <span className="text-[10px] text-slate-500 font-mono">+{t.timestamp_offset_sec.toFixed(1)}s</span>
                        </div>
                        <p className="text-slate-200 leading-relaxed">{t.spoken_text}</p>
                      </div>
                    ))}
                  </div>
                ) : (
                  <p className="text-xs text-slate-500 italic neo-inset p-4 rounded-xl">No transcripts recorded yet for this session.</p>
                )}
              </div>
            </div>

            <div className="flex justify-end pt-3 border-t border-white/[0.08]">
              <button
                onClick={() => setSelectedMeeting(null)}
                className="px-5 py-2 rounded-xl text-xs font-bold text-slate-300 neo-btn hover:text-white"
              >
                Close
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Intern Roster & Deletions Modal */}
      {showInternRosterModal && (
        <div className="fixed inset-0 z-50 bg-black/80 backdrop-blur-sm flex items-center justify-center p-4 animate-fadeIn">
          <div className="glass-card neo-surface rounded-3xl w-full max-w-2xl p-6 sm:p-7 space-y-5 border border-white/[0.12] shadow-2xl">
            <div className="flex items-center justify-between pb-3 border-b border-white/[0.08]">
              <div className="flex items-center space-x-3">
                <div className="w-10 h-10 rounded-xl bg-purple-500/10 border border-purple-500/20 flex items-center justify-center text-purple-400">
                  <Users className="w-5 h-5" />
                </div>
                <div>
                  <h3 className="text-lg font-bold text-slate-100 flex items-center gap-2">
                    <span>Manage Intern Roster</span>
                    <span className="neo-inset px-2.5 py-0.5 rounded-full text-xs text-purple-300 font-mono">
                      {interns.length} Registered
                    </span>
                  </h3>
                  <p className="text-xs text-slate-400">
                    Review assigned tasks or delete intern accounts from your workspace.
                  </p>
                </div>
              </div>
              <button
                onClick={() => {
                  setShowInternRosterModal(false);
                  onNavigateToWorkspace();
                }}
                className="flex items-center space-x-1.5 glass-btn-primary text-white text-xs font-bold px-3 py-2 rounded-xl"
              >
                <UserPlus className="w-3.5 h-3.5" />
                <span>Go to Workspace</span>
              </button>
            </div>

            {rosterFeedback && (
              <div className="p-3 bg-emerald-950/70 border border-emerald-800 text-emerald-300 text-xs rounded-xl flex items-center space-x-2">
                <CheckCircle2 className="w-4 h-4 text-emerald-400 flex-shrink-0" />
                <span>{rosterFeedback}</span>
              </div>
            )}

            {rosterError && (
              <div className="p-3 bg-rose-950/70 border border-rose-800 text-rose-300 text-xs rounded-xl flex items-center space-x-2">
                <AlertTriangle className="w-4 h-4 text-rose-400 flex-shrink-0" />
                <span>{rosterError}</span>
              </div>
            )}

            <div className="max-h-96 overflow-y-auto space-y-2.5 pr-1">
              {interns.length === 0 ? (
                <div className="text-center py-10 neo-inset rounded-2xl border border-white/[0.06] text-slate-400 text-xs">
                  No interns currently registered. Go to Tasks Workspace to register a new candidate.
                </div>
              ) : (
                interns.map((intern) => {
                  const assignedCount = tasks.filter((t) => t.intern_id === intern.id).length;
                  const isDeleting = deletingInternId === intern.id;

                  return (
                    <div
                      key={intern.id}
                      className="flex items-center justify-between p-3.5 neo-inset rounded-2xl border border-white/[0.06] hover:border-white/[0.12] transition-all"
                    >
                      <div className="flex items-center space-x-3.5">
                        <div className="w-9 h-9 rounded-xl bg-slate-800 border border-white/[0.08] flex items-center justify-center text-slate-300">
                          <GraduationCap className="w-4 h-4 text-emerald-400" />
                        </div>
                        <div>
                          <div className="text-sm font-bold text-slate-100 flex items-center gap-2">
                            <span>{intern.full_name}</span>
                            {assignedCount > 0 && (
                              <span className="text-[10px] neo-inset px-2 py-0.5 rounded-full text-cyan-300 border border-cyan-500/20">
                                {assignedCount} {assignedCount === 1 ? 'task' : 'tasks'} assigned
                              </span>
                            )}
                          </div>
                          <div className="text-xs text-slate-400 font-mono mt-0.5">{intern.email}</div>
                        </div>
                      </div>

                      <div className="flex items-center space-x-2">
                        <button
                          type="button"
                          disabled={isDeleting}
                          onClick={() => handleDeleteIntern(intern.id, intern.full_name)}
                          className="flex items-center space-x-1.5 px-3 py-1.5 bg-rose-950/60 hover:bg-rose-900/60 border border-rose-800/60 hover:border-rose-600 rounded-xl text-rose-300 text-xs font-semibold transition-all disabled:opacity-50"
                          title="Delete intern and unassign associated tasks"
                        >
                          <Trash2 className="w-3.5 h-3.5 text-rose-400" />
                          <span>{isDeleting ? 'Deleting...' : 'Delete Intern'}</span>
                        </button>
                      </div>
                    </div>
                  );
                })
              )}
            </div>

            <div className="flex justify-end pt-3 border-t border-white/[0.08]">
              <button
                type="button"
                onClick={() => setShowInternRosterModal(false)}
                className="neo-btn text-slate-300 px-5 py-2 rounded-xl text-xs font-bold"
              >
                Close Roster
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
