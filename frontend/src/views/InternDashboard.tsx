import React, { useState, useEffect } from 'react';
import { Task, Submission, ReviewRound } from '../types';
import { taskApi, submissionApi, reviewApi, meetingApi, BotStatus } from '../api/client';
import {
  FileText,
  Clock,
  ExternalLink,
  Send,
  AlertCircle,
  CheckCircle2,
  XCircle,
  HelpCircle,
  Scale,
  Mic,
  Calendar,
  Layers,
  Sparkles,
  ChevronRight,
  Bot,
  Square,
  Video,
  RefreshCw,
  Volume2
} from 'lucide-react';

interface InternDashboardProps {
  initialTaskId?: string;
}

export const InternDashboard: React.FC<InternDashboardProps> = ({ initialTaskId }) => {
  const [tasks, setTasks] = useState<Task[]>([]);
  const [selectedTask, setSelectedTask] = useState<Task | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  // Submission Form State
  const [repoUrl, setRepoUrl] = useState('');
  const [commitHash, setCommitHash] = useState('');
  const [submissionNotes, setSubmissionNotes] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);

  // Appeal Modal State
  const [showAppealModal, setShowAppealModal] = useState(false);
  const [appealRoundId, setAppealRoundId] = useState<string | null>(null);
  const [appealReason, setAppealReason] = useState('');

  // Google Meet AI Bot state
  const [botStatus, setBotStatus] = useState<BotStatus | null>(null);
  const [isBotLaunching, setIsBotLaunching] = useState(false);
  const [isSpeakingMode, setIsSpeakingMode] = useState<boolean>(true);
  const [customMeetUrl, setCustomMeetUrl] = useState('https://meet.google.com/meet/rqp-ctfg-nri');
  const [botFeedback, setBotFeedback] = useState<string | null>(null);

  const checkBotStatus = async () => {
    try {
      const status = await meetingApi.getBotStatus();
      setBotStatus(status);
    } catch (err) {
      // ignore
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
      const res = await meetingApi.launchDirectBot(customMeetUrl.trim(), isSpeakingMode, selectedTask?.id);
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
      const allTasks = await taskApi.list();
      setTasks(allTasks);
      if (initialTaskId && allTasks.some((t) => t.id === initialTaskId)) {
        const match = allTasks.find((t) => t.id === initialTaskId);
        if (match) setSelectedTask(match);
      } else if (allTasks.length > 0 && !selectedTask) {
        setSelectedTask(allTasks[0]);
      } else if (selectedTask) {
        const refreshed = await taskApi.get(selectedTask.id);
        setSelectedTask(refreshed);
      }
    } catch (err) {
      console.error('Failed to load intern tasks', err);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, [initialTaskId]);

  const handleSubmitDeliverable = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedTask || !repoUrl.trim()) return;
    try {
      setIsSubmitting(true);
      await submissionApi.create({
        task_id: selectedTask.id,
        repository_url: repoUrl.trim(),
        commit_hash: commitHash.trim() || undefined,
        notes: submissionNotes.trim() || undefined
      });
      setRepoUrl('');
      setCommitHash('');
      setSubmissionNotes('');
      await loadData();
    } catch (err) {
      console.error('Failed to submit deliverable', err);
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleSendAppeal = async () => {
    if (!appealRoundId || !appealReason.trim()) return;
    try {
      await reviewApi.appeal(appealRoundId, appealReason.trim());
      setShowAppealModal(false);
      setAppealReason('');
      setAppealRoundId(null);
      await loadData();
    } catch (err) {
      console.error('Failed to submit appeal', err);
    }
  };

  const getStatusBadge = (status: string) => {
    switch (status) {
      case 'PASSED':
        return <span className="bg-emerald-950 text-emerald-300 border border-emerald-800 text-xs px-2.5 py-0.5 rounded-full font-medium">Passed</span>;
      case 'SUBMITTED':
        return <span className="bg-purple-950 text-purple-300 border border-purple-800 text-xs px-2.5 py-0.5 rounded-full font-medium">Submitted</span>;
      case 'REVIEW_SCHEDULED':
        return <span className="bg-sky-950 text-sky-300 border border-sky-800 text-xs px-2.5 py-0.5 rounded-full font-medium">Review Scheduled</span>;
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

  const currentVersion = selectedTask?.versions && selectedTask.versions.length > 0
    ? selectedTask.versions[0]
    : null;

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8 space-y-8 animate-fadeIn">
      {/* Header */}
      <div className="glass-card neo-surface rounded-3xl p-6 sm:p-7 flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div className="space-y-1">
          <div className="flex items-center space-x-2 text-xs font-bold uppercase tracking-wider text-emerald-400">
            <Layers className="w-4 h-4" />
            <span>Intern Learning & Execution Hub</span>
          </div>
          <h1 className="text-2xl sm:text-3xl font-extrabold text-white tracking-tight">
            Assignments & Submissions
          </h1>
          <p className="text-xs sm:text-sm text-slate-300 max-w-2xl">
            Review approved assignment specifications, participate in Google Meet briefings, deliver repository code, and address review revisions.
          </p>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-12 gap-8">
        {/* Task Selector (Left 4 Cols) */}
        <div className="lg:col-span-4 space-y-3">
          <div className="flex items-center justify-between pb-2 border-b border-white/[0.08]">
            <h2 className="text-xs font-bold uppercase tracking-wider text-slate-400">
              My Assigned Tasks ({tasks.length})
            </h2>
            <span className="text-[11px] font-mono text-emerald-400">Active</span>
          </div>

          {isLoading ? (
            <div className="p-8 text-center text-slate-500 glass-card neo-surface rounded-2xl">
              Loading assignments...
            </div>
          ) : tasks.length === 0 ? (
            <div className="p-8 text-center text-slate-500 glass-card neo-surface rounded-2xl">
              No tasks assigned yet. Your assigner will allocate new tasks here.
            </div>
          ) : (
            tasks.map((task) => (
              <div
                key={task.id}
                onClick={() => setSelectedTask(task)}
                className={`p-4 rounded-2xl cursor-pointer transition-all ${
                  selectedTask?.id === task.id
                    ? 'glass-card neo-surface border border-emerald-400/50 shadow-lg shadow-emerald-500/20 ring-1 ring-emerald-400/30'
                    : 'glass-card-interactive neo-surface'
                }`}
              >
                <div className="flex items-start justify-between">
                  <h3 className="font-bold text-slate-100 text-sm line-clamp-1">{task.title}</h3>
                  <ChevronRight className="w-4 h-4 text-slate-500 flex-shrink-0" />
                </div>
                <div className="flex items-center justify-between mt-3 text-xs">
                  {getStatusBadge(task.status)}
                  <span className="text-slate-500">
                    {new Date(task.created_at).toLocaleDateString()}
                  </span>
                </div>
              </div>
            ))
          )}
        </div>

        {/* Task Detail & Submissions (Right 8 Cols) */}
        <div className="lg:col-span-8 space-y-6">
          {selectedTask ? (
            <>
              {/* Task Hero Card */}
              <div className="glass-card neo-surface rounded-3xl p-6 sm:p-7 space-y-4">
                <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between pb-4 border-b border-white/[0.08] gap-2">
                  <div>
                    <span className="text-xs font-mono text-emerald-400">ID: {selectedTask.id.substring(0, 8)}...</span>
                    <div className="flex items-center space-x-3">
                      <h2 className="text-xl font-bold text-slate-100">{selectedTask.title}</h2>
                      {getStatusBadge(selectedTask.status)}
                    </div>
                  </div>
                </div>

                {/* Deadlines & Timezone Banner */}
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 p-3 bg-slate-950/70 border border-slate-800 rounded-xl text-xs">
                  <div className="flex items-center space-x-2 text-slate-300">
                    <Clock className="w-4 h-4 text-cyan-400" />
                    <span>
                      Deadline:{' '}
                      <strong className="text-slate-100">
                        {currentVersion?.deadline_utc
                          ? new Date(currentVersion.deadline_utc).toLocaleString('en-IN', {
                              timeZone: currentVersion.timezone || 'Asia/Kolkata'
                            })
                          : '7 days from briefing'}
                      </strong>
                    </span>
                  </div>
                  <div className="flex items-center space-x-2 text-slate-300 sm:justify-end">
                    <Calendar className="w-4 h-4 text-blue-400" />
                    <span>Timezone: {currentVersion?.timezone || 'Asia/Kolkata (UTC+05:30)'}</span>
                  </div>
                </div>

                {/* Specification Details */}
                {currentVersion ? (
                  <div className="space-y-4 text-xs">
                    <div>
                      <h4 className="font-semibold text-slate-300 uppercase tracking-wider mb-1">Objective</h4>
                      <p className="text-slate-400 leading-relaxed bg-slate-950/40 p-3 rounded-lg border border-slate-800/80">
                        {currentVersion.objective}
                      </p>
                    </div>

                    <div>
                      <h4 className="font-semibold text-slate-300 uppercase tracking-wider mb-1">Expected Deliverables</h4>
                      <p className="text-slate-400 leading-relaxed bg-slate-950/40 p-3 rounded-lg border border-slate-800/80">
                        {currentVersion.deliverables}
                      </p>
                    </div>

                    {/* Requirements Accordion */}
                    <div>
                      <h4 className="font-semibold text-slate-300 uppercase tracking-wider mb-2">
                        Acceptance Criteria & Verification Methods ({currentVersion.requirements?.length || 0})
                      </h4>
                      <div className="space-y-2">
                        {currentVersion.requirements?.map((req, i) => (
                          <div key={i} className="p-3 bg-slate-950/80 border border-slate-800 rounded-xl space-y-2">
                            <div className="flex items-center justify-between">
                              <span className="font-bold text-slate-200">
                                {req.req_code}: {req.title}
                              </span>
                              <span className="text-[10px] bg-slate-800 text-cyan-400 px-2 py-0.5 rounded font-mono">
                                {req.priority}
                              </span>
                            </div>
                            <p className="text-slate-400">{req.description}</p>
                            <div className="space-y-1 pt-1 border-t border-slate-800/80">
                              {req.acceptance_criteria?.map((ac, j) => (
                                <div key={j} className="flex items-center justify-between text-[11px] text-slate-400">
                                  <span>• {ac.description}</span>
                                  <span className="font-mono text-slate-500 bg-slate-900 px-1.5 py-0.5 rounded">
                                    {ac.verification_method}
                                  </span>
                                </div>
                              ))}
                            </div>
                          </div>
                        ))}
                      </div>
                    </div>
                  </div>
                ) : (
                  <div className="p-4 bg-slate-950/60 border border-slate-800 rounded-xl text-xs text-slate-400">
                    Specification draft is being compiled by your task assigner.
                  </div>
                )}

                {/* AI Document Intelligence & Grounding Card (if analyzed document exists) */}
                {selectedTask.documents && selectedTask.documents.some((d) => d.analysis_json) && (
                  <div className="space-y-3 pt-2">
                    {selectedTask.documents
                      .filter((d) => d.analysis_json)
                      .map((doc) => {
                        let analysis: any = null;
                        try {
                          analysis = JSON.parse(doc.analysis_json!);
                        } catch (e) {}
                        if (!analysis) return null;
                        return (
                          <div
                            key={doc.id}
                            className="glass-card neo-surface rounded-2xl p-4 sm:p-5 border border-cyan-500/30 space-y-3 text-xs"
                          >
                            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 pb-2.5 border-b border-white/[0.08]">
                              <div className="flex items-center space-x-2">
                                <Sparkles className="w-4 h-4 text-cyan-400 animate-pulse" />
                                <div>
                                  <span className="text-[10px] font-bold uppercase tracking-wider text-cyan-400">
                                    AI Document Ingestion & Briefing Grounding
                                  </span>
                                  <h5 className="font-bold text-slate-100 text-sm">{analysis.title || doc.original_filename || doc.filename || 'Task Document'}</h5>
                                </div>
                              </div>
                              <span className="inline-flex items-center gap-1.5 text-[11px] font-mono text-emerald-400 neo-inset px-2.5 py-0.5 rounded-full border border-emerald-500/30">
                                <span className="w-2 h-2 rounded-full bg-emerald-400 animate-ping" />
                                Subha Verified Ready for Call
                              </span>
                            </div>

                            {analysis.executive_summary && (
                              <div>
                                <span className="text-[11px] font-bold uppercase tracking-wider text-slate-400 block mb-1">
                                  Document Summary
                                </span>
                                <p className="text-slate-300 leading-relaxed bg-slate-950/50 p-3 rounded-xl border border-slate-800/80">
                                  {analysis.executive_summary}
                                </p>
                              </div>
                            )}

                            {analysis.items && analysis.items.length > 0 && (
                              <div>
                                <span className="text-[11px] font-bold uppercase tracking-wider text-slate-400 block mb-1.5">
                                  Key Findings & Items to Deliver ({analysis.items.length})
                                </span>
                                <div className="max-h-44 overflow-y-auto space-y-1 pr-1">
                                  {analysis.items.map((item: any, idx: number) => (
                                    <div
                                      key={idx}
                                      className="flex items-center justify-between p-2 rounded-lg bg-slate-950/60 border border-slate-800/80 text-[11px]"
                                    >
                                      <div className="flex items-center space-x-2">
                                        <span className="font-mono font-bold text-cyan-400">{item.code}</span>
                                        <span className="text-slate-200">{item.title}</span>
                                      </div>
                                      {item.category && (
                                        <span className="text-indigo-300 font-mono text-[10px] bg-indigo-950/60 px-1.5 py-0.5 rounded">
                                          {item.category}
                                        </span>
                                      )}
                                    </div>
                                  ))}
                                </div>
                              </div>
                            )}

                            {analysis.spoken_briefing_script && (
                              <div className="p-3 bg-indigo-950/30 border border-indigo-500/20 rounded-xl space-y-1">
                                <div className="flex items-center space-x-1.5 text-indigo-300 font-semibold text-[11px]">
                                  <Volume2 className="w-3.5 h-3.5 text-indigo-400" />
                                  <span>What Subha will explain to you in the meeting</span>
                                </div>
                                <p className="text-slate-300 text-xs italic leading-relaxed">
                                  "{analysis.spoken_briefing_script}"
                                </p>
                              </div>
                            )}
                          </div>
                        );
                      })}
                  </div>
                )}
              </div>

              {/* Subha AI Session Feedback Card */}
              {selectedTask.meetings?.some((m) => m.feedback_summary) && (
                <div className="glass-card neo-surface rounded-2xl p-5 border border-purple-500/30 bg-purple-950/20 space-y-2.5 text-xs animate-fadeIn">
                  <div className="flex items-center space-x-2 text-purple-300 font-bold uppercase tracking-wider text-[11px]">
                    <Sparkles className="w-4 h-4 text-purple-400" />
                    <span>Subha Briefing Session Feedback</span>
                  </div>
                  {selectedTask.meetings
                    .filter((m) => m.feedback_summary)
                    .map((m) => (
                      <div key={m.id} className="p-3 bg-black/40 rounded-xl border border-white/[0.06] text-slate-200 leading-relaxed font-mono text-[11px]">
                        {m.feedback_summary}
                      </div>
                    ))}
                </div>
              )}

              {/* Scheduled Meetings Card */}
              <div className="bg-slate-900/90 border border-slate-800 rounded-2xl p-6 space-y-4">
                <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2">
                  <div className="flex items-center space-x-2">
                    <Calendar className="w-5 h-5 text-blue-400" />
                    <h3 className="font-bold text-slate-100 text-base">
                      Scheduled Review & Briefing Sessions ({selectedTask.meetings?.length || 0})
                    </h3>
                  </div>
                  <div className="flex items-center gap-2">
                    {botStatus?.is_running ? (
                      <span className="flex items-center gap-1.5 text-[11px] font-mono text-emerald-400 bg-emerald-950/60 border border-emerald-800/80 px-2.5 py-0.5 rounded-full">
                        <span className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse" />
                        {botStatus.is_speaking ? 'Speaking AI Bot Active' : 'Recording Bot Active'}
                      </span>
                    ) : (
                      <span className="text-[11px] font-mono text-slate-400 bg-slate-950 border border-slate-800 px-2.5 py-0.5 rounded-full">
                        Agent Standby
                      </span>
                    )}
                  </div>
                </div>

                {/* Quick Bot Join Input */}
                <div className="p-3.5 bg-slate-950/80 border border-indigo-500/30 rounded-xl space-y-2">
                  <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2">
                    <div className="flex items-center space-x-1.5 text-xs font-semibold text-indigo-300">
                      <Bot className="w-4 h-4 text-indigo-400" />
                      <span>Have a Google Meet Link? Dispatch AI Bot to Call</span>
                    </div>
                    <label className="flex items-center gap-2 cursor-pointer text-xs font-semibold select-none bg-slate-900 border border-slate-700/80 px-2.5 py-1 rounded-lg hover:border-indigo-500/60 transition-colors">
                      <input
                        type="checkbox"
                        checked={isSpeakingMode}
                        onChange={(e) => setIsSpeakingMode(e.target.checked)}
                        className="w-3.5 h-3.5 rounded text-indigo-600 focus:ring-indigo-500 bg-slate-800 border-slate-600 cursor-pointer"
                      />
                      <span className={isSpeakingMode ? "text-indigo-300 font-bold flex items-center gap-1" : "text-slate-400 flex items-center gap-1"}>
                        <Volume2 className={`w-3 h-3 ${isSpeakingMode ? 'text-indigo-400' : 'text-slate-500'}`} />
                        {isSpeakingMode ? 'Interactive Speaking Bot' : 'Silent Recording'}
                      </span>
                    </label>
                  </div>
                  <p className="text-[11px] text-slate-400">
                    If the meeting is open, the agent clicks "Join now" directly. If host admission is required, it requests to join and waits for the host.
                  </p>
                  <form onSubmit={handleLaunchDirectBot} className="flex flex-col sm:flex-row gap-2 pt-1">
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
                        className="flex items-center justify-center space-x-1 px-3 py-1.5 bg-indigo-600 hover:bg-indigo-500 disabled:opacity-50 text-white rounded-lg text-xs font-semibold transition-colors"
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
                    <div className="text-[11px] text-indigo-300 bg-indigo-950/40 border border-indigo-900/50 p-2 rounded-lg">
                      ℹ️ {botFeedback}
                    </div>
                  )}
                </div>

                {selectedTask.meetings && selectedTask.meetings.length > 0 ? (
                  <div className="space-y-3">
                    {selectedTask.meetings.map((m) => (
                      <div
                        key={m.id}
                        className="p-4 bg-slate-950/80 border border-slate-800/90 rounded-xl text-xs space-y-3 hover:border-slate-700/80 transition-all shadow-sm"
                      >
                        {/* Header: Session Badge, Round, Status, and Date */}
                        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 pb-2.5 border-b border-slate-800/60">
                          <div className="flex items-center gap-2">
                            <span className={`px-2.5 py-0.5 rounded-md font-bold tracking-wider text-[11px] uppercase ${
                              m.meeting_type === 'BRIEFING'
                                ? 'bg-indigo-950/80 text-indigo-300 border border-indigo-800/70'
                                : 'bg-violet-950/80 text-violet-300 border border-violet-800/70'
                            }`}>
                              {m.meeting_type} SESSION {m.meeting_round ? `#${m.meeting_round}` : ''}
                            </span>
                            <span className={`px-2 py-0.5 rounded-full text-[10px] font-mono border ${
                              m.status === 'COMPLETED' ? 'bg-slate-800/90 text-slate-300 border-slate-700' :
                              m.status === 'IN_PROGRESS' ? 'bg-emerald-950 text-emerald-300 border-emerald-600 animate-pulse' :
                              'bg-blue-950 text-blue-300 border-blue-800'
                            }`}>
                              {m.status}
                            </span>
                          </div>
                          <div className="text-slate-300 text-xs font-medium flex items-center gap-1.5">
                            <Calendar className="w-3.5 h-3.5 text-cyan-400 flex-shrink-0" />
                            <span>
                              {new Date(m.scheduled_start_utc).toLocaleString('en-IN', {
                                dateStyle: 'full',
                                timeStyle: 'short',
                                timeZone: m.timezone || 'Asia/Kolkata'
                              })}
                            </span>
                            <span className="text-slate-500 text-[11px]">({m.timezone || 'Asia/Kolkata'})</span>
                          </div>
                        </div>

                        {/* Action Buttons Row */}
                        <div className="flex flex-wrap items-center gap-2.5">
                          {m.google_meet_url && (
                            <a
                              href={m.google_meet_url}
                              target="_blank"
                              rel="noopener noreferrer"
                              className="inline-flex items-center space-x-1.5 px-3 py-1.5 bg-cyan-600/20 hover:bg-cyan-600/30 border border-cyan-500/50 rounded-lg text-cyan-300 hover:text-cyan-200 font-semibold transition-colors"
                            >
                              <Video className="w-3.5 h-3.5 text-cyan-400" />
                              <span>Join Google Meet</span>
                              <ExternalLink className="w-3.5 h-3.5" />
                            </a>
                          )}
                          {botStatus?.is_running && botStatus.meeting_id === m.id ? (
                            <button
                              onClick={handleStopBot}
                              className="inline-flex items-center space-x-1 px-3 py-1.5 bg-rose-950/60 hover:bg-rose-900/60 border border-rose-700/60 rounded-lg text-rose-300 text-xs font-semibold"
                            >
                              <Square className="w-3 h-3 text-rose-400" />
                              <span>Stop Bot</span>
                            </button>
                          ) : m.status !== 'COMPLETED' ? (
                            <button
                              onClick={() => handleLaunchMeetingBot(m.id)}
                              disabled={isBotLaunching}
                              className="inline-flex items-center space-x-1 px-3 py-1.5 bg-indigo-600/20 hover:bg-indigo-600/30 border border-indigo-500/50 rounded-lg text-indigo-300 hover:text-indigo-200 font-semibold text-xs transition-colors disabled:opacity-50"
                            >
                              <Bot className="w-3.5 h-3.5" />
                              <span>{isSpeakingMode ? 'Launch Speaking Bot' : 'Launch Recording Bot'}</span>
                            </button>
                          ) : null}
                          <button
                            onClick={() => handleSyncMeetingTranscripts(m.id)}
                            disabled={isSyncingTranscripts}
                            className="inline-flex items-center space-x-1.5 px-3 py-1.5 bg-cyan-950/60 hover:bg-cyan-900/60 border border-cyan-700/60 rounded-lg text-cyan-300 font-semibold text-xs transition-colors disabled:opacity-50"
                            title="Sync latest MeetingBaas recordings and transcripts"
                          >
                            <RefreshCw className={`w-3.5 h-3.5 ${isSyncingTranscripts ? 'animate-spin' : ''}`} />
                            <span>Sync Transcripts</span>
                          </button>
                        </div>
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
                    No Google Meet sessions scheduled yet. Your assigner will schedule your briefing soon.
                  </div>
                )}
              </div>

              {/* Submission Portal Card */}
              <div className="bg-slate-900/90 border border-slate-800 rounded-2xl p-6 space-y-4">
                <div className="flex items-center space-x-2">
                  <Send className="w-5 h-5 text-cyan-400" />
                  <h3 className="font-bold text-slate-100 text-base">Deliver Task Submission</h3>
                </div>
                <p className="text-xs text-slate-400">
                  Provide your git repository URL and commit hash. The AI Reviewer will verify deterministic test assertions and schedule your evaluation review.
                </p>

                <form onSubmit={handleSubmitDeliverable} className="space-y-3">
                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                    <div>
                      <label className="block text-xs font-semibold text-slate-400 uppercase tracking-wider mb-1">
                        Repository URL *
                      </label>
                      <input
                        type="url"
                        required
                        value={repoUrl}
                        onChange={(e) => setRepoUrl(e.target.value)}
                        placeholder="https://github.com/intern/project"
                        className="w-full bg-slate-950 border border-slate-800 rounded-xl px-4 py-2.5 text-xs font-mono text-slate-200 placeholder-slate-600 focus:outline-none focus:border-cyan-500"
                      />
                    </div>

                    <div>
                      <label className="block text-xs font-semibold text-slate-400 uppercase tracking-wider mb-1">
                        Commit Hash (Optional)
                      </label>
                      <input
                        type="text"
                        value={commitHash}
                        onChange={(e) => setCommitHash(e.target.value)}
                        placeholder="a1b2c3d4e5f6..."
                        className="w-full bg-slate-950 border border-slate-800 rounded-xl px-4 py-2.5 text-xs font-mono text-slate-200 placeholder-slate-600 focus:outline-none focus:border-cyan-500"
                      />
                    </div>
                  </div>

                  <div>
                    <label className="block text-xs font-semibold text-slate-400 uppercase tracking-wider mb-1">
                      Implementation Notes / Test Run Summary
                    </label>
                    <textarea
                      rows={2}
                      value={submissionNotes}
                      onChange={(e) => setSubmissionNotes(e.target.value)}
                      placeholder="e.g. All unit tests passing cleanly; added container Dockerfile and seed fixtures."
                      className="w-full bg-slate-950 border border-slate-800 rounded-xl p-3 text-xs text-slate-200 placeholder-slate-600 focus:outline-none focus:border-cyan-500"
                    />
                  </div>

                  <div className="flex justify-end pt-1">
                    <button
                      type="submit"
                      disabled={isSubmitting || !repoUrl.trim()}
                      className="px-6 py-2.5 bg-gradient-to-r from-cyan-600 to-blue-600 hover:from-cyan-500 hover:to-blue-500 disabled:opacity-50 text-white rounded-xl text-xs font-semibold shadow-md transition-all"
                    >
                      {isSubmitting ? 'Submitting...' : 'Submit Deliverables for Review'}
                    </button>
                  </div>
                </form>
              </div>

              {/* Review History, Revision Requests & Appeal Card */}
              {selectedTask.submissions && selectedTask.submissions.length > 0 && (
                <div className="bg-slate-900/90 border border-slate-800 rounded-2xl p-6 space-y-4">
                  <div className="flex items-center space-x-2">
                    <Scale className="w-5 h-5 text-cyan-400" />
                    <h3 className="font-bold text-slate-100 text-base">Review History & Feedback Loops</h3>
                  </div>

                  <div className="space-y-4">
                    {selectedTask.submissions.map((sub) =>
                      sub.review_rounds?.map((round) => (
                        <div
                          key={round.id}
                          className="p-4 bg-slate-950 border border-slate-800 rounded-xl space-y-3 text-xs"
                        >
                          <div className="flex items-center justify-between">
                            <span className="font-bold text-slate-200">Review Round {round.round_number}</span>
                            <div className="flex items-center space-x-2">
                              {round.outcome === 'PASS' && (
                                <span className="bg-emerald-950 text-emerald-300 border border-emerald-800 px-2 py-0.5 rounded font-medium">
                                  PASS
                                </span>
                              )}
                              {round.outcome === 'REVISION_REQUIRED' && (
                                <span className="bg-amber-950 text-amber-300 border border-amber-800 px-2 py-0.5 rounded font-medium">
                                  REVISION REQUIRED
                                </span>
                              )}
                              {round.outcome === 'HUMAN_REVIEW_REQUIRED' && (
                                <span className="bg-purple-950 text-purple-300 border border-purple-800 px-2 py-0.5 rounded font-medium">
                                  HUMAN REVIEW REQUIRED
                                </span>
                              )}
                              {round.total_score !== undefined && (
                                <span className="font-mono text-cyan-300 font-semibold">
                                  {round.total_score.toFixed(1)}%
                                </span>
                              )}
                            </div>
                          </div>

                          {round.summary && <p className="text-slate-400">{round.summary}</p>}

                          {/* Revision Requests List */}
                          {round.revision_requests && round.revision_requests.length > 0 && (
                            <div className="p-3 bg-amber-950/30 border border-amber-800/40 rounded-lg space-y-2">
                              <span className="font-semibold text-amber-400 flex items-center gap-1.5">
                                <AlertCircle className="w-3.5 h-3.5" /> Action Items to Address in Next Revision:
                              </span>
                              <div className="space-y-2">
                                {round.revision_requests.map((rev) => (
                                  <div key={rev.id} className="text-slate-300 space-y-0.5">
                                    <div className="font-medium text-slate-200">• {rev.observed_failure}</div>
                                    <div className="text-slate-400">
                                      <strong className="text-slate-300">Recommended Fix: </strong>
                                      {rev.recommended_fix}
                                    </div>
                                  </div>
                                ))}
                              </div>
                            </div>
                          )}

                          {/* Appeal Button */}
                          {round.outcome === 'REVISION_REQUIRED' && (
                            <div className="pt-2 flex justify-end">
                              <button
                                onClick={() => {
                                  setAppealRoundId(round.id);
                                  setShowAppealModal(true);
                                }}
                                className="flex items-center space-x-1 px-3 py-1 bg-slate-800 hover:bg-slate-700 border border-slate-700 text-slate-300 rounded font-medium transition-colors"
                              >
                                <Scale className="w-3.5 h-3.5 text-purple-400" />
                                <span>Dispute / Submit Appeal</span>
                              </button>
                            </div>
                          )}
                        </div>
                      ))
                    )}
                  </div>
                </div>
              )}
            </>
          ) : (
            <div className="bg-slate-900/60 border border-slate-800 rounded-2xl p-12 text-center text-slate-500">
              Select an assignment on the left to view briefing materials and deliver submissions.
            </div>
          )}
        </div>
      </div>

      {/* MODAL: Appeal Evaluation */}
      {showAppealModal && appealRoundId && (
        <div className="fixed inset-0 z-50 bg-black/80 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="bg-slate-900 border border-slate-800 rounded-2xl w-full max-w-md p-6 space-y-4">
            <h3 className="text-lg font-bold text-slate-100 flex items-center gap-2">
              <Scale className="w-5 h-5 text-purple-400" />
              File Evaluation Appeal
            </h3>
            <p className="text-xs text-slate-400 leading-relaxed">
              If an automated test assertion or rubric finding failed due to an environment mismatch, floating point tolerance, or ambiguous specification, state your technical reason below. Submitting an appeal routes the task directly to your company assigner for human adjudication.
            </p>

            <textarea
              rows={4}
              required
              value={appealReason}
              onChange={(e) => setAppealReason(e.target.value)}
              placeholder="Explain the technical evidence or rationale for this appeal..."
              className="w-full bg-slate-950 border border-slate-800 rounded-xl p-3 text-xs text-slate-200 focus:outline-none focus:border-purple-500"
            />

            <div className="flex justify-end space-x-2 pt-2">
              <button
                type="button"
                onClick={() => setShowAppealModal(false)}
                className="px-4 py-2 text-sm text-slate-400 hover:text-slate-200"
              >
                Cancel
              </button>
              <button
                type="button"
                onClick={handleSendAppeal}
                disabled={!appealReason.trim()}
                className="px-5 py-2 bg-purple-600 hover:bg-purple-500 disabled:opacity-50 text-white rounded-xl text-sm font-semibold shadow"
              >
                Submit to Assigner
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
