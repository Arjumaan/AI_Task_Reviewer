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
  Video,
  Radio,
  Key,
  Volume2,
  Briefcase,
  Trash2,
  GraduationCap,
  BookOpen,
  Layers,
  Mail,
  Send,
  Check,
  AlertCircle,
  Info
} from 'lucide-react';

interface AssignerDashboardProps {
  initialTaskId?: string;
}

export const AssignerDashboard: React.FC<AssignerDashboardProps> = ({ initialTaskId }) => {
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
  const [showReviewOutcomeModal, setShowReviewOutcomeModal] = useState(false);
  const [reviewOutcomePassed, setReviewOutcomePassed] = useState(true);
  const [reviewFeedback, setReviewFeedback] = useState('All acceptance criteria met. Implementation verified successfully.');
  const [reviewGaps, setReviewGaps] = useState('1. Handle edge case validation\n2. Add missing integration test');
  const [targetReviewMeetingId, setTargetReviewMeetingId] = useState<string | null>(null);
  const [isSubmittingReviewOutcome, setIsSubmittingReviewOutcome] = useState(false);
  const [reviewOutcomeSuccessMsg, setReviewOutcomeSuccessMsg] = useState<string | null>(null);

  // Form states
  const [newTitle, setNewTitle] = useState('');
  const [selectedInternId, setSelectedInternId] = useState('');
  const [uploadFile, setUploadFile] = useState<File | null>(null);
  const [newDeadline, setNewDeadline] = useState('');
  const [isCreatingTask, setIsCreatingTask] = useState(false);
  const [createTaskError, setCreateTaskError] = useState<string | null>(null);
  const [isEditingDeadline, setIsEditingDeadline] = useState(false);
  const [editDeadlineValue, setEditDeadlineValue] = useState('');
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

  // Intern Roster & Management state
  const [showInternRosterModal, setShowInternRosterModal] = useState(false);
  const [showNewInternModal, setShowNewInternModal] = useState(false);
  const [newInternName, setNewInternName] = useState('');
  const [newInternEmail, setNewInternEmail] = useState('');
  const [newInternPassword, setNewInternPassword] = useState('');
  const [isCreatingIntern, setIsCreatingIntern] = useState(false);
  const [newInternError, setNewInternError] = useState<string | null>(null);
  const [deletingInternId, setDeletingInternId] = useState<string | null>(null);
  const [rosterFeedback, setRosterFeedback] = useState<string | null>(null);
  const [rosterError, setRosterError] = useState<string | null>(null);

  // Bulk Task Assignment State
  const [showBulkModal, setShowBulkModal] = useState(false);
  const [bulkFile, setBulkFile] = useState<File | null>(null);
  const [bulkMeetingUrl, setBulkMeetingUrl] = useState('https://meet.google.com/meet/rqp-ctfg-nri');
  const [bulkCustomTitle, setBulkCustomTitle] = useState('');
  const [bulkDeadlineDays, setBulkDeadlineDays] = useState(7);
  const [bulkTimezone, setBulkTimezone] = useState('Asia/Kolkata');
  const [selectedBulkInternIds, setSelectedBulkInternIds] = useState<string[]>([]);
  const [isBulkSubmitting, setIsBulkSubmitting] = useState(false);
  const [bulkError, setBulkError] = useState<string | null>(null);
  const [bulkSuccessResult, setBulkSuccessResult] = useState<any | null>(null);
  // Excel Multi-Task Assignment State
  const [showExcelModal, setShowExcelModal] = useState(false);
  const [excelFile, setExcelFile] = useState<File | null>(null);
  const [excelTimezone, setExcelTimezone] = useState('Asia/Kolkata');
  const [isExcelSubmitting, setIsExcelSubmitting] = useState(false);
  const [excelError, setExcelError] = useState<string | null>(null);
  const [excelSuccessResult, setExcelSuccessResult] = useState<any | null>(null);


  // Google Meet AI Bot state
  const [botStatus, setBotStatus] = useState<BotStatus | null>(null);
  const [isBotLaunching, setIsBotLaunching] = useState(false);
  const [isSpeakingMode, setIsSpeakingMode] = useState<boolean>(true);
  const [customMeetUrl, setCustomMeetUrl] = useState('https://meet.google.com/meet/rqp-ctfg-nri');
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
      const [allTasks, allUsers] = await Promise.all([
        taskApi.list(),
        authApi.getUsers()
      ]);
      setTasks(allTasks);
      setInterns(allUsers.filter((u) => u.role === 'INTERN'));
      if (selectedTask) {
        const refreshed = await taskApi.get(selectedTask.id);
        setSelectedTask(refreshed);
      } else if (initialTaskId && allTasks.some(t => t.id === initialTaskId)) {
        const match = allTasks.find(t => t.id === initialTaskId);
        if (match) setSelectedTask(match);
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
  }, [initialTaskId]);

  const setDeadlinePreset = (days: number) => {
    const d = new Date();
    d.setDate(d.getDate() + days);
    d.setHours(18, 0, 0, 0);
    const pad = (n: number) => (n < 10 ? '0' + n : n);
    const localIso = `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}T${pad(d.getHours())}:${pad(d.getMinutes())}`;
    setNewDeadline(localIso);
  };

  const handleSaveDeadline = async () => {
    if (!selectedTask || !editDeadlineValue) return;
    try {
      const updated = await taskApi.update(selectedTask.id, {
        deadline_iso: new Date(editDeadlineValue).toISOString()
      });
      setSelectedTask(updated);
      setIsEditingDeadline(false);
      await loadData();
    } catch (err) {
      console.error('Failed to update deadline', err);
    }
  };

  const [isDeletingTask, setIsDeletingTask] = useState(false);

  const handleDeleteTask = async (taskId: string, taskTitle: string, e?: React.MouseEvent) => {
    if (e) e.stopPropagation();
    if (!window.confirm(`Are you sure you want to permanently delete task "${taskTitle}"?\n\nThis will remove all associated meetings, documents, specifications, and notifications.`)) {
      return;
    }
    setIsDeletingTask(true);
    try {
      await taskApi.delete(taskId);
      if (selectedTask?.id === taskId) {
        setSelectedTask(null);
      }
      await loadData();
    } catch (err: any) {
      console.error('Failed to delete task', err);
      alert(err?.response?.data?.detail || 'Failed to delete task.');
    } finally {
      setIsDeletingTask(false);
    }
  };

  const handleCreateTask = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newTitle.trim()) return;
    setIsCreatingTask(true);
    setCreateTaskError(null);
    try {
      let deadlineIso: string | undefined = undefined;
      if (newDeadline) {
        const d = new Date(newDeadline);
        if (!isNaN(d.getTime())) {
          deadlineIso = d.toISOString();
        }
      }

      const created = await taskApi.create({
        title: newTitle.trim(),
        intern_id: selectedInternId || undefined,
        deadline_iso: deadlineIso,
        display_timezone: 'Asia/Kolkata'
      });
      setShowCreateModal(false);
      setNewTitle('');
      setSelectedInternId('');
      setNewDeadline('');
      setCreateTaskError(null);
      await loadData();
      setSelectedTask(created);
    } catch (err: any) {
      console.error('Failed to create task', err);
      const detail = err?.response?.data?.detail || err?.message || 'Failed to create task. Please check server connection.';
      setCreateTaskError(typeof detail === 'string' ? detail : JSON.stringify(detail));
    } finally {
      setIsCreatingTask(false);
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

  const openReviewModal = (meetingOrTaskId: string, defaultPassed: boolean = true) => {
    setTargetReviewMeetingId(meetingOrTaskId);
    setReviewOutcomePassed(defaultPassed);
    if (defaultPassed) {
      setReviewFeedback('All acceptance criteria met. Implementation verified successfully.');
    } else {
      setReviewFeedback('Revisions are required before this task can be approved.');
    }
    setReviewOutcomeSuccessMsg(null);
    setShowReviewOutcomeModal(true);
  };

  const handleSubmitReviewOutcome = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!targetReviewMeetingId) return;
    setIsSubmittingReviewOutcome(true);
    try {
      const gapsList = reviewOutcomePassed
        ? []
        : reviewGaps.split('\n').map((l) => l.trim()).filter((l) => l.length > 0);

      const res = await meetingApi.completeReview(targetReviewMeetingId, {
        passed: reviewOutcomePassed,
        feedback: reviewFeedback.trim(),
        gaps: gapsList.length > 0 ? gapsList : undefined
      });

      setReviewOutcomeSuccessMsg(res.message);
      setTimeout(async () => {
        setShowReviewOutcomeModal(false);
        setReviewOutcomeSuccessMsg(null);
        await loadData();
      }, 1500);
    } catch (err: any) {
      console.error('Failed to complete review evaluation', err);
      alert('Error completing review: ' + (err?.response?.data?.detail || err.message));
    } finally {
      setIsSubmittingReviewOutcome(false);
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
      setNewInternPassword('');
      setRosterFeedback(`Intern "${created.full_name}" registered successfully.`);
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
      await loadData();
    } catch (err: any) {
      const msg = err?.response?.data?.detail || err?.message || 'Failed to delete intern';
      setRosterError(typeof msg === 'string' ? msg : JSON.stringify(msg));
    } finally {
      setDeletingInternId(null);
    }
  };

  const toggleSelectAllInterns = () => {
    if (selectedBulkInternIds.length === interns.length) {
      setSelectedBulkInternIds([]);
    } else {
      setSelectedBulkInternIds(interns.map((i) => i.id));
    }
  };

  const toggleInternSelection = (internId: string) => {
    setSelectedBulkInternIds((prev) =>
      prev.includes(internId) ? prev.filter((id) => id !== internId) : [...prev, internId]
    );
  };

  const handleBulkAssign = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!bulkFile) {
      setBulkError('Please select a common task document (PDF, DOCX, TXT, or MD).');
      return;
    }
    if (!bulkMeetingUrl.trim()) {
      setBulkError('Please enter a Google Meet URL or meeting link.');
      return;
    }
    if (selectedBulkInternIds.length === 0) {
      setBulkError('Please select at least one intern to assign the task.');
      return;
    }

    setIsBulkSubmitting(true);
    setBulkError(null);
    setBulkSuccessResult(null);

    try {
      const formData = new FormData();
      formData.append('file', bulkFile);
      formData.append('intern_ids', JSON.stringify(selectedBulkInternIds));
      formData.append('meeting_url', bulkMeetingUrl.trim());
      if (bulkCustomTitle.trim()) {
        formData.append('custom_title', bulkCustomTitle.trim());
      }
      const deadlineDate = new Date();
      deadlineDate.setDate(deadlineDate.getDate() + bulkDeadlineDays);
      formData.append('deadline_iso', deadlineDate.toISOString());
      formData.append('timezone_str', bulkTimezone);

      const result = await taskApi.bulkAssign(formData);
      setBulkSuccessResult(result);
      await loadData();
    } catch (err: any) {
      const msg = err?.response?.data?.detail || err?.message || 'Failed to bulk-assign tasks';
      setBulkError(typeof msg === 'string' ? msg : JSON.stringify(msg));
    } finally {
      setIsBulkSubmitting(false);
    }
  };

  const handleExcelAssign = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!excelFile) {
      setExcelError('Please select an Excel (.xlsx) or CSV (.csv) file.');
      return;
    }
    setIsExcelSubmitting(true);
    setExcelError(null);
    setExcelSuccessResult(null);
    try {
      const formData = new FormData();
      formData.append('file', excelFile);
      formData.append('timezone_str', excelTimezone);
      const result = await taskApi.excelAssign(formData);
      setExcelSuccessResult(result);
      await loadData();
    } catch (err: any) {
      const msg = err?.response?.data?.detail || err?.message || 'Failed to process Excel assignment';
      setExcelError(typeof msg === 'string' ? msg : JSON.stringify(msg));
    } finally {
      setIsExcelSubmitting(false);
    }
  };

  const resetExcelModal = () => {
    setShowExcelModal(false);
    setExcelFile(null);
    setExcelError(null);
    setExcelSuccessResult(null);
  };

  const resetBulkModal = () => {
    setShowBulkModal(false);
    setBulkFile(null);
    setBulkMeetingUrl('');
    setBulkCustomTitle('');
    setBulkDeadlineDays(7);
    setSelectedBulkInternIds([]);
    setBulkError(null);
    setBulkSuccessResult(null);
  };

  const getStatusBadge = (status: string) => {
    switch (status) {
      case 'SUBMITTED':
        return <span className="bg-purple-950 text-purple-300 border border-purple-800 text-xs px-2.5 py-0.5 rounded-full font-medium">Submitted</span>;
      case 'REVIEW_SCHEDULED':
        return <span className="bg-sky-950 text-sky-300 border border-sky-800 text-xs px-2.5 py-0.5 rounded-full font-medium">Review Scheduled</span>;
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
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8 space-y-8 animate-fadeIn">
      {/* Top action header */}
      <div className="glass-card neo-surface rounded-3xl p-6 sm:p-7 flex flex-col sm:flex-row sm:items-center sm:justify-between gap-5">
        <div className="space-y-1">
          <div className="flex items-center space-x-2 text-xs font-bold uppercase tracking-wider text-cyan-400">
            <Briefcase className="w-4 h-4" />
            <span>Task Assigner Workspace</span>
          </div>
          <h1 className="text-2xl sm:text-3xl font-extrabold text-white tracking-tight">
            Authoring & Evaluation Workspace
          </h1>
          <p className="text-xs sm:text-sm text-slate-300 max-w-2xl">
            Upload assignment briefs, generate AI specification drafts, schedule briefings, and deploy Google Meet autonomous agents.
          </p>
        </div>
        <div className="flex flex-wrap items-center gap-3">
          <button
            onClick={() => loadData()}
            className="p-2.5 rounded-xl neo-btn text-slate-300 hover:text-white transition-colors"
            title="Refresh dashboard"
          >
            <RefreshCw className="w-4 h-4" />
          </button>
          <button
            onClick={() => setShowInternRosterModal(true)}
            className="flex items-center space-x-2 neo-btn text-purple-300 hover:text-purple-200 font-bold text-xs px-4 py-2.5 rounded-xl transition-all"
            title="Manage and delete registered interns"
          >
            <Users className="w-4 h-4 text-purple-400" />
            <span>Intern Roster ({interns.length})</span>
          </button>
          <button
            onClick={() => setShowNewInternModal(true)}
            className="flex items-center space-x-2 neo-btn text-slate-200 font-bold text-xs px-4 py-2.5 rounded-xl transition-all"
          >
            <UserPlus className="w-4 h-4 text-cyan-400" />
            <span>Add New Intern</span>
          </button>
          <button
            onClick={() => {
              setBulkError(null);
              setBulkSuccessResult(null);
              setShowBulkModal(true);
            }}
            className="flex items-center space-x-2 bg-gradient-to-r from-purple-600 to-indigo-600 hover:from-purple-500 hover:to-indigo-500 text-white font-bold text-xs px-4 py-2.5 rounded-xl shadow-lg shadow-purple-500/25 border border-purple-400/30 transition-all active:scale-95"
            title="Upload one document and assign with common meeting URL to multiple interns"
          >
            <Layers className="w-4 h-4 text-purple-200" />
            <span>Bulk Task Upload</span>
          </button>
          <button
            onClick={() => {
              setExcelError(null);
              setExcelSuccessResult(null);
              setShowExcelModal(true);
            }}
            className="flex items-center space-x-2 bg-gradient-to-r from-emerald-600 to-teal-600 hover:from-emerald-500 hover:to-teal-500 text-white font-bold text-xs px-4 py-2.5 rounded-xl shadow-lg shadow-emerald-500/25 border border-emerald-400/30 transition-all active:scale-95"
            title="Upload Excel spreadsheet with separate tasks for each intern"
          >
            <FileText className="w-4 h-4 text-emerald-200" />
            <span>Excel Multi-Task</span>
          </button>

          <button
            onClick={() => setShowCreateModal(true)}
            className="flex items-center space-x-2 glass-btn-primary text-white font-bold text-xs px-4 py-2.5 rounded-xl shadow-lg shadow-cyan-500/20 transition-all active:scale-95"
            title="Create an individual task assignment"
          >
            <Plus className="w-4 h-4" />
            <span>Create Single Task</span>
          </button>
        </div>
      </div>

      {/* Grid: Task list & Selected Task detail */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-8">
        {/* Task List (Left 5 Cols) */}
        <div className="lg:col-span-5 space-y-3">
          <div className="flex items-center justify-between pb-2 border-b border-white/[0.08]">
            <h2 className="text-xs font-bold uppercase tracking-wider text-slate-400">
              Tasks Portfolio ({tasks.length})
            </h2>
            <span className="text-[11px] font-mono text-cyan-400">Select to View</span>
          </div>

          {isLoading && tasks.length === 0 ? (
            <div className="p-8 text-center text-slate-500 glass-card neo-surface rounded-2xl">
              Loading tasks...
            </div>
          ) : tasks.length === 0 ? (
            <div className="p-8 text-center text-slate-500 glass-card neo-surface rounded-2xl">
              No tasks created yet. Click "Create New Task" to begin.
            </div>
          ) : (
            tasks.map((task) => (
              <div
                key={task.id}
                onClick={() => setSelectedTask(task)}
                className={`p-4 rounded-2xl cursor-pointer transition-all ${
                  selectedTask?.id === task.id
                    ? 'glass-card neo-surface border border-cyan-400/50 shadow-lg shadow-cyan-500/20 ring-1 ring-cyan-400/30'
                    : 'glass-card-interactive neo-surface'
                }`}
              >
                <div className="flex items-start justify-between">
                  <h3 className="font-bold text-slate-100 text-sm line-clamp-1">{task.title}</h3>
                  <div className="flex items-center space-x-1 flex-shrink-0 ml-2">
                    <button
                      type="button"
                      onClick={(e) => handleDeleteTask(task.id, task.title, e)}
                      title="Delete task"
                      className="p-1 text-slate-500 hover:text-rose-400 hover:bg-rose-950/50 rounded transition-colors"
                    >
                      <Trash2 className="w-3.5 h-3.5" />
                    </button>
                    <ChevronRight className="w-4 h-4 text-slate-500" />
                  </div>
                </div>
                <div className="flex items-center justify-between mt-3">
                  <div className="text-xs text-slate-400 flex items-center gap-1.5">
                    Intern: <strong className="text-slate-300">{task.intern_id ? interns.find((i) => i.id === task.intern_id)?.full_name || 'Assigned' : 'Unassigned'}</strong>
                    {task.submissions && task.submissions.length > 0 && (
                      <span className="text-[10px] bg-purple-950/80 text-purple-300 border border-purple-800/80 px-1.5 py-0.5 rounded-md font-bold">
                        📦 Submitted
                      </span>
                    )}
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
            <div className="glass-card neo-surface rounded-3xl p-6 sm:p-7 space-y-6">
              {/* Task Header */}
              <div className="flex flex-col sm:flex-row sm:items-start sm:justify-between pb-4 border-b border-slate-800 gap-4">
                <div className="space-y-1.5">
                  <span className="text-xs font-mono text-cyan-400">ID: {selectedTask.id.substring(0, 8)}...</span>
                  <h2 className="text-xl font-bold text-slate-100">{selectedTask.title}</h2>
                  <div className="flex flex-wrap items-center gap-3 pt-1.5">
                    <div className="flex items-center space-x-2">
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

                    <div className="flex items-center space-x-2 pl-3 border-l border-slate-800">
                      <span className="text-xs font-medium text-slate-400 flex items-center gap-1">
                        <Clock className="w-3.5 h-3.5 text-amber-400" />
                        Deadline:
                      </span>
                      {isEditingDeadline ? (
                        <div className="flex items-center gap-1.5">
                          <input
                            type="datetime-local"
                            value={editDeadlineValue}
                            onChange={(e) => setEditDeadlineValue(e.target.value)}
                            className="bg-slate-950 border border-amber-500/50 rounded-lg px-2 py-0.5 text-xs text-amber-200 focus:outline-none [color-scheme:dark]"
                          />
                          <button
                            type="button"
                            onClick={handleSaveDeadline}
                            className="px-2 py-0.5 bg-amber-600 hover:bg-amber-500 text-white rounded text-xs font-semibold"
                          >
                            Save
                          </button>
                          <button
                            type="button"
                            onClick={() => setIsEditingDeadline(false)}
                            className="px-1.5 py-0.5 text-slate-400 hover:text-slate-200 text-xs"
                          >
                            ✕
                          </button>
                        </div>
                      ) : (
                        <div className="flex items-center gap-1.5">
                          <span className="text-xs font-bold text-amber-300 font-mono">
                            {selectedTask.versions && selectedTask.versions.length > 0 && selectedTask.versions[selectedTask.versions.length - 1].deadline_utc
                              ? new Date(selectedTask.versions[selectedTask.versions.length - 1].deadline_utc).toLocaleString('en-US', {
                                  dateStyle: 'medium',
                                  timeStyle: 'short'
                                })
                              : 'Not set (defaults to 7 days)'}
                          </span>
                          <button
                            type="button"
                            onClick={() => {
                              const curr = selectedTask.versions?.[selectedTask.versions.length - 1]?.deadline_utc;
                              if (curr) {
                                const d = new Date(curr);
                                const pad = (n: number) => (n < 10 ? '0' + n : n);
                                setEditDeadlineValue(`${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}T${pad(d.getHours())}:${pad(d.getMinutes())}`);
                              } else {
                                setEditDeadlineValue('');
                              }
                              setIsEditingDeadline(true);
                            }}
                            className="px-1.5 py-0.5 bg-slate-800 hover:bg-slate-700 text-[10px] text-slate-300 rounded transition-colors"
                            title="Edit or assign deadline"
                          >
                            Edit
                          </button>
                        </div>
                      )}
                    </div>
                  </div>
                </div>
                <div>{getStatusBadge(selectedTask.status)}</div>
              </div>

              {/* INTERN SUBMISSION REVIEW & GATE BANNER */}
              {selectedTask.submissions && selectedTask.submissions.length > 0 ? (
                <div className="p-4 bg-gradient-to-r from-purple-950/70 via-indigo-950/40 to-slate-900 border border-purple-500/50 rounded-2xl space-y-3 shadow-lg shadow-purple-950/30">
                  <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 pb-2 border-b border-purple-800/40">
                    <div className="flex items-center gap-2">
                      <span className="w-2.5 h-2.5 rounded-full bg-emerald-400 animate-pulse" />
                      <span className="text-xs font-bold text-purple-200 tracking-wide uppercase">
                        🚀 Intern Deliverables Submitted (Round #{selectedTask.submissions.length})
                      </span>
                    </div>
                    <span className="text-[11px] text-slate-400 font-mono">
                      Submitted {new Date(selectedTask.submissions[selectedTask.submissions.length - 1].created_at).toLocaleString('en-IN', { dateStyle: 'medium', timeStyle: 'short' })}
                    </span>
                  </div>

                  <div className="grid grid-cols-1 md:grid-cols-2 gap-3 text-xs">
                    <div className="bg-slate-950/80 border border-slate-800/80 p-3 rounded-xl space-y-1">
                      <span className="text-slate-400 font-medium">Git Repository:</span>
                      <div className="flex items-center gap-2">
                        <a
                          href={selectedTask.submissions[selectedTask.submissions.length - 1].repository_url}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="text-cyan-400 hover:text-cyan-300 font-mono underline break-all flex items-center gap-1 font-semibold"
                        >
                          <span>{selectedTask.submissions[selectedTask.submissions.length - 1].repository_url}</span>
                          <ExternalLink className="w-3 h-3 flex-shrink-0" />
                        </a>
                      </div>
                      {selectedTask.submissions[selectedTask.submissions.length - 1].commit_hash && (
                        <div className="text-[11px] text-slate-500 font-mono">
                          Commit: <span className="text-slate-300">{selectedTask.submissions[selectedTask.submissions.length - 1].commit_hash}</span>
                        </div>
                      )}
                    </div>

                    <div className="bg-slate-950/80 border border-slate-800/80 p-3 rounded-xl space-y-1">
                      <span className="text-slate-400 font-medium">Intern Implementation Notes:</span>
                      <p className="text-slate-300 italic text-[11px] leading-relaxed line-clamp-3">
                        {selectedTask.submissions[selectedTask.submissions.length - 1].notes || 'No extra notes provided.'}
                      </p>
                    </div>
                  </div>

                  <div className="flex flex-wrap items-center justify-between gap-2 pt-1">
                    <span className="text-xs text-purple-300/90 font-medium">
                      {selectedTask.status === 'PASSED'
                        ? '✅ This task has been reviewed and approved.'
                        : 'Review the code above and the Google Meet session demo, then record the official outcome:'}
                    </span>
                    {selectedTask.status !== 'PASSED' && (
                      <button
                        onClick={() => openReviewModal(selectedTask.id)}
                        className="px-4 py-2 bg-gradient-to-r from-emerald-600 to-teal-600 hover:from-emerald-500 hover:to-teal-500 text-white font-bold rounded-xl text-xs shadow-md shadow-emerald-950/50 flex items-center gap-1.5 transition-all active:scale-95 ml-auto"
                      >
                        <CheckCircle className="w-3.5 h-3.5" />
                        <span>Review & Evaluate (Pass / Revise)</span>
                      </button>
                    )}
                  </div>
                </div>
              ) : (
                <div className="p-3.5 bg-slate-950/60 border border-slate-800/80 rounded-xl flex items-center justify-between text-xs gap-3">
                  <div className="flex items-center gap-2 text-slate-400">
                    <Clock className="w-4 h-4 text-amber-400 flex-shrink-0" />
                    <span>
                      <strong className="text-slate-300">Pending Intern Deliverables:</strong> Intern has not submitted their code repository yet.
                    </span>
                  </div>
                  <span className="text-[11px] text-slate-500 font-medium bg-slate-900 border border-slate-800 px-2 py-0.5 rounded-md flex-shrink-0">
                    Evaluation Gate: Awaiting Submission
                  </span>
                </div>
              )}

              {/* Action Toolbar */}
              <div className="flex flex-wrap gap-2.5">
                <button
                  onClick={() => setShowUploadModal(true)}
                  className="flex items-center space-x-1.5 px-3.5 py-2 neo-btn rounded-xl text-xs font-semibold text-slate-200 transition-all"
                >
                  <Upload className="w-3.5 h-3.5 text-cyan-400" />
                  <span>Upload Brief (PDF/DOCX)</span>
                </button>

                <button
                  onClick={handleExtractDraft}
                  className="flex items-center space-x-1.5 px-4 py-2 glass-btn-primary rounded-xl text-xs font-bold text-white shadow-md shadow-cyan-500/20 transition-all active:scale-95"
                >
                  <Sparkles className="w-3.5 h-3.5" />
                  <span>AI Spec Drafter</span>
                </button>

                <button
                  onClick={() => {
                    setMeetingType('BRIEFING');
                    setShowScheduleModal(true);
                  }}
                  className="flex items-center space-x-1.5 px-3.5 py-2 neo-btn rounded-xl text-xs font-semibold text-slate-200 transition-all"
                >
                  <Calendar className="w-3.5 h-3.5 text-blue-400" />
                  <span>Schedule Meeting</span>
                </button>

                <button
                  type="button"
                  onClick={() => handleDeleteTask(selectedTask.id, selectedTask.title)}
                  disabled={isDeletingTask}
                  className="flex items-center space-x-1.5 px-3.5 py-2 bg-rose-950/60 hover:bg-rose-900/80 border border-rose-800/60 hover:border-rose-600 rounded-xl text-xs font-semibold text-rose-300 transition-all ml-auto"
                  title="Permanently delete this task and all associated records"
                >
                  <Trash2 className="w-3.5 h-3.5 text-rose-400" />
                  <span>{isDeletingTask ? 'Deleting...' : 'Delete Task'}</span>
                </button>
              </div>

              {/* Uploaded Documents & AI Intelligence */}
              <div>
                <h4 className="text-xs font-semibold uppercase tracking-wider text-slate-400 mb-2">
                  Uploaded Documents & Knowledge Ingestion ({selectedTask.documents?.length || 0})
                </h4>
                {selectedTask.documents && selectedTask.documents.length > 0 ? (
                  <div className="space-y-4">
                    {selectedTask.documents.map((doc) => {
                      let analysis: any = null;
                      if (doc.analysis_json) {
                        try {
                          analysis = JSON.parse(doc.analysis_json);
                        } catch (e) {
                          // ignore json parse error
                        }
                      }
                      return (
                        <div key={doc.id} className="space-y-3">
                          <div
                            className="flex items-center justify-between p-3.5 neo-inset rounded-2xl text-xs"
                          >
                            <div className="flex items-center space-x-2.5">
                              <FileText className="w-4 h-4 text-cyan-400" />
                              <span className="font-semibold text-slate-200">{doc.original_filename || doc.filename || 'Document'}</span>
                              <span className="text-slate-500">({(doc.file_size_bytes / 1024).toFixed(1)} KB)</span>
                            </div>
                            <div className="flex items-center gap-2">
                              {analysis && (
                                <span className="text-cyan-400 flex items-center gap-1 neo-inset px-2.5 py-0.5 rounded-full border border-cyan-500/30 text-[11px] font-semibold">
                                  <Sparkles className="w-3 h-3 text-cyan-400 animate-pulse" /> Document Analyzed
                                </span>
                              )}
                              {doc.has_detected_injection ? (
                                <span className="flex items-center text-rose-400 gap-1 font-semibold neo-inset px-2.5 py-0.5 rounded-full border border-rose-500/30">
                                  <ShieldAlert className="w-3.5 h-3.5" /> Injection Flagged
                                </span>
                              ) : (
                                <span className="text-emerald-400 flex items-center gap-1 neo-inset px-2.5 py-0.5 rounded-full border border-emerald-500/30 font-medium">
                                  <CheckCircle2 className="w-3.5 h-3.5" /> Verified Clean
                                </span>
                              )}
                            </div>
                          </div>

                          {/* AI Document Intelligence Card */}
                          {analysis && (
                            <div className="glass-card neo-surface rounded-2xl p-4.5 sm:p-5 border border-cyan-500/30 space-y-3.5 text-xs animate-fadeIn">
                              <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 pb-3 border-b border-white/[0.08]">
                                <div className="flex items-center space-x-2">
                                  <div className="w-7 h-7 rounded-lg bg-cyan-500/10 border border-cyan-500/30 flex items-center justify-center text-cyan-400">
                                    <Sparkles className="w-4 h-4 text-cyan-400" />
                                  </div>
                                  <div>
                                    <span className="text-xs font-bold uppercase tracking-wider text-cyan-300">
                                      AI Document Comprehension & Grounding
                                    </span>
                                    <h5 className="font-bold text-slate-100 text-sm">{analysis.title || doc.original_filename || doc.filename}</h5>
                                  </div>
                                </div>
                                <span className="inline-flex items-center gap-1.5 text-[11px] font-mono text-emerald-400 neo-inset px-3 py-1 rounded-full border border-emerald-500/30 self-start sm:self-auto">
                                  <span className="w-2 h-2 rounded-full bg-emerald-400 animate-ping" />
                                  Bot Ready to Explain in Meet
                                </span>
                              </div>

                              {analysis.executive_summary && (
                                <div className="space-y-1">
                                  <span className="text-[11px] font-bold uppercase tracking-wider text-slate-400">Executive Summary</span>
                                  <p className="text-slate-300 leading-relaxed neo-inset p-3 rounded-xl border border-white/[0.05]">
                                    {analysis.executive_summary}
                                  </p>
                                </div>
                              )}

                              {analysis.items && analysis.items.length > 0 && (
                                <div className="space-y-2">
                                  <div className="flex items-center justify-between">
                                    <span className="text-[11px] font-bold uppercase tracking-wider text-slate-400">
                                      Extracted Issue & Defect Catalog ({analysis.items.length})
                                    </span>
                                    <span className="text-[10px] text-cyan-400 font-mono">Grounded Knowledge</span>
                                  </div>
                                  <div className="max-h-48 overflow-y-auto space-y-1.5 pr-1">
                                    {analysis.items.map((item: any, idx: number) => (
                                      <div key={idx} className="flex flex-col sm:flex-row sm:items-center justify-between p-2.5 rounded-xl neo-inset border border-white/[0.04] text-xs gap-1.5">
                                        <div className="flex items-center space-x-2">
                                          <span className="font-mono font-bold text-cyan-400 bg-cyan-950/60 border border-cyan-800/80 px-2 py-0.5 rounded text-[11px]">
                                            {item.code}
                                          </span>
                                          <span className="font-medium text-slate-200">{item.title}</span>
                                        </div>
                                        <div className="flex items-center gap-2 self-start sm:self-auto">
                                          {item.category && (
                                            <span className="text-[10px] text-indigo-300 font-mono bg-indigo-950/60 px-2 py-0.5 rounded">
                                              {item.category}
                                            </span>
                                          )}
                                          {item.severity && (
                                            <span className={`text-[10px] font-mono px-2 py-0.5 rounded ${
                                              item.severity === 'CRITICAL' ? 'bg-rose-950 text-rose-300 border border-rose-800' :
                                              item.severity === 'HIGH' ? 'bg-amber-950 text-amber-300 border border-amber-800' :
                                              'bg-slate-800 text-slate-300'
                                            }`}>
                                              {item.severity}
                                            </span>
                                          )}
                                        </div>
                                      </div>
                                    ))}
                                  </div>
                                </div>
                              )}

                              {analysis.spoken_briefing_script && (
                                <div className="p-3 bg-indigo-950/30 border border-indigo-500/20 rounded-xl space-y-1">
                                  <div className="flex items-center space-x-1.5 text-indigo-300 font-semibold text-[11px]">
                                    <Volume2 className="w-3.5 h-3.5 text-indigo-400" />
                                    <span>Subha's Meeting Briefing Guide</span>
                                  </div>
                                  <p className="text-slate-300 text-xs italic leading-relaxed">
                                    "{analysis.spoken_briefing_script}"
                                  </p>
                                </div>
                              )}
                            </div>
                          )}
                        </div>
                      );
                    })}
                  </div>
                ) : (
                  <p className="text-xs text-slate-500 italic neo-inset p-3.5 rounded-2xl">No document uploaded yet.</p>
                )}
              </div>

              {/* Approved Specification View */}
              {selectedTask.versions && selectedTask.versions.length > 0 && (
                <div className="p-5 glass-card neo-surface border border-cyan-500/30 rounded-2xl space-y-3">
                  <div className="flex items-center justify-between">
                    <span className="text-xs font-bold uppercase text-cyan-400 flex items-center gap-1.5">
                      <CheckCircle className="w-4 h-4 text-cyan-400" /> Approved Specification (v{selectedTask.versions[0].version_number})
                    </span>
                    <span className="text-xs text-slate-400 font-mono">Timezone: {selectedTask.versions[0].timezone}</span>
                  </div>
                  <p className="text-sm text-slate-200 font-medium leading-relaxed">{selectedTask.versions[0].objective}</p>
                  <div className="grid grid-cols-2 gap-4 pt-3 text-xs text-slate-400 border-t border-white/[0.08]">
                    <div>
                      <span className="block font-bold text-slate-300">Deliverables:</span>
                      {selectedTask.versions[0].deliverables}
                    </div>
                    <div>
                      <span className="block font-bold text-slate-300">Requirements Count:</span>
                      {selectedTask.versions[0].requirements?.length || 0} items
                    </div>
                  </div>
                </div>
              )}

              {/* Autonomous Google Meet Bot Quick Dispatcher */}
              <div className="glass-card neo-surface rounded-3xl p-6 border border-indigo-500/30 space-y-4">
                <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pb-3 border-b border-white/[0.08]">
                  <div className="flex items-center space-x-3">
                    <div className="w-9 h-9 rounded-xl bg-indigo-500/10 border border-indigo-500/20 flex items-center justify-center text-indigo-400">
                      <Bot className="w-5 h-5" />
                    </div>
                    <div>
                      <h4 className="text-xs font-bold uppercase tracking-wider text-indigo-300">
                        Google Meet AI Agent Dispatcher
                      </h4>
                      <p className="text-[11px] text-slate-400">Autonomous voice agent for live meetings</p>
                    </div>
                  </div>
                  <div className="flex items-center gap-2">
                    {isGoogleAuthed ? (
                      <span className="flex items-center gap-1 text-[11px] font-mono text-emerald-400 neo-inset px-3 py-1 rounded-full border border-emerald-500/30">
                        <CheckCircle2 className="w-3 h-3 text-emerald-400" /> Google Account Linked
                      </span>
                    ) : (
                      <button
                        type="button"
                        onClick={handleLaunchGoogleLogin}
                        disabled={isLaunchingLogin}
                        className="flex items-center gap-1.5 text-[11px] font-bold text-amber-300 neo-btn px-3 py-1.5 rounded-xl border border-amber-500/40 hover:border-amber-400 transition-colors shadow-sm"
                        title="Click to open Chrome and sign in to your Google Account"
                      >
                        <Key className="w-3 h-3 text-amber-400" />
                        <span>{isLaunchingLogin ? 'Opening Chrome...' : 'Sign in Bot to Google'}</span>
                      </button>
                    )}
                    {botStatus?.is_running ? (
                      <span className="flex items-center gap-1.5 text-[11px] font-mono text-emerald-400 neo-inset px-3 py-1 rounded-full border border-emerald-500/30">
                        <span className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse" />
                        {botStatus.status === 'in_call_recording'
                          ? (botStatus.is_speaking ? 'In-Call (Speaking & Recording)' : 'In-Call (Recording)')
                          : botStatus.status === 'joining'
                          ? 'Joining Call...'
                          : botStatus.bot_id
                          ? `MeetingBaas (${botStatus.status})`
                          : `Agent Active (PID: ${botStatus.pid})`}
                      </span>
                    ) : (
                      <span className="text-[11px] font-mono text-slate-400 neo-inset px-3 py-1 rounded-full border border-slate-700/60">
                        Agent Standby
                      </span>
                    )}
                  </div>
                </div>

                <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
                  <p className="text-xs text-slate-400 leading-relaxed flex-1">
                    Enter any Google Meet URL or code below. The bot will join open calls directly or request host admission.
                  </p>
                  <label className="flex items-center gap-2 cursor-pointer text-xs font-semibold select-none neo-surface px-3.5 py-2 rounded-xl border border-white/[0.08] hover:border-indigo-500/50 transition-colors flex-shrink-0">
                    <input
                      type="checkbox"
                      checked={isSpeakingMode}
                      onChange={(e) => setIsSpeakingMode(e.target.checked)}
                      className="w-4 h-4 rounded text-indigo-600 focus:ring-indigo-500 bg-slate-900 border-slate-700 cursor-pointer"
                    />
                    <span className={isSpeakingMode ? "text-indigo-300 font-bold flex items-center gap-1.5" : "text-slate-400 flex items-center gap-1.5"}>
                      <Volume2 className={`w-3.5 h-3.5 ${isSpeakingMode ? 'text-indigo-400' : 'text-slate-500'}`} />
                      {isSpeakingMode ? 'Interactive Speaking Bot' : 'Silent Recording Bot'}
                    </span>
                  </label>
                </div>

                <form onSubmit={handleLaunchDirectBot} className="flex flex-col sm:flex-row gap-2.5">
                  <input
                    type="text"
                    placeholder="e.g. rqp-ctfg-nri or https://meet.google.com/rqp-ctfg-nri"
                    value={customMeetUrl}
                    onChange={(e) => setCustomMeetUrl(e.target.value)}
                    className="flex-1 neo-inset rounded-xl px-4 py-2.5 text-xs text-slate-100 placeholder-slate-500 focus:outline-none focus:border-indigo-400/50 font-mono transition-colors"
                  />
                  <div className="flex gap-2">
                    <button
                      type="submit"
                      disabled={isBotLaunching || !customMeetUrl.trim()}
                      className="flex items-center justify-center space-x-1.5 px-4 py-2.5 glass-btn-primary disabled:opacity-50 text-white rounded-xl text-xs font-bold transition-all shadow-md active:scale-95"
                    >
                      <Bot className="w-3.5 h-3.5" />
                      <span>{isBotLaunching ? 'Dispatching...' : (isSpeakingMode ? 'Dispatch Speaking Bot' : 'Dispatch Recording Bot')}</span>
                    </button>
                    {botStatus?.is_running && (
                      <button
                        type="button"
                        onClick={handleStopBot}
                        className="flex items-center space-x-1 px-3.5 py-2.5 bg-rose-950/80 hover:bg-rose-900 border border-rose-700/60 rounded-xl text-rose-200 text-xs font-bold transition-colors"
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
                          {/* Complete Review Button: ONLY for REVIEW sessions and only when task isn't already PASSED */}
                          {m.meeting_type === 'REVIEW' && selectedTask?.status !== 'PASSED' && (
                            <button
                              onClick={() => openReviewModal(m.id)}
                              className="inline-flex items-center space-x-1.5 px-3 py-1.5 bg-emerald-600/20 hover:bg-emerald-600/30 border border-emerald-500/50 rounded-lg text-emerald-300 font-semibold text-xs transition-colors sm:ml-auto shadow-sm shadow-emerald-950/50"
                              title="Record review evaluation outcome (Pass / Revise) and dispatch official email"
                            >
                              <CheckCircle className="w-3.5 h-3.5 text-emerald-400" />
                              <span>Complete Review</span>
                            </button>
                          )}
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
                                onClick={() => openReviewModal(selectedTask.id)}
                                className="flex items-center space-x-1 px-3 py-1 bg-emerald-700 hover:bg-emerald-600 text-white rounded font-medium transition-colors"
                                title="Evaluate Review and send Pass / Revision email"
                              >
                                <CheckCircle className="w-3.5 h-3.5" />
                                <span>Record Review Outcome</span>
                              </button>
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
              {createTaskError && (
                <div className="p-3 bg-rose-950/70 border border-rose-800 rounded-xl text-xs text-rose-200 font-medium flex items-center gap-2">
                  <AlertTriangle className="w-4 h-4 text-rose-400 flex-shrink-0" />
                  <span>{createTaskError}</span>
                </div>
              )}
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

              <div>
                <div className="flex items-center justify-between mb-1">
                  <label className="block text-xs font-semibold text-slate-400 uppercase tracking-wider">
                    Task Submission Deadline
                  </label>
                  <span className="text-[11px] text-cyan-400 font-mono">Optional / Defaults to 7 days</span>
                </div>
                <input
                  type="datetime-local"
                  value={newDeadline}
                  onChange={(e) => setNewDeadline(e.target.value)}
                  className="w-full bg-slate-950 border border-slate-800 rounded-xl px-4 py-2.5 text-sm text-slate-100 focus:outline-none focus:border-cyan-500 [color-scheme:dark]"
                />
                <div className="flex items-center gap-1.5 mt-2">
                  <span className="text-[11px] text-slate-500 mr-1">Quick Presets:</span>
                  <button
                    type="button"
                    onClick={() => setDeadlinePreset(3)}
                    className="px-2 py-0.5 bg-slate-800 hover:bg-slate-700 text-slate-300 text-xs rounded-md transition-colors"
                  >
                    +3 Days
                  </button>
                  <button
                    type="button"
                    onClick={() => setDeadlinePreset(7)}
                    className="px-2 py-0.5 bg-cyan-950 border border-cyan-800/60 hover:bg-cyan-900 text-cyan-300 text-xs font-semibold rounded-md transition-colors"
                  >
                    +7 Days
                  </button>
                  <button
                    type="button"
                    onClick={() => setDeadlinePreset(14)}
                    className="px-2 py-0.5 bg-slate-800 hover:bg-slate-700 text-slate-300 text-xs rounded-md transition-colors"
                  >
                    +14 Days
                  </button>
                  <button
                    type="button"
                    onClick={() => setDeadlinePreset(30)}
                    className="px-2 py-0.5 bg-slate-800 hover:bg-slate-700 text-slate-300 text-xs rounded-md transition-colors"
                  >
                    +30 Days
                  </button>
                </div>
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
                  disabled={isCreatingTask || !newTitle.trim()}
                  className="px-5 py-2 bg-cyan-600 hover:bg-cyan-500 disabled:opacity-50 text-white rounded-xl text-sm font-semibold shadow flex items-center gap-2"
                >
                  {isCreatingTask ? (
                    <>
                      <RefreshCw className="w-4 h-4 animate-spin" />
                      <span>Creating...</span>
                    </>
                  ) : (
                    <span>Create Task</span>
                  )}
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

      {/* MODAL: Complete Review Outcome & Dispatch Email */}
      {showReviewOutcomeModal && (
        <div className="fixed inset-0 z-50 bg-black/80 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="bg-slate-900 border border-slate-800 rounded-2xl w-full max-w-xl p-6 space-y-4 shadow-2xl">
            <div className="flex items-center justify-between">
              <div>
                <h3 className="text-lg font-bold text-slate-100 flex items-center gap-2">
                  <CheckCircle className="w-5 h-5 text-emerald-400" />
                  <span>Complete Review Meeting Evaluation</span>
                </h3>
                <p className="text-xs text-slate-400 mt-1">
                  Evaluate the intern implementation and presentation. The decision will trigger official SMTP email dispatch.
                </p>
              </div>
              <button
                onClick={() => setShowReviewOutcomeModal(false)}
                className="text-slate-500 hover:text-slate-300 text-sm p-1"
              >
                ✕
              </button>
            </div>

            {reviewOutcomeSuccessMsg && (
              <div className="p-3 bg-emerald-950/60 border border-emerald-800 rounded-xl text-xs text-emerald-200 font-medium">
                ✓ {reviewOutcomeSuccessMsg}
              </div>
            )}

            <form onSubmit={handleSubmitReviewOutcome} className="space-y-4">
              {/* Submission Context Preview */}
              {selectedTask?.submissions && selectedTask.submissions.length > 0 ? (
                <div className="p-3 bg-slate-950 border border-slate-800 rounded-xl text-xs space-y-1.5">
                  <span className="text-xs font-bold text-slate-300 uppercase tracking-wider">
                    📦 Deliverables Under Review (Round #{selectedTask.submissions.length}):
                  </span>
                  <div className="flex items-center gap-2 font-mono text-cyan-300">
                    <span>Repo:</span>
                    <a
                      href={selectedTask.submissions[selectedTask.submissions.length - 1].repository_url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="underline break-all"
                    >
                      {selectedTask.submissions[selectedTask.submissions.length - 1].repository_url}
                    </a>
                  </div>
                  {selectedTask.submissions[selectedTask.submissions.length - 1].notes && (
                    <div className="text-slate-400 text-[11px] italic">
                      Notes: "{selectedTask.submissions[selectedTask.submissions.length - 1].notes}"
                    </div>
                  )}
                </div>
              ) : (
                <div className="p-3 bg-amber-950/40 border border-amber-800/60 rounded-xl text-xs text-amber-300 flex items-center gap-2">
                  <AlertTriangle className="w-4 h-4 text-amber-400 flex-shrink-0" />
                  <span>Note: Intern has not delivered code repository yet. You can evaluate the live voice presentation or request code submission.</span>
                </div>
              )}

              <div>
                <label className="block text-xs font-semibold text-slate-400 uppercase tracking-wider mb-2">
                  Evaluation Outcome
                </label>
                <div className="grid grid-cols-2 gap-3">
                  <button
                    type="button"
                    onClick={() => {
                      setReviewOutcomePassed(true);
                      setReviewFeedback('All acceptance criteria met. Implementation verified successfully.');
                    }}
                    className={`p-3 rounded-xl border text-left flex items-center space-x-3 transition-all ${
                      reviewOutcomePassed
                        ? 'bg-emerald-950/60 border-emerald-500 text-emerald-200 ring-2 ring-emerald-500/30'
                        : 'bg-slate-950/60 border-slate-800 text-slate-400 hover:border-slate-700'
                    }`}
                  >
                    <div className="w-4 h-4 rounded-full border-2 border-emerald-400 flex items-center justify-center">
                      {reviewOutcomePassed && <div className="w-2 h-2 rounded-full bg-emerald-400" />}
                    </div>
                    <div>
                      <div className="font-bold text-sm text-slate-100">PASSED</div>
                      <div className="text-[11px] text-slate-400">Accept and congratulate</div>
                    </div>
                  </button>

                  <button
                    type="button"
                    onClick={() => {
                      setReviewOutcomePassed(false);
                      setReviewFeedback('Revisions are required before this task can be approved.');
                    }}
                    className={`p-3 rounded-xl border text-left flex items-center space-x-3 transition-all ${
                      !reviewOutcomePassed
                        ? 'bg-rose-950/60 border-rose-500 text-rose-200 ring-2 ring-rose-500/30'
                        : 'bg-slate-950/60 border-slate-800 text-slate-400 hover:border-slate-700'
                    }`}
                  >
                    <div className="w-4 h-4 rounded-full border-2 border-rose-400 flex items-center justify-center">
                      {!reviewOutcomePassed && <div className="w-2 h-2 rounded-full bg-rose-400" />}
                    </div>
                    <div>
                      <div className="font-bold text-sm text-slate-100">REVISION REQUIRED</div>
                      <div className="text-[11px] text-slate-400">Generate next review & meet link</div>
                    </div>
                  </button>
                </div>
              </div>

              {/* Notice Banner */}
              {reviewOutcomePassed ? (
                <div className="p-3 bg-emerald-950/40 border border-emerald-800/60 rounded-xl text-xs text-emerald-300">
                  <span className="font-semibold">Email Action:</span> Dispatches congratulations email via live SMTP:
                  <div className="font-mono text-[11px] mt-1 text-slate-200 italic">
                    "Your task has been completed. Congratulations. Wait until the next task is being assigned."
                  </div>
                </div>
              ) : (
                <div className="p-3 bg-rose-950/40 border border-rose-800/60 rounded-xl text-xs text-rose-300">
                  <span className="font-semibold">Email Action:</span> Dispatches revision notice via live SMTP:
                  <div className="font-mono text-[11px] mt-1 text-slate-200 italic">
                    "These needs to be changed: [Action Items List]"
                  </div>
                  <div className="text-[11px] text-slate-300 mt-1">
                    Auto-schedules next review in 2 days and generates a <strong>NEW Google Meet link</strong>.
                  </div>
                </div>
              )}

              {/* Feedback text */}
              <div>
                <label className="block text-xs font-semibold text-slate-400 uppercase tracking-wider mb-1">
                  Evaluation Feedback & Summary
                </label>
                <textarea
                  rows={2}
                  required
                  value={reviewFeedback}
                  onChange={(e) => setReviewFeedback(e.target.value)}
                  className="w-full bg-slate-950 border border-slate-800 rounded-xl p-3 text-xs text-slate-100 focus:outline-none focus:border-cyan-500"
                />
              </div>

              {/* Gaps list if Revision Required */}
              {!reviewOutcomePassed && (
                <div>
                  <label className="block text-xs font-semibold text-rose-400 uppercase tracking-wider mb-1">
                    Action Items / Changes Needed (one per line)
                  </label>
                  <textarea
                    rows={3}
                    required
                    value={reviewGaps}
                    onChange={(e) => setReviewGaps(e.target.value)}
                    placeholder="1. Fix validation error on invalid input&#10;2. Increase test coverage"
                    className="w-full bg-slate-950 border border-rose-800/60 rounded-xl p-3 text-xs text-slate-100 focus:outline-none focus:border-rose-500 font-mono"
                  />
                </div>
              )}

              <div className="flex justify-end space-x-2 pt-3 border-t border-slate-800">
                <button
                  type="button"
                  onClick={() => setShowReviewOutcomeModal(false)}
                  className="px-4 py-2 text-sm text-slate-400 hover:text-slate-200"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={isSubmittingReviewOutcome}
                  className={`px-5 py-2 rounded-xl text-sm font-semibold text-white shadow flex items-center space-x-2 ${
                    reviewOutcomePassed
                      ? 'bg-emerald-600 hover:bg-emerald-500'
                      : 'bg-rose-600 hover:bg-rose-500'
                  }`}
                >
                  {isSubmittingReviewOutcome ? (
                    <>
                      <RefreshCw className="w-4 h-4 animate-spin" />
                      <span>Dispatching Notice...</span>
                    </>
                  ) : (
                    <span>Confirm & Dispatch Email</span>
                  )}
                </button>
              </div>
            </form>
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
                  placeholder="Enter initial password (min 6 chars)"
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

      {/* MODAL 7: Manage Intern Roster & Deletions */}
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
                    Review assigned tasks, register new candidates, or delete interns from your workspace.
                  </p>
                </div>
              </div>
              <button
                onClick={() => {
                  setShowInternRosterModal(false);
                  setShowNewInternModal(true);
                }}
                className="flex items-center space-x-1.5 glass-btn-primary text-white text-xs font-bold px-3 py-2 rounded-xl"
              >
                <UserPlus className="w-3.5 h-3.5" />
                <span>+ Register Intern</span>
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
                  No interns currently registered. Click "+ Register Intern" to onboard a candidate.
                </div>
              ) : (
                interns.map((intern) => {
                  const assignedCount = tasks.filter(t => t.intern_id === intern.id).length;
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

      {/* MODAL 8: Bulk Task Upload & Assignment with SMTP Notification */}
      {showBulkModal && (
        <div className="fixed inset-0 z-50 bg-black/85 backdrop-blur-md flex items-center justify-center p-3 sm:p-5 overflow-y-auto animate-fadeIn">
          <div className="glass-card neo-surface rounded-3xl w-full max-w-4xl p-6 sm:p-8 space-y-6 border border-white/[0.14] shadow-2xl my-auto">
            {/* Modal Header */}
            <div className="flex items-start justify-between pb-4 border-b border-white/[0.08]">
              <div className="space-y-1">
                <div className="flex items-center space-x-2 text-xs font-bold uppercase tracking-wider text-purple-400">
                  <Layers className="w-4 h-4" />
                  <span>HR / Tech Lead Bulk Operations</span>
                  <span className="neo-inset px-2 py-0.5 rounded-full text-[10px] text-cyan-300 font-mono">
                    SMTP Automated Dispatch
                  </span>
                </div>
                <h3 className="text-xl sm:text-2xl font-extrabold text-white tracking-tight flex items-center gap-2">
                  <span>Bulk Task Assignment</span>
                  <span className="text-sm font-normal text-slate-400">
                    — One Document, Multiple Interns
                  </span>
                </h3>
                <p className="text-xs text-slate-300 max-w-2xl">
                  Upload a single common task document, configure a shared Google Meet briefing link, and assign individual tasks to selected interns. Each intern receives an automated SMTP notification email with the document attached and briefing link.
                </p>
              </div>
              <button
                type="button"
                onClick={resetBulkModal}
                className="p-2 text-slate-400 hover:text-white rounded-xl neo-btn text-xs font-bold"
              >
                ✕
              </button>
            </div>

            {/* Success Results Screen */}
            {bulkSuccessResult ? (
              <div className="space-y-6 py-2 animate-fadeIn">
                <div className="p-5 neo-inset rounded-2xl border border-emerald-500/30 bg-emerald-950/30 space-y-3">
                  <div className="flex items-center space-x-3 text-emerald-300">
                    <div className="w-10 h-10 rounded-xl bg-emerald-500/20 border border-emerald-500/30 flex items-center justify-center text-emerald-400 flex-shrink-0">
                      <CheckCircle2 className="w-6 h-6" />
                    </div>
                    <div>
                      <h4 className="text-base font-bold text-white">
                        Bulk Assignment Completed Successfully!
                      </h4>
                      <p className="text-xs text-emerald-300">
                        {bulkSuccessResult.message || `Successfully assigned tasks to ${bulkSuccessResult.assigned_count} interns.`}
                      </p>
                    </div>
                  </div>

                  <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 pt-2 text-xs">
                    <div className="p-3 bg-black/40 rounded-xl border border-white/[0.06]">
                      <span className="text-slate-400 block text-[11px]">Task Title</span>
                      <span className="font-semibold text-slate-100 truncate block">
                        {bulkSuccessResult.task_title}
                      </span>
                    </div>
                    <div className="p-3 bg-black/40 rounded-xl border border-white/[0.06]">
                      <span className="text-slate-400 block text-[11px]">Assigned Interns</span>
                      <span className="font-semibold text-cyan-300">
                        {bulkSuccessResult.assigned_count} Assigned
                      </span>
                    </div>
                    <div className="p-3 bg-black/40 rounded-xl border border-white/[0.06]">
                      <span className="text-slate-400 block text-[11px]">Deadline</span>
                      <span className="font-semibold text-amber-300">
                        {bulkSuccessResult.deadline}
                      </span>
                    </div>
                    <div className="p-3 bg-black/40 rounded-xl border border-white/[0.06]">
                      <span className="text-slate-400 block text-[11px]">Email Provider</span>
                      <span className="font-semibold text-purple-300 flex items-center gap-1">
                        <Mail className="w-3 h-3" />
                        <span>SMTP Dispatched</span>
                      </span>
                    </div>
                  </div>
                </div>

                {/* Assigned Interns & Delivery Status List */}
                <div className="space-y-3">
                  <h5 className="text-xs font-bold uppercase tracking-wider text-slate-400 flex items-center justify-between">
                    <span>Assigned Candidates & Email Delivery Log</span>
                    <span className="text-cyan-400 font-mono text-[11px]">
                      Shared Briefing Link: {bulkSuccessResult.common_meeting_url}
                    </span>
                  </h5>
                  <div className="max-h-60 overflow-y-auto space-y-2 pr-1">
                    {bulkSuccessResult.tasks?.map((t: any, idx: number) => (
                      <div
                        key={t.task_id || idx}
                        className="p-3 neo-inset rounded-xl border border-white/[0.06] flex items-center justify-between text-xs"
                      >
                        <div className="flex items-center space-x-3">
                          <div className="w-7 h-7 rounded-lg bg-purple-500/20 text-purple-300 flex items-center justify-center font-bold">
                            {idx + 1}
                          </div>
                          <div>
                            <span className="font-bold text-slate-100 block">{t.intern_name}</span>
                            <span className="text-slate-400 font-mono text-[11px]">{t.intern_email}</span>
                          </div>
                        </div>
                        <div className="flex items-center space-x-3">
                          <span className="neo-inset px-2.5 py-1 rounded-full text-[11px] text-emerald-300 border border-emerald-500/20 flex items-center gap-1">
                            <Check className="w-3 h-3 text-emerald-400" />
                            <span>Task & Spec Created</span>
                          </span>
                          <span className="neo-inset px-2.5 py-1 rounded-full text-[11px] text-purple-300 border border-purple-500/20 flex items-center gap-1">
                            <Mail className="w-3 h-3 text-purple-400" />
                            <span>SMTP {t.email_status}</span>
                          </span>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>

                <div className="flex items-center justify-between pt-4 border-t border-white/[0.08]">
                  <a
                    href={bulkSuccessResult.common_meeting_url}
                    target="_blank"
                    rel="noreferrer"
                    className="flex items-center space-x-2 text-xs text-cyan-400 hover:text-cyan-300 font-semibold"
                  >
                    <ExternalLink className="w-4 h-4" />
                    <span>Open Common Google Meet Room</span>
                  </a>
                  <div className="flex space-x-3">
                    <button
                      type="button"
                      onClick={() => {
                        setBulkSuccessResult(null);
                        setBulkFile(null);
                        setBulkCustomTitle('');
                        setSelectedBulkInternIds([]);
                      }}
                      className="neo-btn text-slate-300 px-4 py-2 rounded-xl text-xs font-semibold"
                    >
                      Assign Another Batch
                    </button>
                    <button
                      type="button"
                      onClick={resetBulkModal}
                      className="glass-btn-primary text-white px-5 py-2 rounded-xl text-xs font-bold"
                    >
                      Done & Close
                    </button>
                  </div>
                </div>
              </div>
            ) : (
              /* Bulk Assignment Form */
              <form onSubmit={handleBulkAssign} className="space-y-6">
                {bulkError && (
                  <div className="p-3.5 bg-rose-950/70 border border-rose-800 text-rose-300 text-xs rounded-xl flex items-center space-x-2 animate-shake">
                    <AlertCircle className="w-4 h-4 text-rose-400 flex-shrink-0" />
                    <span>{bulkError}</span>
                  </div>
                )}

                <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
                  {/* Left Column: Document Upload & Meeting URL (7 Cols) */}
                  <div className="lg:col-span-7 space-y-4">
                    {/* Common Task Document Upload Zone */}
                    <div className="space-y-1.5">
                      <label className="block text-xs font-bold uppercase tracking-wider text-slate-300">
                        1. Common Task Document <span className="text-rose-400">*</span>
                      </label>
                      <div className="border-2 border-dashed border-white/[0.12] hover:border-purple-400/50 rounded-2xl p-5 text-center neo-inset transition-all relative">
                        <input
                          type="file"
                          accept=".pdf,.docx,.txt,.md"
                          required
                          onChange={(e) => {
                            const file = e.target.files?.[0] || null;
                            setBulkFile(file);
                            if (file && !bulkCustomTitle) {
                              const cleanName = file.name.replace(/\.[^/.]+$/, "").replace(/[-_]/g, " ");
                              setBulkCustomTitle(cleanName);
                            }
                          }}
                          className="absolute inset-0 w-full h-full opacity-0 cursor-pointer z-10"
                        />
                        <div className="flex flex-col items-center justify-center space-y-2 pointer-events-none">
                          <div className="w-12 h-12 rounded-2xl bg-purple-500/10 border border-purple-500/20 flex items-center justify-center text-purple-400">
                            {bulkFile ? <FileText className="w-6 h-6 text-purple-300" /> : <Upload className="w-6 h-6 text-purple-400" />}
                          </div>
                          {bulkFile ? (
                            <div>
                              <p className="text-sm font-bold text-white">{bulkFile.name}</p>
                              <p className="text-xs text-purple-300 font-mono mt-0.5">
                                {(bulkFile.size / 1024).toFixed(1)} KB • Document Ready for Analysis
                              </p>
                            </div>
                          ) : (
                            <div>
                              <p className="text-xs font-semibold text-slate-200">
                                Click or drag & drop task specification file
                              </p>
                              <p className="text-[11px] text-slate-400 mt-0.5">
                                Supports PDF, DOCX, TXT, MD (Analyzed by AI & attached to notification emails)
                              </p>
                            </div>
                          )}
                        </div>
                      </div>
                    </div>

                    {/* Common Google Meet URL */}
                    <div className="space-y-1.5">
                      <label className="block text-xs font-bold uppercase tracking-wider text-slate-300 flex items-center justify-between">
                        <span>2. Common Meeting URL (Google Meet) <span className="text-rose-400">*</span></span>
                        <span className="text-[10px] text-cyan-400 font-mono lowercase">Uploaded by the HR</span>
                      </label>
                      <div className="relative">
                        <input
                          type="url"
                          required
                          value={bulkMeetingUrl}
                          onChange={(e) => setBulkMeetingUrl(e.target.value)}
                          placeholder="https://meet.google.com/abc-defg-hij"
                          className="w-full bg-slate-950/80 border border-white/[0.12] focus:border-purple-400 rounded-xl px-4 py-2.5 text-xs text-slate-100 placeholder-slate-500 font-mono focus:outline-none shadow-inner"
                        />
                      </div>
                      <p className="text-[11px] text-slate-400">
                        This meeting link is automatically shared with all assigned interns and embedded in the briefing notification email.
                      </p>
                    </div>

                    {/* Optional Custom Title Override & Timezone */}
                    <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                      <div className="space-y-1">
                        <label className="block text-xs font-semibold text-slate-400 uppercase tracking-wider">
                          Task Title (Optional Override)
                        </label>
                        <input
                          type="text"
                          value={bulkCustomTitle}
                          onChange={(e) => setBulkCustomTitle(e.target.value)}
                          placeholder="Leave blank for AI auto-title"
                          className="w-full bg-slate-950/80 border border-white/[0.12] focus:border-purple-400 rounded-xl px-3 py-2 text-xs text-slate-100 placeholder-slate-500 focus:outline-none"
                        />
                      </div>

                      <div className="space-y-1">
                        <label className="block text-xs font-semibold text-slate-400 uppercase tracking-wider">
                          Timezone
                        </label>
                        <select
                          value={bulkTimezone}
                          onChange={(e) => setBulkTimezone(e.target.value)}
                          className="w-full bg-slate-950/80 border border-white/[0.12] focus:border-purple-400 rounded-xl px-3 py-2 text-xs text-slate-100 focus:outline-none"
                        >
                          <option value="Asia/Kolkata">Asia/Kolkata (IST)</option>
                          <option value="UTC">UTC (Universal)</option>
                          <option value="America/New_York">America/New_York (EST)</option>
                          <option value="Europe/London">Europe/London (BST/GMT)</option>
                        </select>
                      </div>
                    </div>

                    {/* Completion Deadline Selector */}
                    <div className="space-y-1.5">
                      <label className="block text-xs font-bold uppercase tracking-wider text-slate-300">
                        3. Completion Deadline
                      </label>
                      <div className="grid grid-cols-4 gap-2">
                        {[3, 7, 14, 21].map((days) => (
                          <button
                            key={days}
                            type="button"
                            onClick={() => setBulkDeadlineDays(days)}
                            className={`py-2 px-3 rounded-xl text-xs font-bold transition-all ${
                              bulkDeadlineDays === days
                                ? 'bg-gradient-to-r from-purple-600 to-indigo-600 text-white shadow-md border border-purple-400/40'
                                : 'neo-btn text-slate-300 hover:text-white'
                            }`}
                          >
                            {days} Days
                          </button>
                        ))}
                      </div>
                      <p className="text-[11px] text-slate-400">
                        Calculated target deadline: {new Date(Date.now() + bulkDeadlineDays * 86400000).toLocaleDateString('en-US', {
                          weekday: 'short',
                          year: 'numeric',
                          month: 'short',
                          day: 'numeric'
                        })} ({bulkDeadlineDays} calendar days)
                      </p>
                    </div>
                  </div>

                  {/* Right Column: Intern Selection Roster (5 Cols) */}
                  <div className="lg:col-span-5 space-y-3 flex flex-col justify-between">
                    <div className="space-y-2">
                      <div className="flex items-center justify-between pb-1">
                        <label className="text-xs font-bold uppercase tracking-wider text-slate-300 flex items-center gap-1.5">
                          <Users className="w-4 h-4 text-purple-400" />
                          <span>4. Select Interns ({selectedBulkInternIds.length}/{interns.length})</span>
                        </label>
                        <button
                          type="button"
                          onClick={toggleSelectAllInterns}
                          className="text-[11px] text-purple-300 hover:text-purple-200 font-semibold neo-btn px-2.5 py-1 rounded-lg"
                        >
                          {selectedBulkInternIds.length === interns.length ? 'Deselect All' : 'Select All'}
                        </button>
                      </div>

                      {/* Intern Checklist Box */}
                      <div className="neo-inset rounded-2xl border border-white/[0.08] p-2.5 max-h-72 overflow-y-auto space-y-2">
                        {interns.length === 0 ? (
                          <div className="text-center py-8 text-slate-400 text-xs">
                            No registered interns found. Add interns via the "Add New Intern" button first.
                          </div>
                        ) : (
                          interns.map((intern) => {
                            const isSelected = selectedBulkInternIds.includes(intern.id);
                            return (
                              <div
                                key={intern.id}
                                onClick={() => toggleInternSelection(intern.id)}
                                className={`p-2.5 rounded-xl border cursor-pointer transition-all flex items-center justify-between ${
                                  isSelected
                                    ? 'bg-purple-950/40 border-purple-500/40 text-white shadow-sm'
                                    : 'bg-black/20 border-white/[0.04] text-slate-300 hover:border-white/[0.1]'
                                }`}
                              >
                                <div className="flex items-center space-x-3">
                                  <div
                                    className={`w-5 h-5 rounded-md flex items-center justify-center transition-all ${
                                      isSelected
                                        ? 'bg-purple-500 text-white'
                                        : 'border border-slate-600 bg-slate-900'
                                    }`}
                                  >
                                    {isSelected && <Check className="w-3.5 h-3.5 stroke-[3]" />}
                                  </div>
                                  <div className="truncate">
                                    <div className="text-xs font-bold truncate">{intern.full_name}</div>
                                    <div className="text-[11px] text-slate-400 font-mono truncate">
                                      {intern.email}
                                    </div>
                                  </div>
                                </div>
                                <GraduationCap className={`w-3.5 h-3.5 flex-shrink-0 ${isSelected ? 'text-purple-300' : 'text-slate-500'}`} />
                              </div>
                            );
                          })
                        )}
                      </div>
                    </div>

                    {/* Live Email Notification Preview */}
                    <div className="neo-inset rounded-2xl border border-purple-500/20 bg-purple-950/20 p-3 space-y-1.5 text-xs">
                      <div className="flex items-center space-x-2 text-[11px] font-bold text-purple-300">
                        <Mail className="w-3.5 h-3.5 text-purple-400" />
                        <span>SMTP Email Notification Template</span>
                      </div>
                      <div className="p-2.5 bg-black/60 rounded-xl font-mono text-[11px] text-slate-300 leading-relaxed border border-white/[0.06]">
                        <p className="text-purple-200">
                          "This is your assigned task <span className="text-white font-bold underline">{bulkCustomTitle || (bulkFile ? bulkFile.name.replace(/\.[^/.]+$/, "") : "[Task Title]")}</span> must be completed within <span className="text-amber-300 font-bold underline">{new Date(Date.now() + bulkDeadlineDays * 86400000).toLocaleDateString()}</span> deadline. The task document (<span className="text-cyan-300 underline">{bulkFile?.name || "[Document Filename]"}</span>) (Uploaded by the HR) and a common meeting URL <span className="text-cyan-300 underline">{bulkMeetingUrl || "[Google Meet URL]"}</span> (Also Uploaded by the HR)."
                        </p>
                      </div>
                      <div className="flex items-center justify-between text-[10px] text-slate-400 pt-1">
                        <span>Includes task specification & document attachment</span>
                        <span className="text-emerald-400 font-semibold">Live SMTP Supported</span>
                      </div>
                    </div>
                  </div>
                </div>

                {/* Form Footer */}
                <div className="flex items-center justify-between pt-4 border-t border-white/[0.08]">
                  <button
                    type="button"
                    onClick={resetBulkModal}
                    className="neo-btn text-slate-300 px-5 py-2.5 rounded-xl text-xs font-semibold"
                  >
                    Cancel
                  </button>
                  <button
                    type="submit"
                    disabled={isBulkSubmitting || !bulkFile || !bulkMeetingUrl.trim() || selectedBulkInternIds.length === 0}
                    className="flex items-center space-x-2 bg-gradient-to-r from-purple-600 via-indigo-600 to-cyan-600 hover:from-purple-500 hover:to-cyan-500 disabled:opacity-40 disabled:cursor-not-allowed text-white font-bold text-xs px-6 py-3 rounded-xl shadow-xl shadow-purple-500/25 border border-purple-400/40 transition-all active:scale-95"
                  >
                    {isBulkSubmitting ? (
                      <>
                        <RefreshCw className="w-4 h-4 animate-spin text-purple-200" />
                        <span>Analyzing Brief & Dispatching SMTP Emails...</span>
                      </>
                    ) : (
                      <>
                        <Send className="w-4 h-4" />
                        <span>
                          Upload & Assign to {selectedBulkInternIds.length} {selectedBulkInternIds.length === 1 ? 'Intern' : 'Interns'}
                        </span>
                      </>
                    )}
                  </button>
                </div>
              </form>
            )}
          </div>
        </div>
      )}

      {/* MODAL 9: Excel Multi-Task Upload & Assignment */}
      {showExcelModal && (
        <div className="fixed inset-0 z-50 bg-black/85 backdrop-blur-md flex items-center justify-center p-3 sm:p-5 overflow-y-auto animate-fadeIn">
          <div className="glass-card neo-surface rounded-3xl w-full max-w-3xl p-6 sm:p-8 space-y-6 border border-white/[0.14] shadow-2xl my-auto">
            {/* Header */}
            <div className="flex items-start justify-between pb-4 border-b border-white/[0.08]">
              <div className="space-y-1">
                <div className="flex items-center space-x-2 text-xs font-bold uppercase tracking-wider text-emerald-400">
                  <FileText className="w-4 h-4" />
                  <span>HR Multi-Task Operations</span>
                  <span className="neo-inset px-2 py-0.5 rounded-full text-[10px] text-teal-300 font-mono">
                    Excel Ingestion
                  </span>
                </div>
                <h3 className="text-xl sm:text-2xl font-extrabold text-white tracking-tight flex items-center gap-2">
                  <span>Excel Multi-Task Assignment</span>
                  <span className="text-sm font-normal text-slate-400">— Separate Tasks for Each Intern</span>
                </h3>
                <p className="text-xs text-slate-300 max-w-xl">
                  Upload an Excel spreadsheet containing separate task specifications for each intern. The system auto-provisions candidate accounts, generates unique Google Meet briefing links, and dispatches individual SMTP notification emails.
                </p>
              </div>
              <button
                type="button"
                onClick={resetExcelModal}
                className="p-2 text-slate-400 hover:text-white rounded-xl neo-btn text-xs font-bold"
              >
                ✕
              </button>
            </div>

            {excelSuccessResult ? (
              <div className="space-y-5 animate-fadeIn">
                <div className="p-5 neo-inset rounded-2xl border border-emerald-500/30 bg-emerald-950/30 space-y-3">
                  <div className="flex items-center space-x-3 text-emerald-300">
                    <CheckCircle2 className="w-8 h-8 text-emerald-400 flex-shrink-0" />
                    <div>
                      <h4 className="text-base font-bold text-white">Excel Assignment Completed!</h4>
                      <p className="text-xs text-emerald-300">{excelSuccessResult.message}</p>
                    </div>
                  </div>
                  <div className="max-h-60 overflow-y-auto space-y-2 pr-1">
                    {excelSuccessResult.assignments?.map((a: any, i: number) => (
                      <div key={i} className="p-3 neo-inset rounded-xl border border-white/[0.06] flex items-center justify-between text-xs">
                        <div className="flex items-center space-x-3">
                          <div className="w-7 h-7 rounded-lg bg-emerald-500/20 text-emerald-300 flex items-center justify-center font-bold">
                            {i + 1}
                          </div>
                          <div>
                            <span className="font-bold text-slate-100 block">{a.intern_name}</span>
                            <span className="text-slate-400 font-mono text-[11px]">{a.intern_email}</span>
                          </div>
                        </div>
                        <div className="text-right">
                          <span className="text-cyan-300 text-[11px] font-semibold block">{a.task_title}</span>
                          <span className="text-emerald-400 text-[10px] font-mono">SMTP {a.email_status}</span>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
                <div className="flex justify-end space-x-3 pt-3 border-t border-white/[0.08]">
                  <button
                    type="button"
                    onClick={() => { setExcelSuccessResult(null); setExcelFile(null); }}
                    className="neo-btn text-slate-300 px-4 py-2 rounded-xl text-xs font-semibold"
                  >
                    Assign Another File
                  </button>
                  <button
                    type="button"
                    onClick={resetExcelModal}
                    className="glass-btn-primary text-white px-5 py-2 rounded-xl text-xs font-bold"
                  >
                    Done & Close
                  </button>
                </div>
              </div>
            ) : (
              <form onSubmit={handleExcelAssign} className="space-y-5">
                {excelError && (
                  <div className="p-3.5 bg-rose-950/70 border border-rose-800 text-rose-300 text-xs rounded-xl flex items-center space-x-2">
                    <AlertCircle className="w-4 h-4 text-rose-400 flex-shrink-0" />
                    <span>{excelError}</span>
                  </div>
                )}

                {/* Download Template Card */}
                <div className="p-4 neo-inset rounded-2xl border border-emerald-500/20 bg-emerald-950/20 flex items-center justify-between">
                  <div className="flex items-center space-x-3">
                    <Info className="w-5 h-5 text-emerald-400 flex-shrink-0" />
                    <div className="text-xs">
                      <p className="text-slate-200 font-semibold">Download the required Excel template</p>
                      <p className="text-slate-400 text-[11px]">Columns: Intern Email, Intern Name, Task Title, Task Objective / Requirements, Deadline Date, Meeting Time</p>
                    </div>
                  </div>
                  <a
                    href={taskApi.getExcelTemplate()}
                    target="_blank"
                    rel="noreferrer"
                    className="flex items-center space-x-1.5 neo-btn text-emerald-300 hover:text-emerald-200 text-xs font-bold px-3 py-2 rounded-xl"
                  >
                    <ExternalLink className="w-3.5 h-3.5" />
                    <span>Download Template</span>
                  </a>
                </div>

                {/* File Upload Zone */}
                <div className="space-y-1.5">
                  <label className="block text-xs font-bold uppercase tracking-wider text-slate-300">
                    Upload Spreadsheet <span className="text-rose-400">*</span>
                  </label>
                  <div className="border-2 border-dashed border-white/[0.12] hover:border-emerald-400/50 rounded-2xl p-5 text-center neo-inset transition-all relative">
                    <input
                      type="file"
                      accept=".xlsx,.csv"
                      required
                      onChange={(e) => setExcelFile(e.target.files?.[0] || null)}
                      className="absolute inset-0 w-full h-full opacity-0 cursor-pointer z-10"
                    />
                    <div className="flex flex-col items-center justify-center space-y-2 pointer-events-none">
                      <div className="w-12 h-12 rounded-2xl bg-emerald-500/10 border border-emerald-500/20 flex items-center justify-center text-emerald-400">
                        {excelFile ? <FileText className="w-6 h-6 text-emerald-300" /> : <Upload className="w-6 h-6 text-emerald-400" />}
                      </div>
                      {excelFile ? (
                        <div>
                          <p className="text-sm font-bold text-white">{excelFile.name}</p>
                          <p className="text-xs text-emerald-300 font-mono mt-0.5">{(excelFile.size / 1024).toFixed(1)} KB • File Ready</p>
                        </div>
                      ) : (
                        <div>
                          <p className="text-xs font-semibold text-slate-200">Click or drag & drop Excel / CSV spreadsheet</p>
                          <p className="text-[11px] text-slate-400 mt-0.5">Supports .xlsx and .csv formats</p>
                        </div>
                      )}
                    </div>
                  </div>
                </div>

                {/* Timezone */}
                <div className="space-y-1">
                  <label className="block text-xs font-semibold text-slate-400 uppercase tracking-wider">Default Timezone</label>
                  <select
                    value={excelTimezone}
                    onChange={(e) => setExcelTimezone(e.target.value)}
                    className="w-full bg-slate-950/80 border border-white/[0.12] focus:border-emerald-400 rounded-xl px-3 py-2 text-xs text-slate-100 focus:outline-none"
                  >
                    <option value="Asia/Kolkata">Asia/Kolkata (IST)</option>
                    <option value="UTC">UTC (Universal)</option>
                    <option value="America/New_York">America/New_York (EST)</option>
                    <option value="Europe/London">Europe/London (BST/GMT)</option>
                  </select>
                </div>

                {/* Footer Buttons */}
                <div className="flex items-center justify-between pt-4 border-t border-white/[0.08]">
                  <button
                    type="button"
                    onClick={resetExcelModal}
                    className="neo-btn text-slate-300 px-5 py-2.5 rounded-xl text-xs font-semibold"
                  >
                    Cancel
                  </button>
                  <button
                    type="submit"
                    disabled={isExcelSubmitting || !excelFile}
                    className="flex items-center space-x-2 bg-gradient-to-r from-emerald-600 via-teal-600 to-cyan-600 hover:from-emerald-500 hover:to-cyan-500 disabled:opacity-40 disabled:cursor-not-allowed text-white font-bold text-xs px-6 py-3 rounded-xl shadow-xl shadow-emerald-500/25 border border-emerald-400/40 transition-all active:scale-95"
                  >
                    {isExcelSubmitting ? (
                      <>
                        <RefreshCw className="w-4 h-4 animate-spin text-emerald-200" />
                        <span>Processing Excel & Dispatching Emails...</span>
                      </>
                    ) : (
                      <>
                        <Send className="w-4 h-4" />
                        <span>Upload & Assign Tasks</span>
                      </>
                    )}
                  </button>
                </div>
              </form>
            )}
          </div>
        </div>
      )}
    </div>
  );
};
