import React, { useState, useEffect } from 'react';
import {
  Task,
  User,
  TaskSpecificationDraft,
  Meeting,
  ReviewRound
} from '../types';
import { taskApi, authApi, schedulingApi, reviewApi, meetingApi, BotStatus } from '../api/client';
import {
  Plus,
  Upload,
  Sparkles,
  CheckCircle,
  Clock,
  Calendar,
  AlertTriangle,
  FileText,
  ChevronRight,
  ExternalLink,
  ShieldAlert,
  PlayCircle,
  Eye,
  CheckCircle2,
  XCircle,
  RefreshCw,
  UserPlus,
  Users,
  Bot,
  Square,
  Radio,
  Key,
  Mic,
  Volume2
} from 'lucide-react';

interface AssignerDashboardProps {
  onOpenVoiceRoom?: (taskTitle?: string, taskId?: string) => void;
}

export const AssignerDashboard: React.FC<AssignerDashboardProps> = ({ onOpenVoiceRoom }) => {
  const [tasks, setTasks] = useState<Task[]>([]);
  const [interns, setInterns] = useState<User[]>([]);
  const [selectedTask, setSelectedTask] = useState<Task | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  // Modal States
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [showUploadModal, setShowUploadModal] = useState(false);
  const [showDraftModal, setShowDraftModal] = useState(false);
  const [showScheduleModal, setShowScheduleModal] = useState(false);
  const [showEvaluateModal, setShowEvaluateModal] = useState(false);

  // Form states
  const [newTitle, setNewTitle] = useState('');
  const [selectedInternId, setSelectedInternId] = useState('');
  const [uploadFile, setUploadFile] = useState<File | null>(null);
  const [draft, setDraft] = useState<TaskSpecificationDraft | null>(null);
  const [isExtracting, setIsExtracting] = useState(false);

  // Schedule form state
  const [meetingType, setMeetingType] = useState<'BRIEFING' | 'REVIEW'>('BRIEFING');
  const [scheduleTime, setScheduleTime] = useState('');
  const [timezone, setTimezone] = useState('Asia/Kolkata');
  const [isScheduling, setIsScheduling] = useState(false);
  const [scheduleError, setScheduleError] = useState<string | null>(null);

  // Evaluation form state
  const [evalTestOutput, setEvalTestOutput] = useState('14 passed, 0 failed in 0.82s (100% pass)');
  const [evalRepoUrl, setEvalRepoUrl] = useState('https://github.com/intern/project-deliverable');
  const [evalTranscripts, setEvalTranscripts] = useState(
    'AI Reviewer: Please explain your architectural approach.\nIntern: We implemented container isolation with reproducible test fixtures.'
  );
  const [activeRoundId, setActiveRoundId] = useState<string | null>(null);

  // New Intern form state
  const [showNewInternModal, setShowNewInternModal] = useState(false);
  const [newInternName, setNewInternName] = useState('');
  const [newInternEmail, setNewInternEmail] = useState('');
  const [newInternPassword, setNewInternPassword] = useState('SecretPass123!');
  const [isCreatingIntern, setIsCreatingIntern] = useState(false);
  const [newInternError, setNewInternError] = useState<string | null>(null);

  // Google Meet AI Bot state
  const [botStatus, setBotStatus] = useState<BotStatus | null>(null);
  const [isBotLaunching, setIsBotLaunching] = useState(false);
  const [isSpeakingMode, setIsSpeakingMode] = useState<boolean>(true);
  const [customMeetUrl, setCustomMeetUrl] = useState('');
  const [botFeedback, setBotFeedback] = useState<string | null>(null);
  const [isGoogleAuthed, setIsGoogleAuthed] = useState<boolean>(false);
  const [isLaunchingLogin, setIsLaunchingLogin] = useState<boolean>(false);

  const checkBotStatus = async () => {
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

  useEffect(() => {
    checkBotStatus();
    const interval = setInterval(checkBotStatus, 4000);
    return () => clearInterval(interval);
  }, []);

  const handleLaunchDirectBot = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!customMeetUrl.trim()) return;
    try {
      setIsBotLaunching(true);
      setBotFeedback(null);
      const res = await meetingApi.launchDirectBot(customMeetUrl.trim(), isSpeakingMode);
      setBotFeedback(res.message);
      await checkBotStatus();
    } catch (err: any) {
      setBotFeedback(err.response?.data?.detail || 'Failed to dispatch AI Bot');
    } finally {
      setIsBotLaunching(false);
    }
  };

  const handleLaunchMeetingBot = async (meetingId: string) => {
    try {
      setIsBotLaunching(true);
      setBotFeedback(null);
      const res = await meetingApi.launchMeetingBot(meetingId, isSpeakingMode);
      setBotFeedback(res.message);
      await checkBotStatus();
    } catch (err: any) {
      setBotFeedback(err.response?.data?.detail || 'Failed to launch AI Bot for session');
    } finally {
      setIsBotLaunching(false);
    }
  };

  const [isSyncingTranscripts, setIsSyncingTranscripts] = useState(false);

  const handleStopBot = async () => {
    try {
      const res = await meetingApi.stopBot();
      setBotFeedback(res.message || 'Bot process stopped.');
      await checkBotStatus();
      await loadData();
    } catch (err: any) {
      setBotFeedback('Failed to stop bot');
    }
  };

  const handleSyncMeetingTranscripts = async (meetingId: string) => {
    try {
      setIsSyncingTranscripts(true);
      const res = await meetingApi.syncBaasTranscripts(meetingId);
      setBotFeedback(`Transcripts synced: ${res.transcripts_synced} segments saved from MeetingBaas.`);
      await loadData();
    } catch (err: any) {
      setBotFeedback(err.response?.data?.detail || 'Failed to sync MeetingBaas transcripts');
    } finally {
      setIsSyncingTranscripts(false);
    }
  };

  const loadData = async () => {
    try {
      setIsLoading(true);
      const [allTasks, allUsers] = await Promise.all([
        taskApi.list(),
        authApi.getUsers()
      ]);
      setTasks(allTasks);
      setInterns(allUsers.filter((u) => u.role === 'INTERN'));
      if (selectedTask) {
        const refreshed = await taskApi.get(selectedTask.id);
        setSelectedTask(refreshed);
      } else if (allTasks.length > 0) {
        setSelectedTask(allTasks[0]);
      }
    } catch (err) {
      console.error('Failed to load dashboard data', err);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, []);

  const handleCreateTask = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newTitle.trim()) return;
    try {
      const created = await taskApi.create({
        title: newTitle,
        intern_id: selectedInternId || undefined
      });
      setShowCreateModal(false);
      setNewTitle('');
      await loadData();
      setSelectedTask(created);
    } catch (err) {
      console.error('Failed to create task', err);
    }
  };

  const handleUploadFile = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!uploadFile || !selectedTask) return;
    try {
      await taskApi.uploadDocument(selectedTask.id, uploadFile);
      setShowUploadModal(false);
      setUploadFile(null);
      await loadData();
    } catch (err) {
      console.error('Failed to upload assignment file', err);
    }
  };

  const handleExtractDraft = async () => {
    if (!selectedTask) return;
    try {
      setIsExtracting(true);
      setShowDraftModal(true);
      const spec = await taskApi.extractDraft(selectedTask.id);
      setDraft(spec);
    } catch (err) {
      console.error('Failed to extract draft', err);
    } finally {
      setIsExtracting(false);
    }
  };

  const handleApproveSpecification = async () => {
    if (!selectedTask || !draft) return;
    try {
      await taskApi.approveSpecification(selectedTask.id, draft);
      setShowDraftModal(false);
      setDraft(null);
      await loadData();
    } catch (err) {
      console.error('Failed to approve specification', err);
    }
  };

  const handleScheduleMeeting = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedTask || !scheduleTime) return;
    setIsScheduling(true);
    setScheduleError(null);
    try {
      await schedulingApi.scheduleMeeting({
        task_id: selectedTask.id,
        meeting_type: meetingType,
        start_time_iso: new Date(scheduleTime).toISOString(),
        duration_minutes: 30,
        timezone
      });
      setShowScheduleModal(false);
      setScheduleTime('');
      await loadData();
    } catch (err: any) {
      console.error('Failed to schedule meeting', err);
      const detail = err?.response?.data?.detail;
      setScheduleError(typeof detail === 'string' ? detail : err?.message || 'Failed to schedule meeting.');
    } finally {
      setIsScheduling(false);
    }
  };

  const handleRunEvaluation = async (roundId: string) => {
    try {
      await reviewApi.evaluate(roundId, {
        test_output: evalTestOutput,
        repo_url: evalRepoUrl,
        meeting_transcripts: evalTranscripts.split('\n').filter((l) => l.trim().length > 0)
      });
      setShowEvaluateModal(false);
      await loadData();
    } catch (err) {
      console.error('Evaluation run failed', err);
    }
  };

  const handleReassignIntern = async (newInternId: string) => {
    if (!selectedTask) return;
    try {
      const updated = await taskApi.update(selectedTask.id, { intern_id: newInternId || '' });
      setSelectedTask(updated);
      await loadData();
    } catch (err) {
      console.error('Failed to update assigned intern', err);
    }
  };

  const handleCreateIntern = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newInternName.trim() || !newInternEmail.trim() || !newInternPassword.trim()) return;
    setIsCreatingIntern(true);
    setNewInternError(null);
    try {
      const created = await authApi.createUser({
        full_name: newInternName.trim(),
        email: newInternEmail.trim().toLowerCase(),
        password: newInternPassword,
        role: 'INTERN'
      });
      setShowNewInternModal(false);
      setNewInternName('');
      setNewInternEmail('');
      await loadData();
      if (selectedTask) {
        await handleReassignIntern(created.id);
      }
    } catch (err: any) {
      const msg = err?.response?.data?.detail || err?.message || 'Failed to create intern';
      setNewInternError(typeof msg === 'string' ? msg : JSON.stringify(msg));
    } finally {
      setIsCreatingIntern(false);
    }
  };

  const getStatusBadge = (status: string) => {
    switch (status) {
      case 'PASSED':
        return <span className="bg-emerald-950 text-emerald-300 border border-emerald-800 text-xs px-2.5 py-0.5 rounded-full font-medium">Passed</span>;
      case 'REVISION_REQUIRED':
        return <span className="bg-amber-950 text-amber-300 border border-amber-800 text-xs px-2.5 py-0.5 rounded-full font-medium">Revision Required</span>;
      case 'HUMAN_REVIEW_REQUIRED':
        return <span className="bg-rose-950 text-rose-300 border border-rose-800 text-xs px-2.5 py-0.5 rounded-full font-medium">Human Review Flagged</span>;
      case 'SPECIFICATION_APPROVED':
        return <span className="bg-cyan-950 text-cyan-300 border border-cyan-800 text-xs px-2.5 py-0.5 rounded-full font-medium">Spec Approved</span>;
      case 'BRIEFING_SCHEDULED':
        return <span className="bg-blue-950 text-blue-300 border border-blue-800 text-xs px-2.5 py-0.5 rounded-full font-medium">Briefing Scheduled</span>;
      case 'IN_PROGRESS':
        return <span className="bg-indigo-950 text-indigo-300 border border-indigo-800 text-xs px-2.5 py-0.5 rounded-full font-medium">In Progress</span>;
      default:
        return <span className="bg-slate-800 text-slate-300 border border-slate-700 text-xs px-2.5 py-0.5 rounded-full font-medium">{status}</span>;
    }
  };

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
      {/* Top action header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between pb-6 border-b border-slate-800 gap-4">
        <div>
          <h1 className="text-2xl font-bold text-slate-100">Task Assigner Workspace</h1>
          <p className="text-sm text-slate-400">
            Define requirements, trigger local AI specification extraction, schedule meetings, and supervise review cycles.
          </p>
        </div>
        <div className="flex items-center space-x-3">
          <button
            onClick={() => loadData()}
            className="p-2 bg-slate-800 hover:bg-slate-700 border border-slate-700 rounded-xl text-slate-300 transition-colors"
            title="Refresh dashboard"
          >
            <RefreshCw className="w-4 h-4" />
          </button>
          <button
            onClick={() => setShowNewInternModal(true)}
            className="flex items-center space-x-2 bg-slate-800 hover:bg-slate-700 border border-slate-700 text-slate-200 font-semibold text-sm px-4 py-2 rounded-xl transition-all"
          >
            <UserPlus className="w-4 h-4 text-cyan-400" />
            <span>Add New Intern</span>
          </button>
          <button
            onClick={() => setShowCreateModal(true)}
            className="flex items-center space-x-2 bg-cyan-600 hover:bg-cyan-500 text-white font-semibold text-sm px-4 py-2 rounded-xl shadow-lg shadow-cyan-600/20 transition-all"
          >
            <Plus className="w-4 h-4" />
            <span>Create New Task</span>
          </button>
        </div>
      </div>

      {/* Grid: Task list & Selected Task detail */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-8 mt-6">
        {/* Task List (Left 5 Cols) */}
        <div className="lg:col-span-5 space-y-3">
          <h2 className="text-sm font-semibold uppercase tracking-wider text-slate-400 mb-2">
            Tasks Portfolio ({tasks.length})
          </h2>
          {isLoading && tasks.length === 0 ? (
            <div className="p-8 text-center text-slate-500 bg-slate-900/60 rounded-2xl border border-slate-800">
              Loading tasks...
            </div>
          ) : tasks.length === 0 ? (
            <div className="p-8 text-center text-slate-500 bg-slate-900/60 rounded-2xl border border-slate-800">
              No tasks created yet. Click "Create New Task" to begin.
            </div>
          ) : (
            tasks.map((task) => (
              <div
                key={task.id}
                onClick={() => setSelectedTask(task)}
                className={`p-4 rounded-2xl border cursor-pointer transition-all ${
                  selectedTask?.id === task.id
                    ? 'bg-slate-800/90 border-cyan-500/80 shadow-lg shadow-cyan-950/40'
                    : 'bg-slate-900/80 border-slate-800/80 hover:bg-slate-800/50 hover:border-slate-700'
                }`}
              >
                <div className="flex items-start justify-between">
                  <h3 className="font-semibold text-slate-100 text-sm line-clamp-1">{task.title}</h3>
                  <ChevronRight className="w-4 h-4 text-slate-500 flex-shrink-0" />
                </div>
                <div className="flex items-center justify-between mt-3">
                  <div className="text-xs text-slate-400">
                    Intern: {task.intern_id ? interns.find((i) => i.id === task.intern_id)?.full_name || 'Assigned' : 'Unassigned'}
                  </div>
                  {getStatusBadge(task.status)}
                </div>
              </div>
            ))
          )}
        </div>

        {/* Selected Task Details (Right 7 Cols) */}
        <div className="lg:col-span-7">
          {selectedTask ? (
            <div className="bg-slate-900/90 border border-slate-800 rounded-2xl p-6 space-y-6">
              {/* Task Header */}
              <div className="flex flex-col sm:flex-row sm:items-start sm:justify-between pb-4 border-b border-slate-800 gap-4">
                <div className="space-y-1.5">
                  <span className="text-xs font-mono text-cyan-400">ID: {selectedTask.id.substring(0, 8)}...</span>
                  <h2 className="text-xl font-bold text-slate-100">{selectedTask.title}</h2>
                  <div className="flex items-center space-x-2 pt-1">
                    <span className="text-xs font-medium text-slate-400 flex items-center gap-1">
                      <Users className="w-3.5 h-3.5 text-cyan-400" />
                      Assigned Intern:
                    </span>
                    <select
                      value={selectedTask.intern_id || ''}
                      onChange={(e) => handleReassignIntern(e.target.value)}
                      className="bg-slate-950 border border-slate-800 hover:border-cyan-500 rounded-lg px-2.5 py-1 text-xs text-cyan-300 font-semibold focus:outline-none transition-colors"
                    >
                      <option value="">(Unassigned)</option>
                      {interns.map((i) => (
                        <option key={i.id} value={i.id}>
                          {i.full_name} ({i.email})
                        </option>
                      ))}
                    </select>
                  </div>
                </div>
                <div>{getStatusBadge(selectedTask.status)}</div>
              </div>

              {/* Action Toolbar */}
              <div className="flex flex-wrap gap-2">
                <button
                  onClick={() => setShowUploadModal(true)}
                  className="flex items-center space-x-1.5 px-3 py-1.5 bg-slate-800 hover:bg-slate-700 border border-slate-700 rounded-lg text-xs font-medium text-slate-200 transition-colors"
                >
                  <Upload className="w-3.5 h-3.5 text-cyan-400" />
                  <span>Upload Brief (PDF/DOCX)</span>
                </button>

                <button
                  onClick={handleExtractDraft}
                  className="flex items-center space-x-1.5 px-3 py-1.5 bg-gradient-to-r from-cyan-600 to-blue-600 hover:from-cyan-500 hover:to-blue-500 rounded-lg text-xs font-medium text-white shadow transition-all"
                >
                  <Sparkles className="w-3.5 h-3.5" />
                  <span>AI Spec Drafter</span>
                </button>

                <button
                  onClick={() => {
                    setMeetingType('BRIEFING');
                    setShowScheduleModal(true);
                  }}
                  className="flex items-center space-x-1.5 px-3 py-1.5 bg-slate-800 hover:bg-slate-700 border border-slate-700 rounded-lg text-xs font-medium text-slate-200 transition-colors"
                >
                  <Calendar className="w-3.5 h-3.5 text-blue-400" />
                  <span>Schedule Meeting</span>
                </button>

                <button
                  onClick={() => onOpenVoiceRoom?.(selectedTask.title, selectedTask.id)}
                  className="flex items-center space-x-1.5 px-3 py-1.5 bg-gradient-to-r from-emerald-600 to-teal-600 hover:from-emerald-500 hover:to-teal-500 rounded-lg text-xs font-semibold text-white shadow-md transition-all active:scale-95"
                  title="Launch local AI Voice Review Room for this task"
                >
                  <Mic className="w-3.5 h-3.5" />
                  <span>Launch AI Voice Room</span>
                </button>
              </div>

              {/* Uploaded Documents */}
              <div>
                <h4 className="text-xs font-semibold uppercase tracking-wider text-slate-400 mb-2">
                  Uploaded Documents ({selectedTask.documents?.length || 0})
                </h4>
                {selectedTask.documents && selectedTask.documents.length > 0 ? (
                  <div className="space-y-2">
                    {selectedTask.documents.map((doc) => (
                      <div
                        key={doc.id}
                        className="flex items-center justify-between p-3 bg-slate-950/60 border border-slate-800 rounded-xl text-xs"
                      >
                        <div className="flex items-center space-x-2">
                          <FileText className="w-4 h-4 text-cyan-400" />
                          <span className="font-medium text-slate-200">{doc.original_filename}</span>
                          <span className="text-slate-500">({(doc.file_size_bytes / 1024).toFixed(1)} KB)</span>
                        </div>
                        {doc.has_detected_injection ? (
                          <span className="flex items-center text-rose-400 gap-1 font-semibold">
                            <ShieldAlert className="w-3.5 h-3.5" /> Injection Flagged
                          </span>
                        ) : (
                          <span className="text-emerald-400 flex items-center gap-1">
                            <CheckCircle2 className="w-3.5 h-3.5" /> Verified Clean
                          </span>
                        )}
                      </div>
                    ))}
                  </div>
                ) : (
                  <p className="text-xs text-slate-500 italic">No document uploaded yet.</p>
                )}
              </div>

              {/* Approved Specification View */}
              {selectedTask.versions && selectedTask.versions.length > 0 && (
                <div className="p-4 bg-slate-950/80 border border-cyan-900/50 rounded-xl space-y-3">
                  <div className="flex items-center justify-between">
                    <span className="text-xs font-semibold uppercase text-cyan-400 flex items-center gap-1.5">
                      <CheckCircle className="w-4 h-4 text-cyan-400" /> Approved Specification (v{selectedTask.versions[0].version_number})
                    </span>
                    <span className="text-xs text-slate-400 font-mono">Timezone: {selectedTask.versions[0].timezone}</span>
                  </div>
                  <p className="text-sm text-slate-200 font-medium">{selectedTask.versions[0].objective}</p>
                  <div className="grid grid-cols-2 gap-4 pt-2 text-xs text-slate-400 border-t border-slate-800/80">
                    <div>
                      <span className="block font-semibold text-slate-300">Deliverables:</span>
                      {selectedTask.versions[0].deliverables}
                    </div>
                    <div>
                      <span className="block font-semibold text-slate-300">Requirements Count:</span>
                      {selectedTask.versions[0].requirements?.length || 0} items
                    </div>
                  </div>
                </div>
              )}

              {/* Autonomous Google Meet Bot Quick Dispatcher */}
              <div className="p-4 bg-slate-950/90 border border-indigo-500/30 rounded-xl space-y-3">
                <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2">
                  <div className="flex items-center space-x-2">
                    <Bot className="w-4 h-4 text-indigo-400" />
                    <h4 className="text-xs font-bold uppercase tracking-wider text-indigo-300">
                      Google Meet AI Agent Dispatcher
                    </h4>
                  </div>
                  <div className="flex items-center gap-2">
                    {isGoogleAuthed ? (
                      <span className="flex items-center gap-1 text-[11px] font-mono text-emerald-400 bg-emerald-950/60 border border-emerald-800/80 px-2.5 py-0.5 rounded-full">
                        <CheckCircle2 className="w-3 h-3 text-emerald-400" /> Google Account Linked
                      </span>
                    ) : (
                      <button
                        type="button"
                        onClick={handleLaunchGoogleLogin}
                        disabled={isLaunchingLogin}
                        className="flex items-center gap-1 text-[11px] font-semibold text-amber-300 bg-amber-950/60 hover:bg-amber-900/60 border border-amber-800/80 px-2.5 py-1 rounded-lg transition-colors shadow-sm"
                        title="Click to open Chrome and sign in to your Google Account"
                      >
                        <Key className="w-3 h-3 text-amber-400" />
                        <span>{isLaunchingLogin ? 'Opening Chrome...' : '🔑 Sign in Bot to Google'}</span>
                      </button>
                    )}
                    {botStatus?.is_running ? (
                      <span className="flex items-center gap-1.5 text-[11px] font-mono text-emerald-400 bg-emerald-950/60 border border-emerald-800/80 px-2.5 py-0.5 rounded-full">
                        <span className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse" />
                        {botStatus.status === 'in_call_recording'
                          ? (botStatus.is_speaking ? 'MeetingBaas In-Call (Speaking & Recording)' : 'MeetingBaas In-Call (Recording)')
                          : botStatus.status === 'joining'
                          ? 'MeetingBaas Joining Call'
                          : botStatus.bot_id
                          ? `MeetingBaas (${botStatus.status}${botStatus.is_speaking ? ' - Speaking' : ''})`
                          : `Agent Active (PID: ${botStatus.pid})`}
                      </span>
                    ) : (
                      <span className="text-[11px] font-mono text-slate-400 bg-slate-900 border border-slate-800 px-2.5 py-0.5 rounded-full">
                        Agent Standby
                      </span>
                    )}
                  </div>
                </div>

                <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 pt-1 pb-1 px-1">
                  <p className="text-[11px] text-slate-400 leading-relaxed flex-1">
                    Enter any Google Meet URL or code below. The bot will join open calls directly or request host admission.
                  </p>
                  <label className="flex items-center gap-2 cursor-pointer text-xs font-semibold select-none bg-slate-900/90 border border-slate-700/80 px-3 py-1.5 rounded-lg flex-shrink-0 hover:border-indigo-500/60 transition-colors">
                    <input
                      type="checkbox"
                      checked={isSpeakingMode}
                      onChange={(e) => setIsSpeakingMode(e.target.checked)}
                      className="w-4 h-4 rounded text-indigo-600 focus:ring-indigo-500 bg-slate-800 border-slate-600 cursor-pointer"
                    />
                    <span className={isSpeakingMode ? "text-indigo-300 font-bold flex items-center gap-1.5" : "text-slate-400 flex items-center gap-1.5"}>
                      <Volume2 className={`w-3.5 h-3.5 ${isSpeakingMode ? 'text-indigo-400' : 'text-slate-500'}`} />
                      {isSpeakingMode ? 'Interactive Speaking Bot (Voice AI)' : 'Silent Recording Bot'}
                    </span>
                  </label>
                </div>

                <form onSubmit={handleLaunchDirectBot} className="flex flex-col sm:flex-row gap-2">
                  <input
                    type="text"
                    placeholder="e.g. rqp-ctfg-nri or https://meet.google.com/rqp-ctfg-nri"
                    value={customMeetUrl}
                    onChange={(e) => setCustomMeetUrl(e.target.value)}
                    className="flex-1 bg-slate-900 border border-slate-700 rounded-lg px-3 py-1.5 text-xs text-slate-100 placeholder-slate-500 focus:outline-none focus:ring-1 focus:ring-indigo-500 font-mono"
                  />
                  <div className="flex gap-2">
                    <button
                      type="submit"
                      disabled={isBotLaunching || !customMeetUrl.trim()}
                      className="flex items-center justify-center space-x-1.5 px-3 py-1.5 bg-indigo-600 hover:bg-indigo-500 disabled:opacity-50 text-white rounded-lg text-xs font-semibold transition-colors"
                    >
                      <Bot className="w-3.5 h-3.5" />
                      <span>{isBotLaunching ? 'Dispatching...' : (isSpeakingMode ? 'Dispatch Speaking Bot' : 'Dispatch Recording Bot')}</span>
                    </button>
                    {botStatus?.is_running && (
                      <button
                        type="button"
                        onClick={handleStopBot}
                        className="flex items-center space-x-1 px-3 py-1.5 bg-rose-900/60 hover:bg-rose-800/80 border border-rose-700/60 rounded-lg text-rose-200 text-xs font-semibold"
                      >
                        <Square className="w-3 h-3 text-rose-400" />
                        <span>Stop Bot</span>
                      </button>
                    )}
                  </div>
                </form>

                {botFeedback && (
                  <div className="text-[11px] font-medium text-indigo-300 bg-indigo-950/40 border border-indigo-900/50 p-2 rounded-lg">
                    ℹ️ {botFeedback}
                  </div>
                )}
              </div>

              {/* Meetings List */}
              <div>
                <div className="flex items-center justify-between mb-2">
                  <h4 className="text-xs font-semibold uppercase tracking-wider text-slate-400">
                    Scheduled Meetings ({selectedTask.meetings?.length || 0})
                  </h4>
                  <button
                    onClick={() => {
                      setMeetingType('BRIEFING');
                      setShowScheduleModal(true);
                    }}
                    className="text-xs text-cyan-400 hover:text-cyan-300 flex items-center gap-1 font-medium"
                  >
                    <Plus className="w-3 h-3" /> Schedule Meeting
                  </button>
                </div>
                {selectedTask.meetings && selectedTask.meetings.length > 0 ? (
                  <div className="space-y-2">
                    {selectedTask.meetings.map((m) => (
                      <div
                        key={m.id}
                        className="flex flex-col sm:flex-row sm:items-center justify-between p-3.5 bg-slate-950/80 border border-slate-800 rounded-xl text-xs gap-3"
                      >
                        <div className="space-y-1">
                          <div className="flex items-center gap-2">
                            <span className="font-bold text-slate-100">{m.meeting_type} SESSION</span>
                            <span className="bg-blue-950/80 border border-blue-800 text-blue-300 px-2 py-0.5 rounded-full text-[10px] font-mono">
                              {m.status}
                            </span>
                          </div>
                          <div className="text-slate-300 font-medium">
                            📅 {new Date(m.scheduled_start_utc).toLocaleString('en-IN', {
                              dateStyle: 'full',
                              timeStyle: 'short',
                              timeZone: m.timezone || 'Asia/Kolkata'
                            })} ({m.timezone || 'Asia/Kolkata'})
                          </div>
                        </div>
                        {m.google_meet_url && (
                          <div className="flex items-center gap-2 flex-shrink-0">
                            <a
                              href={m.google_meet_url}
                              target="_blank"
                              rel="noopener noreferrer"
                              className="flex items-center space-x-1.5 px-3 py-1.5 bg-cyan-600/20 hover:bg-cyan-600/30 border border-cyan-500/50 rounded-lg text-cyan-300 hover:text-cyan-200 font-semibold transition-colors"
                            >
                              <span>Join Google Meet</span>
                              <ExternalLink className="w-3.5 h-3.5" />
                            </a>
                            {botStatus?.is_running && botStatus.meeting_id === m.id ? (
                              <button
                                onClick={handleStopBot}
                                className="flex items-center space-x-1 px-3 py-1.5 bg-rose-950/60 hover:bg-rose-900/60 border border-rose-700/60 rounded-lg text-rose-300 text-xs font-semibold"
                              >
                                <Square className="w-3 h-3 text-rose-400" />
                                <span>Stop Bot</span>
                              </button>
                            ) : (
                              <button
                                onClick={() => handleLaunchMeetingBot(m.id)}
                                disabled={isBotLaunching}
                                className="flex items-center space-x-1 px-3 py-1.5 bg-indigo-600/20 hover:bg-indigo-600/30 border border-indigo-500/50 rounded-lg text-indigo-300 hover:text-indigo-200 font-semibold text-xs transition-colors"
                              >
                                <Bot className="w-3.5 h-3.5" />
                                <span>{isSpeakingMode ? 'Launch Speaking Bot' : 'Launch Recording Bot'}</span>
                              </button>
                            )}
                            <button
                              onClick={() => handleSyncMeetingTranscripts(m.id)}
                              disabled={isSyncingTranscripts}
                              className="flex items-center space-x-1.5 px-3 py-1.5 bg-cyan-950/60 hover:bg-cyan-900/60 border border-cyan-700/60 rounded-lg text-cyan-300 font-semibold text-xs transition-colors"
                              title="Sync latest MeetingBaas recordings and transcripts"
                            >
                              <RefreshCw className={`w-3.5 h-3.5 ${isSyncingTranscripts ? 'animate-spin' : ''}`} />
                              <span>Sync Transcripts</span>
                            </button>
                            <button
                              onClick={() => onOpenVoiceRoom?.(selectedTask.title, selectedTask.id)}
                              className="flex items-center space-x-1.5 px-3 py-1.5 bg-slate-800 hover:bg-slate-700 border border-slate-700 rounded-lg text-slate-200 font-semibold text-xs transition-colors"
                              title="Join Interactive AI Voice Briefing"
                            >
                              <Mic className="w-3.5 h-3.5 text-emerald-400" />
                              <span>Web Voice Room</span>
                            </button>
                          </div>
                        )}
                        {/* Diarized Transcripts Preview */}
                        {m.transcripts && m.transcripts.length > 0 && (
                          <div className="w-full mt-2 pt-2 border-t border-slate-800/80 text-[11px] text-slate-300 space-y-1.5">
                            <div className="flex items-center justify-between">
                              <span className="font-semibold text-cyan-400 flex items-center gap-1.5">
                                <FileText className="w-3.5 h-3.5" />
                                Meeting Transcripts ({m.transcripts.length} segments from MeetingBaas)
                              </span>
                              <span className="text-[10px] text-slate-500 font-mono">Diarized & Verified</span>
                            </div>
                            <div className="max-h-28 overflow-y-auto space-y-1 bg-slate-900/90 border border-slate-800 p-2.5 rounded-lg font-mono text-[11px]">
                              {m.transcripts.map((t) => (
                                <div key={t.id} className="leading-snug">
                                  <span className="text-indigo-400 font-bold">{t.speaker_label}:</span>{' '}
                                  <span className="text-slate-200">{t.spoken_text}</span>
                                </div>
                              ))}
                            </div>
                          </div>
                        )}
                      </div>
                    ))}
                  </div>
                ) : (
                  <div className="p-4 bg-slate-950/40 border border-slate-800 rounded-xl text-xs text-slate-500 italic">
                    No meeting scheduled yet. Click "Schedule Meeting" above to set up a Google Meet briefing.
                  </div>
                )}
              </div>

              {/* Submissions & Review Rounds */}
              <div>
                <h4 className="text-xs font-semibold uppercase tracking-wider text-slate-400 mb-2">
                  Submissions & Review Rounds ({selectedTask.submissions?.length || 0})
                </h4>
                {selectedTask.submissions && selectedTask.submissions.length > 0 ? (
                  <div className="space-y-3">
                    {selectedTask.submissions.map((sub) => (
                      <div key={sub.id} className="p-4 bg-slate-950 border border-slate-800 rounded-xl space-y-3">
                        <div className="flex items-center justify-between text-xs">
                          <div>
                            <span className="font-semibold text-slate-300">Repository: </span>
                            <a
                              href={sub.repository_url}
                              target="_blank"
                              rel="noreferrer"
                              className="text-cyan-400 underline font-mono"
                            >
                              {sub.repository_url}
                            </a>
                            {sub.commit_hash && (
                              <span className="ml-2 font-mono text-slate-500">[{sub.commit_hash.substring(0, 7)}]</span>
                            )}
                          </div>
                          <span className="text-slate-500">{new Date(sub.created_at).toLocaleDateString()}</span>
                        </div>

                        {/* Review Rounds */}
                        {sub.review_rounds?.map((round) => (
                          <div
                            key={round.id}
                            className="p-3 bg-slate-900 border border-slate-800/80 rounded-lg text-xs space-y-2"
                          >
                            <div className="flex items-center justify-between">
                              <span className="font-bold text-slate-200">Review Round {round.round_number}</span>
                              <div className="flex items-center space-x-2">
                                {round.outcome && getStatusBadge(round.outcome)}
                                {round.total_score !== undefined && (
                                  <span className="font-mono font-semibold text-cyan-300">
                                    Score: {round.total_score.toFixed(1)}%
                                  </span>
                                )}
                              </div>
                            </div>

                            {round.summary && <p className="text-slate-400 leading-relaxed">{round.summary}</p>}

                            {/* Evaluation Trigger Button */}
                            <div className="pt-2 flex justify-end">
                              <button
                                onClick={() => {
                                  setActiveRoundId(round.id);
                                  if (selectedTask?.meetings) {
                                    const allTranscripts: string[] = [];
                                    selectedTask.meetings.forEach((m) => {
                                      if (m.transcripts && m.transcripts.length > 0) {
                                        m.transcripts.forEach((t) => allTranscripts.push(`${t.speaker_label}: ${t.spoken_text}`));
                                      }
                                    });
                                    if (allTranscripts.length > 0) {
                                      setEvalTranscripts(allTranscripts.join('\n'));
                                    }
                                  }
                                  setShowEvaluateModal(true);
                                }}
                                className="flex items-center space-x-1 px-3 py-1 bg-cyan-700 hover:bg-cyan-600 text-white rounded font-medium transition-colors"
                              >
                                <PlayCircle className="w-3.5 h-3.5" />
                                <span>Run AI Evidence Evaluation</span>
                              </button>
                            </div>
                          </div>
                        ))}
                      </div>
                    ))}
                  </div>
                ) : (
                  <p className="text-xs text-slate-500 italic">No submissions delivered by intern yet.</p>
                )}
              </div>
            </div>
          ) : (
            <div className="bg-slate-900/60 border border-slate-800 rounded-2xl p-12 text-center text-slate-500">
              Select a task from the portfolio on the left to inspect details or run AI actions.
            </div>
          )}
        </div>
      </div>

      {/* MODAL 1: Create Task */}
      {showCreateModal && (
        <div className="fixed inset-0 z-50 bg-black/80 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="bg-slate-900 border border-slate-800 rounded-2xl w-full max-w-md p-6 space-y-4">
            <h3 className="text-lg font-bold text-slate-100">Create Task Assignment</h3>
            <form onSubmit={handleCreateTask} className="space-y-4">
              <div>
                <label className="block text-xs font-semibold text-slate-400 uppercase tracking-wider mb-1">
                  Task Title
                </label>
                <input
                  type="text"
                  required
                  value={newTitle}
                  onChange={(e) => setNewTitle(e.target.value)}
                  placeholder="e.g. Distributed Consensus Engine"
                  className="w-full bg-slate-950 border border-slate-800 rounded-xl px-4 py-2.5 text-sm text-slate-100 focus:outline-none focus:border-cyan-500"
                />
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-400 uppercase tracking-wider mb-1">
                  Assign To Intern
                </label>
                <select
                  value={selectedInternId}
                  onChange={(e) => setSelectedInternId(e.target.value)}
                  className="w-full bg-slate-950 border border-slate-800 rounded-xl px-4 py-2.5 text-sm text-slate-100 focus:outline-none focus:border-cyan-500"
                >
                  <option value="">Select an intern (optional)</option>
                  {interns.map((intern) => (
                    <option key={intern.id} value={intern.id}>
                      {intern.full_name} ({intern.email})
                    </option>
                  ))}
                </select>
              </div>

              <div className="flex justify-end space-x-2 pt-2">
                <button
                  type="button"
                  onClick={() => setShowCreateModal(false)}
                  className="px-4 py-2 text-sm text-slate-400 hover:text-slate-200"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className="px-5 py-2 bg-cyan-600 hover:bg-cyan-500 text-white rounded-xl text-sm font-semibold shadow"
                >
                  Create Task
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* MODAL 2: Upload Brief File */}
      {showUploadModal && (
        <div className="fixed inset-0 z-50 bg-black/80 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="bg-slate-900 border border-slate-800 rounded-2xl w-full max-w-md p-6 space-y-4">
            <h3 className="text-lg font-bold text-slate-100">Upload Task Brief Document</h3>
            <p className="text-xs text-slate-400">
              Upload PDF, DOCX, or TXT file. Text is extracted safely and screened for prompt injection attacks.
            </p>
            <form onSubmit={handleUploadFile} className="space-y-4">
              <input
                type="file"
                required
                accept=".pdf,.docx,.txt"
                onChange={(e) => setUploadFile(e.target.files ? e.target.files[0] : null)}
                className="w-full text-sm text-slate-300 file:mr-4 file:py-2 file:px-4 file:rounded-xl file:border-0 file:text-xs file:font-semibold file:bg-cyan-600 file:text-white hover:file:bg-cyan-500 cursor-pointer"
              />

              <div className="flex justify-end space-x-2 pt-2">
                <button
                  type="button"
                  onClick={() => setShowUploadModal(false)}
                  className="px-4 py-2 text-sm text-slate-400 hover:text-slate-200"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={!uploadFile}
                  className="px-5 py-2 bg-cyan-600 hover:bg-cyan-500 disabled:opacity-50 text-white rounded-xl text-sm font-semibold shadow"
                >
                  Upload & Analyze
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* MODAL 3: AI Specification Drafter & Approval */}
      {showDraftModal && (
        <div className="fixed inset-0 z-50 bg-black/80 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="bg-slate-900 border border-slate-800 rounded-2xl w-full max-w-3xl p-6 space-y-4 max-h-[85vh] flex flex-col">
            <div className="flex items-center justify-between border-b border-slate-800 pb-3">
              <div className="flex items-center space-x-2">
                <Sparkles className="w-5 h-5 text-cyan-400" />
                <h3 className="text-lg font-bold text-slate-100">AI Task Specification Draft</h3>
              </div>
              <span className="text-xs font-mono text-cyan-400 bg-cyan-950 px-2 py-0.5 rounded border border-cyan-800">
                Ollama Local Inference
              </span>
            </div>

            <div className="flex-1 overflow-y-auto space-y-4 pr-1 text-sm">
              {isExtracting ? (
                <div className="p-12 text-center text-slate-400 space-y-3">
                  <div className="w-8 h-8 border-2 border-cyan-500 border-t-transparent rounded-full animate-spin mx-auto" />
                  <p>Local Ollama LLM is parsing document, detecting contradictions, and structuring rubric...</p>
                </div>
              ) : draft ? (
                <>
                  {draft.detected_contradictions?.length > 0 && (
                    <div className="p-3 bg-rose-950/60 border border-rose-800 rounded-xl text-xs text-rose-300 space-y-1">
                      <div className="font-semibold flex items-center gap-1.5">
                        <AlertTriangle className="w-4 h-4" /> Detected Contradictions
                      </div>
                      <ul className="list-disc pl-5">
                        {draft.detected_contradictions.map((c, i) => (
                          <li key={i}>{c}</li>
                        ))}
                      </ul>
                    </div>
                  )}

                  <div>
                    <label className="block text-xs font-semibold text-slate-400 uppercase tracking-wider mb-1">
                      Objective
                    </label>
                    <textarea
                      rows={2}
                      value={draft.objective}
                      onChange={(e) => setDraft({ ...draft, objective: e.target.value })}
                      className="w-full bg-slate-950 border border-slate-800 rounded-xl p-3 text-sm text-slate-200 focus:outline-none focus:border-cyan-500"
                    />
                  </div>

                  <div>
                    <label className="block text-xs font-semibold text-slate-400 uppercase tracking-wider mb-1">
                      Deliverables
                    </label>
                    <textarea
                      rows={2}
                      value={draft.deliverables}
                      onChange={(e) => setDraft({ ...draft, deliverables: e.target.value })}
                      className="w-full bg-slate-950 border border-slate-800 rounded-xl p-3 text-sm text-slate-200 focus:outline-none focus:border-cyan-500"
                    />
                  </div>

                  <div>
                    <h4 className="text-xs font-semibold text-slate-400 uppercase tracking-wider mb-2">
                      Structured Requirements ({draft.requirements?.length || 0})
                    </h4>
                    <div className="space-y-2">
                      {draft.requirements?.map((req, i) => (
                        <div key={i} className="p-3 bg-slate-950 border border-slate-800 rounded-xl space-y-1">
                          <div className="flex items-center justify-between">
                            <span className="font-bold text-slate-200 text-xs">
                              {req.req_code}: {req.title}
                            </span>
                            <span className="text-[10px] bg-slate-800 text-slate-300 px-2 py-0.5 rounded font-mono">
                              {req.priority}
                            </span>
                          </div>
                          <p className="text-xs text-slate-400">{req.description}</p>
                        </div>
                      ))}
                    </div>
                  </div>

                  <div>
                    <h4 className="text-xs font-semibold text-slate-400 uppercase tracking-wider mb-2">
                      Configurable Rubric Items ({draft.rubric?.length || 0})
                    </h4>
                    <div className="space-y-2">
                      {draft.rubric?.map((rub, i) => (
                        <div key={i} className="p-3 bg-slate-950 border border-slate-800 rounded-xl space-y-1">
                          <div className="flex items-center justify-between">
                            <span className="font-semibold text-slate-200 text-xs">{rub.name}</span>
                            <span className="text-xs font-mono text-cyan-400">Weight: {rub.weight} | Max: {rub.max_score}</span>
                          </div>
                          <p className="text-xs text-slate-400">{rub.description}</p>
                        </div>
                      ))}
                    </div>
                  </div>
                </>
              ) : null}
            </div>

            <div className="flex items-center justify-between border-t border-slate-800 pt-3">
              <span className="text-xs text-slate-400">
                Approving this draft publishes Specification v1 and unblocks briefing scheduling.
              </span>
              <div className="flex space-x-2">
                <button
                  onClick={() => setShowDraftModal(false)}
                  className="px-4 py-2 text-sm text-slate-400 hover:text-slate-200"
                >
                  Cancel
                </button>
                <button
                  onClick={handleApproveSpecification}
                  disabled={!draft || isExtracting}
                  className="px-5 py-2 bg-emerald-600 hover:bg-emerald-500 disabled:opacity-50 text-white rounded-xl text-sm font-semibold shadow"
                >
                  Approve Specification
                </button>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* MODAL 4: Schedule Meeting */}
      {showScheduleModal && (
        <div className="fixed inset-0 z-50 bg-black/80 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="bg-slate-900 border border-slate-800 rounded-2xl w-full max-w-md p-6 space-y-4">
            <h3 className="text-lg font-bold text-slate-100">Schedule Google Meet Session</h3>
            {scheduleError && (
              <div className="p-3 bg-rose-950/70 border border-rose-800 text-rose-300 text-xs rounded-xl flex items-start gap-2">
                <AlertTriangle className="w-4 h-4 text-rose-400 flex-shrink-0 mt-0.5" />
                <span>{scheduleError}</span>
              </div>
            )}

            {selectedTask?.status === 'DRAFT' && meetingType === 'BRIEFING' && (
              <div className="p-3 bg-amber-950/70 border border-amber-800 rounded-xl text-xs space-y-2 text-amber-200">
                <div className="flex items-start gap-2">
                  <AlertTriangle className="w-4 h-4 text-amber-400 flex-shrink-0 mt-0.5" />
                  <span>This task specification is currently in DRAFT. Briefing meetings require an approved specification.</span>
                </div>
                <button
                  type="button"
                  disabled={isExtracting}
                  onClick={async () => {
                    try {
                      setIsExtracting(true);
                      setScheduleError(null);
                      const draft = await taskApi.extractDraft(selectedTask.id);
                      await taskApi.approveSpecification(selectedTask.id, draft);
                      await loadData();
                    } catch (e: any) {
                      setScheduleError('Failed to auto-approve specification: ' + (e?.message || e));
                    } finally {
                      setIsExtracting(false);
                    }
                  }}
                  className="w-full py-2 px-3 bg-amber-600 hover:bg-amber-500 disabled:opacity-50 text-white rounded-lg font-semibold flex items-center justify-center gap-1.5 transition-colors"
                >
                  <Sparkles className="w-3.5 h-3.5" />
                  <span>{isExtracting ? 'Extracting & Approving...' : 'Auto-Approve Specification Now'}</span>
                </button>
              </div>
            )}
            <form onSubmit={handleScheduleMeeting} className="space-y-4">
              <div>
                <label className="block text-xs font-semibold text-slate-400 uppercase tracking-wider mb-1">
                  Meeting Type
                </label>
                <select
                  value={meetingType}
                  onChange={(e) => setMeetingType(e.target.value as any)}
                  className="w-full bg-slate-950 border border-slate-800 rounded-xl px-4 py-2.5 text-sm text-slate-100 focus:outline-none focus:border-cyan-500"
                >
                  <option value="BRIEFING">BRIEFING (Task Explanation & Voice Brief)</option>
                  <option value="REVIEW">REVIEW (Evaluation & Oral Defense)</option>
                </select>
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-400 uppercase tracking-wider mb-1">
                  Start Date & Time (Local Time)
                </label>
                <input
                  type="datetime-local"
                  required
                  value={scheduleTime}
                  onChange={(e) => setScheduleTime(e.target.value)}
                  className="w-full bg-slate-950 border border-slate-800 rounded-xl px-4 py-2.5 text-sm text-slate-100 focus:outline-none focus:border-cyan-500"
                />
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-400 uppercase tracking-wider mb-1">
                  Timezone
                </label>
                <select
                  value={timezone}
                  onChange={(e) => setTimezone(e.target.value)}
                  className="w-full bg-slate-950 border border-slate-800 rounded-xl px-4 py-2.5 text-sm text-slate-100 focus:outline-none focus:border-cyan-500"
                >
                  <option value="Asia/Kolkata">Asia/Kolkata (UTC+05:30) [Default]</option>
                  <option value="UTC">UTC</option>
                  <option value="America/New_York">America/New_York (EST)</option>
                </select>
              </div>

              <div className="flex justify-end space-x-2 pt-2">
                <button
                  type="button"
                  onClick={() => setShowScheduleModal(false)}
                  className="px-4 py-2 text-sm text-slate-400 hover:text-slate-200"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={isScheduling || !scheduleTime}
                  className="px-5 py-2 bg-blue-600 hover:bg-blue-500 disabled:opacity-50 text-white rounded-xl text-sm font-semibold shadow"
                >
                  {isScheduling ? 'Scheduling...' : 'Confirm & Schedule'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* MODAL 5: Run Evaluation Form */}
      {showEvaluateModal && activeRoundId && (
        <div className="fixed inset-0 z-50 bg-black/80 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="bg-slate-900 border border-slate-800 rounded-2xl w-full max-w-2xl p-6 space-y-4">
            <h3 className="text-lg font-bold text-slate-100">Run Rubric Evaluation on Review Round</h3>
            <p className="text-xs text-slate-400">
              Deterministic checks verify test assertions, while qualitative checks assess meeting transcript explanations.
            </p>

            <div className="space-y-3 text-sm">
              <div>
                <label className="block text-xs font-semibold text-slate-400 uppercase tracking-wider mb-1">
                  Automated Test Output / Execution Logs
                </label>
                <textarea
                  rows={3}
                  value={evalTestOutput}
                  onChange={(e) => setEvalTestOutput(e.target.value)}
                  className="w-full font-mono text-xs bg-slate-950 border border-slate-800 rounded-xl p-3 text-slate-200 focus:outline-none focus:border-cyan-500"
                />
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-400 uppercase tracking-wider mb-1">
                  Repository URL
                </label>
                <input
                  type="text"
                  value={evalRepoUrl}
                  onChange={(e) => setEvalRepoUrl(e.target.value)}
                  className="w-full bg-slate-950 border border-slate-800 rounded-xl px-4 py-2 text-xs font-mono text-slate-200 focus:outline-none focus:border-cyan-500"
                />
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-400 uppercase tracking-wider mb-1">
                  Meeting Transcript Excerpts
                </label>
                <textarea
                  rows={3}
                  value={evalTranscripts}
                  onChange={(e) => setEvalTranscripts(e.target.value)}
                  className="w-full text-xs bg-slate-950 border border-slate-800 rounded-xl p-3 text-slate-200 focus:outline-none focus:border-cyan-500"
                />
              </div>
            </div>

            <div className="flex justify-end space-x-2 pt-2 border-t border-slate-800">
              <button
                type="button"
                onClick={() => setShowEvaluateModal(false)}
                className="px-4 py-2 text-sm text-slate-400 hover:text-slate-200"
              >
                Cancel
              </button>
              <button
                type="button"
                onClick={() => handleRunEvaluation(activeRoundId)}
                className="px-5 py-2 bg-cyan-600 hover:bg-cyan-500 text-white rounded-xl text-sm font-semibold shadow"
              >
                Execute Evaluation Engine
              </button>
            </div>
          </div>
        </div>
      )}

      {/* MODAL 6: Add New Intern */}
      {showNewInternModal && (
        <div className="fixed inset-0 z-50 bg-black/80 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="bg-slate-900 border border-slate-800 rounded-2xl w-full max-w-md p-6 space-y-4">
            <div className="flex items-center space-x-2">
              <UserPlus className="w-5 h-5 text-cyan-400" />
              <h3 className="text-lg font-bold text-slate-100">Add New Intern Account</h3>
            </div>
            <p className="text-xs text-slate-400">
              Register a new intern so they can log in, receive task assignments, and participate in voice reviews.
            </p>

            {newInternError && (
              <div className="p-3 bg-rose-950/70 border border-rose-800 text-rose-300 text-xs rounded-xl flex items-start gap-2">
                <AlertTriangle className="w-4 h-4 text-rose-400 flex-shrink-0 mt-0.5" />
                <span>{newInternError}</span>
              </div>
            )}

            <form onSubmit={handleCreateIntern} className="space-y-3">
              <div>
                <label className="block text-xs font-semibold text-slate-400 uppercase tracking-wider mb-1">
                  Full Name & Role Description
                </label>
                <input
                  type="text"
                  required
                  value={newInternName}
                  onChange={(e) => setNewInternName(e.target.value)}
                  placeholder="e.g. Ananya Sen (Backend Systems Intern)"
                  className="w-full bg-slate-950 border border-slate-800 rounded-xl px-4 py-2 text-sm text-slate-100 focus:outline-none focus:border-cyan-500"
                />
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-400 uppercase tracking-wider mb-1">
                  Email Address (Login ID)
                </label>
                <input
                  type="email"
                  required
                  value={newInternEmail}
                  onChange={(e) => setNewInternEmail(e.target.value)}
                  placeholder="e.g. ananya@internal.company"
                  className="w-full bg-slate-950 border border-slate-800 rounded-xl px-4 py-2 text-sm text-slate-100 focus:outline-none focus:border-cyan-500"
                />
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-400 uppercase tracking-wider mb-1">
                  Initial Password
                </label>
                <input
                  type="password"
                  required
                  value={newInternPassword}
                  onChange={(e) => setNewInternPassword(e.target.value)}
                  placeholder="SecretPass123!"
                  className="w-full bg-slate-950 border border-slate-800 rounded-xl px-4 py-2 text-sm text-slate-100 focus:outline-none focus:border-cyan-500"
                />
              </div>

              <div className="flex justify-end space-x-2 pt-2 border-t border-slate-800">
                <button
                  type="button"
                  onClick={() => setShowNewInternModal(false)}
                  className="px-4 py-2 text-sm text-slate-400 hover:text-slate-200"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={isCreatingIntern}
                  className="px-5 py-2 bg-gradient-to-r from-cyan-600 to-blue-600 hover:from-cyan-500 hover:to-blue-500 disabled:opacity-50 text-white rounded-xl text-sm font-semibold shadow"
                >
                  {isCreatingIntern ? 'Registering...' : 'Register Intern'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
};
