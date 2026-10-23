export type UserRole = 'ADMIN' | 'ASSIGNER' | 'INTERN';

export interface User {
  id: string;
  email: string;
  full_name: string;
  role: UserRole;
  is_active: boolean;
  created_at: string;
}

export type TaskStatus =
  | 'DRAFT'
  | 'SPECIFICATION_APPROVED'
  | 'BRIEFING_SCHEDULED'
  | 'BRIEFING_COMPLETED'
  | 'IN_PROGRESS'
  | 'UNDER_REVIEW'
  | 'REVISION_REQUIRED'
  | 'PASSED'
  | 'HUMAN_REVIEW_REQUIRED'
  | 'CLOSED'
  | 'ESCALATED';

export interface AcceptanceCriterion {
  id?: string;
  criterion_code: string;
  description: string;
  verification_method: 'DETERMINISTIC_TEST' | 'ARTIFACT_INSPECTION' | 'AI_JUDGMENT' | 'HUMAN_AUDIT';
  pass_threshold: string;
  is_mandatory: boolean;
}

export interface Requirement {
  id?: string;
  req_code: string;
  title: string;
  description: string;
  priority: 'LOW' | 'MEDIUM' | 'HIGH' | 'CRITICAL';
  is_mandatory: boolean;
  acceptance_criteria: AcceptanceCriterion[];
}

export interface RubricItem {
  id?: string;
  criterion_code?: string;
  name: string;
  description: string;
  weight: number;
  max_score: number;
  evaluation_guide?: string;
}

export interface TaskVersion {
  id: string;
  version_number: number;
  objective: string;
  scope?: string;
  prerequisites?: string;
  deliverables: string;
  submission_method?: string;
  deadline_utc?: string;
  timezone: string;
  review_schedule_notes?: string;
  is_current: boolean;
  requirements: Requirement[];
  rubric_items: RubricItem[];
  created_at: string;
}

export interface TaskDocument {
  id: string;
  original_filename: string;
  file_type: string;
  file_size_bytes: number;
  has_detected_injection: boolean;
  created_at: string;
}

export interface TranscriptItem {
  id: string;
  speaker_label: string;
  spoken_text: string;
  confidence?: number;
  timestamp_offset_sec: number;
  created_at?: string;
}

export interface RecordingItem {
  id: string;
  file_path: string;
  duration_seconds: number;
  format: string;
  consent_confirmed: boolean;
}

export interface Meeting {
  id: string;
  task_id: string;
  meeting_type: 'BRIEFING' | 'REVIEW';
  scheduled_start_utc: string;
  scheduled_end_utc: string;
  timezone: string;
  google_meet_url?: string;
  google_event_id?: string;
  status: 'SCHEDULED' | 'JOINING' | 'IN_PROGRESS' | 'COMPLETED' | 'CANCELLED' | 'BOT_FAILED';
  is_recorded: boolean;
  consent_obtained: boolean;
  created_at: string;
  transcripts?: TranscriptItem[];
  recordings?: RecordingItem[];
}

export interface EvaluationResult {
  id: string;
  criterion_id?: string;
  status: 'PASS' | 'FAIL' | 'UNCERTAIN' | 'WAIVED';
  score: number;
  observed_evidence?: string;
  artifact_reference?: string;
  transcript_excerpt?: string;
  confidence_score: number;
  evaluator_type: 'DETERMINISTIC' | 'LOCAL_LLM' | 'HUMAN';
  justification?: string;
}

export interface RevisionRequest {
  id: string;
  requirement_id?: string;
  observed_failure: string;
  evidence?: string;
  expected_result: string;
  recommended_fix: string;
  new_deadline_utc?: string;
  is_resolved: boolean;
}

export interface Question {
  id: string;
  speaker: string;
  question_text: string;
  answer_text?: string;
  is_answered: boolean;
  flagged_for_assigner: boolean;
}

export interface ReviewRound {
  id: string;
  submission_id?: string;
  round_number: number;
  status: 'PENDING' | 'IN_EVALUATION' | 'EVALUATED' | 'ESCALATED';
  outcome?: 'PASS' | 'REVISION_REQUIRED' | 'HUMAN_REVIEW_REQUIRED' | 'FAIL';
  total_score?: number;
  summary?: string;
  evaluation_results: EvaluationResult[];
  revision_requests: RevisionRequest[];
  questions: Question[];
  created_at: string;
}

export interface Submission {
  id: string;
  task_id: string;
  intern_id: string;
  repository_url: string;
  commit_hash?: string;
  notes?: string;
  review_rounds: ReviewRound[];
  created_at: string;
}

export interface Task {
  id: string;
  title: string;
  status: TaskStatus;
  assigner_id: string;
  intern_id?: string;
  current_version_id?: string;
  versions?: TaskVersion[];
  documents?: TaskDocument[];
  meetings?: Meeting[];
  submissions?: Submission[];
  created_at: string;
}

export interface TaskSpecificationDraft {
  objective: string;
  scope: string;
  prerequisites: string;
  deliverables: string;
  submission_method: string;
  deadline_iso: string;
  timezone: string;
  review_schedule_notes: string;
  requirements: Requirement[];
  rubric: RubricItem[];
  detected_contradictions: string[];
  missing_information_warnings: string[];
}

export interface AuditLog {
  id: string;
  actor_id?: string;
  actor_email: string;
  action: string;
  resource_type: string;
  resource_id?: string;
  details_json?: string;
  ip_address?: string;
  created_at: string;
}

export interface ModelBenchmark {
  id: string;
  model_name: string;
  quantization: string;
  hardware_target: string;
  prompt_tokens: number;
  completion_tokens: number;
  wall_clock_seconds: number;
  tokens_per_second: number;
  memory_peak_mb: number;
  rtf?: number;
  success: boolean;
  error_message?: string;
  created_at: string;
}

export interface HealthStatus {
  status: string;
  services: {
    database: string;
    ollama: string;
    speech_tts: string;
    speech_stt: string;
    storage: string;
  };
  metrics: {
    ollama_model: string;
    ram_available_mb?: number;
    platform: string;
  };
}
