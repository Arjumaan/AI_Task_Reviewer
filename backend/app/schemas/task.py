"""
Task, Versioning, Requirements, Acceptance Criteria, and Rubric Schemas.
"""
from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, Field
from backend.app.models.task import (
    TaskStatus, RequirementPriority, VerificationMethod
)
from backend.app.schemas.meeting import MeetingResponse
from backend.app.schemas.review import SubmissionResponse

class AcceptanceCriterionSchema(BaseModel):
    id: Optional[str] = None
    criterion_code: str
    description: str
    verification_method: VerificationMethod = VerificationMethod.DETERMINISTIC_TEST
    pass_threshold: str = "100% pass"
    is_mandatory: bool = True

    class Config:
        from_attributes = True

class RequirementSchema(BaseModel):
    id: Optional[str] = None
    req_code: str
    title: str
    description: str
    priority: RequirementPriority = RequirementPriority.HIGH
    is_mandatory: bool = True
    acceptance_criteria: List[AcceptanceCriterionSchema] = []

    class Config:
        from_attributes = True

class RubricItemSchema(BaseModel):
    id: Optional[str] = None
    criterion_id: Optional[str] = None
    criterion_code: Optional[str] = None
    name: str
    description: str
    weight: float = 1.0
    max_score: float = 10.0
    evaluation_guide: Optional[str] = None

    class Config:
        from_attributes = True

class TaskSpecificationDraft(BaseModel):
    title: str
    objective: str
    scope: str
    prerequisites: Optional[str] = "None specified"
    deliverables: str
    submission_method: str = "GitHub Repository with tests and documentation"
    deadline_iso: str
    display_timezone: str = "Asia/Kolkata"
    requirements: List[RequirementSchema] = []
    rubric: List[RubricItemSchema] = []
    review_schedule_summary: str
    detected_contradictions: List[str] = []
    missing_information_warnings: List[str] = []

class TaskDocumentResponse(BaseModel):
    id: str
    filename: str
    file_size_bytes: int
    mime_type: str
    file_hash_sha256: str
    created_at: datetime

    class Config:
        from_attributes = True

class TaskVersionResponse(BaseModel):
    id: str
    version_number: int
    objective: str
    scope: str
    prerequisites: Optional[str]
    deliverables: str
    submission_method: str
    deadline_utc: datetime
    display_timezone: str
    is_approved: bool
    approved_by: Optional[str]
    approved_at: Optional[datetime]
    changelog: Optional[str]
    created_at: datetime
    requirements: List[RequirementSchema] = []
    rubric_items: List[RubricItemSchema] = []

    class Config:
        from_attributes = True

class TaskResponse(BaseModel):
    id: str
    title: str
    status: TaskStatus
    assigner_id: str
    intern_id: Optional[str] = None
    current_version_id: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    documents: List[TaskDocumentResponse] = []
    versions: List[TaskVersionResponse] = []
    current_version: Optional[TaskVersionResponse] = None
    meetings: List[MeetingResponse] = []
    submissions: List[SubmissionResponse] = []

    class Config:
        from_attributes = True

class TaskUpdateRequest(BaseModel):
    title: Optional[str] = None
    intern_id: Optional[str] = None

class TaskCreateRequest(BaseModel):
    title: str = Field(..., min_length=3, max_length=255)
    intern_id: Optional[str] = None

class ApproveSpecificationRequest(BaseModel):
    deadline_iso: Optional[str] = None # Optionally adjust deadline
    changelog: Optional[str] = "Approved initial task specification draft."

class VoiceChatRequest(BaseModel):
    message: str
    session_type: Optional[str] = "BRIEFING"

class VoiceChatResponse(BaseModel):
    reply: str
    speaker: str = "AI Reviewer"
    task_title: str
    session_type: str = "BRIEFING"
    audio_base64: Optional[str] = None
    voice_name: Optional[str] = None

class SynthesizeSpeechRequest(BaseModel):
    text: str


