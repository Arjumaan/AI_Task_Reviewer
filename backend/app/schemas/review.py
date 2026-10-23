"""
Submissions, Evaluation Results, Revision Requests, and Review Round Schemas.
"""
from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, Field
from backend.app.models.review import (
    RoundStatus, EvaluationOutcome, CriterionResultStatus, EvaluatorType
)

class SubmissionCreateRequest(BaseModel):
    task_id: str
    repository_url: Optional[str] = None
    commit_hash: Optional[str] = None
    notes: Optional[str] = None

class EvaluationResultResponse(BaseModel):
    id: str
    rubric_item_id: str
    criterion_id: str
    status: CriterionResultStatus
    score: float
    observed_evidence: str
    transcript_excerpt: Optional[str]
    artifact_reference: Optional[str]
    confidence_score: float
    evaluator_type: EvaluatorType
    justification: str
    created_at: datetime

    class Config:
        from_attributes = True

class RevisionRequestResponse(BaseModel):
    id: str
    requirement_id: str
    observed_failure: str
    evidence: str
    expected_result: str
    recommended_fix: str
    new_deadline_utc: datetime
    is_resolved: bool
    created_at: datetime

    class Config:
        from_attributes = True

class QuestionResponse(BaseModel):
    id: str
    question_text: str
    expected_concept: Optional[str]
    intern_answer: Optional[str]
    is_answered: bool
    was_clarified: bool
    question_order: int

    class Config:
        from_attributes = True

class ReviewRoundResponse(BaseModel):
    id: str
    task_id: str
    round_number: int
    status: RoundStatus
    started_at: Optional[datetime]
    completed_at: Optional[datetime]
    outcome: Optional[EvaluationOutcome]
    total_score: float
    summary_notes: Optional[str]
    appeal_requested: bool
    appeal_reason: Optional[str]
    evaluation_results: List[EvaluationResultResponse] = []
    revision_requests: List[RevisionRequestResponse] = []
    questions: List[QuestionResponse] = []

    class Config:
        from_attributes = True

class SubmissionResponse(BaseModel):
    id: str
    task_id: str
    intern_id: str
    round_number: int
    repository_url: Optional[str]
    commit_hash: Optional[str]
    notes: Optional[str]
    submitted_at: datetime
    review_rounds: List[ReviewRoundResponse] = []

    class Config:
        from_attributes = True

class AppealRequest(BaseModel):
    reason: str = Field(..., min_length=10, max_length=1000)
