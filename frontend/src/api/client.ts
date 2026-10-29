import axios from 'axios';
import {
  User,
  Task,
  TaskSpecificationDraft,
  Meeting,
  Submission,
  ReviewRound,
  AuditLog,
  ModelBenchmark,
  HealthStatus
} from '../types';

const API_BASE = 'http://localhost:8000/api/v1';

export const apiClient = axios.create({
  baseURL: API_BASE,
});

apiClient.interceptors.request.use((config) => {
  const token = localStorage.getItem('token');
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

// Authentication API
export const authApi = {
  login: async (username: string, password: string) => {
    const formData = new URLSearchParams();
    formData.append('username', username);
    formData.append('password', password);
    const res = await apiClient.post<{ access_token: string; token_type: string }>('/auth/login', formData, {
      headers: { 'Content-Type': 'application/x-www-form-urlencoded' }
    });
    return res.data;
  },
  register: async (data: { email: string; full_name: string; password: string; role?: string }) => {
    const res = await apiClient.post<User>('/auth/register', data);
    return res.data;
  },
  getMe: async () => {
    const res = await apiClient.get<User>('/auth/me');
    return res.data;
  },
  getUsers: async () => {
    const res = await apiClient.get<User[]>('/users/');
    return res.data;
  },
  createUser: async (data: { email: string; full_name: string; role: string; password: string }) => {
    const res = await apiClient.post<User>('/users/', data);
    return res.data;
  },
  deleteUser: async (userId: string) => {
    const res = await apiClient.delete<{ message: string; id: string }>(`/users/${userId}`);
    return res.data;
  }
};

// Tasks API
export const taskApi = {
  list: async () => {
    const res = await apiClient.get<Task[]>('/tasks/');
    return res.data;
  },
  get: async (taskId: string) => {
    const res = await apiClient.get<Task>(`/tasks/${taskId}`);
    return res.data;
  },
  create: async (data: { title: string; intern_id?: string; deadline_iso?: string; display_timezone?: string }) => {
    const res = await apiClient.post<Task>('/tasks/', data);
    return res.data;
  },
  delete: async (taskId: string) => {
    const res = await apiClient.delete<{ status: string; deleted_task_id: string; title: string; message: string }>(`/tasks/${taskId}`);
    return res.data;
  },
  bulkAssign: async (formData: FormData) => {
    const res = await apiClient.post<{
      message: string;
      task_title: string;
      common_document: string;
      common_meeting_url: string;
      deadline: string;
      timezone: string;
      assigned_count: number;
      tasks: Array<{
        task_id: string;
        intern_id: string;
        intern_name: string;
        intern_email: string;
        meeting_id: string;
        email_status: string;
      }>;
      email_dispatch_summary: any[];
    }>('/tasks/bulk-assign', formData, {
      headers: { 'Content-Type': 'multipart/form-data' }
    });
    return res.data;
  },
  getSmtpStatus: async () => {
    const res = await apiClient.get<any>('/tasks/diagnostics/smtp');
    return res.data;
  },
  excelAssign: async (formData: FormData) => {
    const res = await apiClient.post<{
      message: string;
      source_file: string;
      assigned_count: number;
      assignments: Array<{
        task_id: string;
        intern_id: string;
        intern_name: string;
        intern_email: string;
        task_title: string;
        meeting_id: string;
        meeting_url: string;
        deadline: string;
        email_status: string;
      }>;
    }>('/tasks/excel-assign', formData, {
      headers: { 'Content-Type': 'multipart/form-data' }
    });
    return res.data;
  },
  getExcelTemplate: () => {
    return `${API_BASE}/tasks/excel-template`;
  },
  uploadDocument: async (taskId: string, file: File) => {
    const formData = new FormData();
    formData.append('file', file);
    const res = await apiClient.post(`/tasks/${taskId}/upload`, formData, {
      headers: { 'Content-Type': 'multipart/form-data' }
    });
    return res.data;
  },
  extractDraft: async (taskId: string) => {
    const res = await apiClient.post<TaskSpecificationDraft>(`/tasks/${taskId}/extract-draft`);
    return res.data;
  },
  approveSpecification: async (taskId: string, draft: TaskSpecificationDraft) => {
    const res = await apiClient.post<Task>(`/tasks/${taskId}/approve-specification`, draft);
    return res.data;
  },
  update: async (taskId: string, data: { title?: string; intern_id?: string; deadline_iso?: string; display_timezone?: string }) => {
    const res = await apiClient.patch<Task>(`/tasks/${taskId}`, data);
    return res.data;
  },
  voiceChat: async (taskId: string, message: string, sessionType: 'BRIEFING' | 'REVIEW' = 'BRIEFING') => {
    const res = await apiClient.post<{
      reply: string;
      speaker: string;
      task_title: string;
      session_type: string;
      audio_base64?: string | null;
      voice_name?: string | null;
    }>(`/tasks/${taskId}/voice-chat`, { message, session_type: sessionType });
    return res.data;
  },
  synthesizeSpeech: async (text: string) => {
    const res = await apiClient.post<{
      audio_base64: string | null;
      voice_name?: string;
      format: string;
      model?: string;
    }>('/tasks/synthesize-speech', { text });
    return res.data;
  }
};

// Scheduling API
export const schedulingApi = {
  scheduleMeeting: async (data: {
    task_id: string;
    meeting_type: 'BRIEFING' | 'REVIEW';
    start_time_iso: string;
    duration_minutes?: number;
    timezone?: string;
  }) => {
    const res = await apiClient.post<Meeting>('/scheduling/meetings', data);
    return res.data;
  },
  getTaskMeetings: async (taskId: string) => {
    const res = await apiClient.get<Meeting[]>(`/scheduling/tasks/${taskId}/meetings`);
    return res.data;
  }
};

// Submissions API
export const submissionApi = {
  create: async (data: { task_id: string; repository_url: string; commit_hash?: string; notes?: string }) => {
    const res = await apiClient.post<Submission>('/submissions/', data);
    return res.data;
  },
  getMy: async () => {
    const res = await apiClient.get<Submission[]>('/submissions/my');
    return res.data;
  },
  getByTask: async (taskId: string) => {
    const res = await apiClient.get<Submission[]>(`/submissions/task/${taskId}`);
    return res.data;
  }
};

// Reviews API
export const reviewApi = {
  evaluate: async (roundId: string, data: { test_output?: string; repo_url?: string; meeting_transcripts?: string[] }) => {
    const res = await apiClient.post<ReviewRound>(`/reviews/${roundId}/evaluate`, data);
    return res.data;
  },
  appeal: async (roundId: string, reason: string) => {
    const res = await apiClient.post<ReviewRound>(`/reviews/${roundId}/appeal`, { reason });
    return res.data;
  },
  override: async (roundId: string, outcome: string, notes: string) => {
    const res = await apiClient.post<ReviewRound>(`/reviews/${roundId}/override`, { outcome, notes });
    return res.data;
  }
};

// Admin & System API
export const adminApi = {
  getHealth: async () => {
    const res = await apiClient.get<HealthStatus>('/health');
    return res.data;
  },
  getAuditLogs: async () => {
    const res = await apiClient.get<AuditLog[]>('/audit/');
    return res.data;
  },
  getBenchmarks: async () => {
    const res = await apiClient.get<ModelBenchmark[]>('/benchmarks/');
    return res.data;
  },
  runBenchmark: async (prompt?: string) => {
    const res = await apiClient.post<ModelBenchmark>('/benchmarks/run', { prompt });
    return res.data;
  }
};

export interface BotStatus {
  is_running: boolean;
  bot_id?: string | null;
  status?: string | null;
  is_speaking?: boolean;
  meet_url?: string | null;
  meeting_id?: string | null;
  duration_seconds?: number | null;
  has_video?: boolean;
  has_transcription?: boolean;
  pid?: number | null;
  started_at?: string | null;
}

// Meeting Bot & Session API
export const meetingApi = {
  listAll: async () => {
    const res = await apiClient.get<Meeting[]>('/meetings/');
    return res.data;
  },
  getBotStatus: async () => {
    const res = await apiClient.get<BotStatus>('/meetings/bot-status');
    return res.data;
  },
  launchDirectBot: async (meet_url: string, is_speaking: boolean = true, task_id?: string) => {
    const res = await apiClient.post<{ status: string; bot_id?: string; pid?: number; meet_url: string; message: string; is_speaking?: boolean }>('/meetings/launch-direct', {
      meet_url,
      is_speaking,
      bot_name: 'Subha HR',
      task_id
    });
    return res.data;
  },
  launchMeetingBot: async (meetingId: string, is_speaking: boolean = true) => {
    const res = await apiClient.post<{ status: string; bot_id?: string; pid?: number; meeting_id: string; google_meet_url: string; message: string; is_speaking?: boolean }>(`/meetings/${meetingId}/launch-bot`, {
      is_speaking
    });
    return res.data;
  },
  stopBot: async () => {
    const res = await apiClient.post<{ status: string; bot_id?: string; message: string }>('/meetings/stop-bot');
    return res.data;
  },
  syncBaasTranscripts: async (meetingId: string, botId?: string) => {
    const res = await apiClient.post(`/meetings/${meetingId}/sync-baas`, null, {
      params: botId ? { bot_id: botId } : {}
    });
    return res.data;
  },
  listBaasBots: async () => {
    const res = await apiClient.get<any[]>('/meetings/baas/bots');
    return res.data;
  },
  getGoogleAuthStatus: async () => {
    const res = await apiClient.get<{ authenticated: boolean }>('/meetings/google-auth-status');
    return res.data;
  },
  completeBriefing: async (meetingId: string) => {
    const res = await apiClient.post<{
      status: string;
      feedback_summary: string;
      task_status: string;
      review_meeting_id: string;
      review_meeting_url: string;
      review_scheduled_at: string;
    }>(`/meetings/${meetingId}/complete-briefing`);
    return res.data;
  },
  completeReview: async (meetingId: string, data: { passed: boolean; feedback: string; gaps?: string[] }) => {
    const res = await apiClient.post<{
      status: string;
      message: string;
      task_id?: string;
      next_meeting_id?: string;
      next_meeting_url?: string;
      next_review_scheduled_at?: string;
      gaps?: string[];
    }>(`/meetings/${meetingId}/complete-review`, data);
    return res.data;
  },
  launchGoogleLogin: async () => {
    const res = await apiClient.post<{ status: string; pid?: number; message: string }>('/meetings/launch-google-login');
    return res.data;
  }
};
