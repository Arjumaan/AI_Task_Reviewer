"""
Submissions, Review Rounds, Questions, Evaluation Results, and Revision Requests.
"""
import enum
from sqlalchemy import Column, String, Text, Integer, Float, Boolean, Enum, ForeignKey, DateTime
from sqlalchemy.orm import relationship
from backend.app.core.database import Base
from backend.app.models.base import UUIDPrimaryKeyMixin, TimestampMixin

class RoundStatus(str, enum.Enum):
    PENDING = "PENDING"
    IN_REVIEW = "IN_REVIEW"
    COMPLETED = "COMPLETED"

class EvaluationOutcome(str, enum.Enum):
    PASS = "PASS"
    REVISION_REQUIRED = "REVISION_REQUIRED"
    HUMAN_REVIEW_REQUIRED = "HUMAN_REVIEW_REQUIRED"

class CriterionResultStatus(str, enum.Enum):
    PASS = "PASS"
    FAIL = "FAIL"
    UNCERTAIN = "UNCERTAIN"

class EvaluatorType(str, enum.Enum):
    DETERMINISTIC = "DETERMINISTIC"
    LOCAL_LLM = "LOCAL_LLM"
    HUMAN = "HUMAN"

class Submission(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "submissions"

    task_id = Column(String(36), ForeignKey("tasks.id", ondelete="CASCADE"), nullable=False, index=True)
    intern_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    round_number = Column(Integer, default=1, nullable=False)
    repository_url = Column(String(512), nullable=True)
    commit_hash = Column(String(64), nullable=True)
    notes = Column(Text, nullable=True)
    submission_artifact_path = Column(String(512), nullable=True)
    submitted_at = Column(DateTime(timezone=True), nullable=False)

    task = relationship("Task", back_populates="submissions")
    intern = relationship("User")
    review_rounds = relationship("ReviewRound", back_populates="submission", lazy="selectin")

class ReviewRound(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "review_rounds"

    task_id = Column(String(36), ForeignKey("tasks.id", ondelete="CASCADE"), nullable=False, index=True)
    submission_id = Column(String(36), ForeignKey("submissions.id", ondelete="SET NULL"), nullable=True)
    round_number = Column(Integer, default=1, nullable=False)
    status = Column(Enum(RoundStatus), default=RoundStatus.PENDING, nullable=False, index=True)
    started_at = Column(DateTime(timezone=True), nullable=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    outcome = Column(Enum(EvaluationOutcome), nullable=True, index=True)
    total_score = Column(Float, default=0.0, nullable=False)
    summary_notes = Column(Text, nullable=True)
    appeal_requested = Column(Boolean, default=False, nullable=False)
    appeal_reason = Column(Text, nullable=True)

    task = relationship("Task", back_populates="review_rounds")
    submission = relationship("Submission", back_populates="review_rounds")
    questions = relationship("Question", back_populates="review_round", cascade="all, delete-orphan", lazy="selectin")
    evaluation_results = relationship("EvaluationResult", back_populates="review_round", cascade="all, delete-orphan", lazy="selectin")
    revision_requests = relationship("RevisionRequest", back_populates="review_round", cascade="all, delete-orphan", lazy="selectin")

class Question(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "questions"

    review_round_id = Column(String(36), ForeignKey("review_rounds.id", ondelete="CASCADE"), nullable=False, index=True)
    question_text = Column(Text, nullable=False)
    expected_concept = Column(Text, nullable=True)
    intern_answer = Column(Text, nullable=True)
    is_answered = Column(Boolean, default=False, nullable=False)
    was_clarified = Column(Boolean, default=False, nullable=False)
    question_order = Column(Integer, default=1, nullable=False)

    review_round = relationship("ReviewRound", back_populates="questions")

class EvaluationResult(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "evaluation_results"

    review_round_id = Column(String(36), ForeignKey("review_rounds.id", ondelete="CASCADE"), nullable=False, index=True)
    rubric_item_id = Column(String(36), ForeignKey("rubric_items.id", ondelete="CASCADE"), nullable=False, index=True)
    criterion_id = Column(String(36), ForeignKey("acceptance_criteria.id", ondelete="CASCADE"), nullable=False, index=True)
    status = Column(Enum(CriterionResultStatus), nullable=False)
    score = Column(Float, default=0.0, nullable=False)
    observed_evidence = Column(Text, nullable=False)
    transcript_excerpt = Column(Text, nullable=True)
    artifact_reference = Column(String(512), nullable=True)
    confidence_score = Column(Float, default=1.0, nullable=False)
    evaluator_type = Column(Enum(EvaluatorType), default=EvaluatorType.LOCAL_LLM, nullable=False)
    justification = Column(Text, nullable=False)

    review_round = relationship("ReviewRound", back_populates="evaluation_results")
    rubric_item = relationship("RubricItem")
    criterion = relationship("AcceptanceCriterion")

class RevisionRequest(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "revision_requests"

    review_round_id = Column(String(36), ForeignKey("review_rounds.id", ondelete="CASCADE"), nullable=False, index=True)
    requirement_id = Column(String(36), ForeignKey("requirements.id", ondelete="CASCADE"), nullable=False, index=True)
    observed_failure = Column(Text, nullable=False)
    evidence = Column(Text, nullable=False)
    expected_result = Column(Text, nullable=False)
    recommended_fix = Column(Text, nullable=False)
    new_deadline_utc = Column(DateTime(timezone=True), nullable=False)
    is_resolved = Column(Boolean, default=False, nullable=False)

    review_round = relationship("ReviewRound", back_populates="revision_requests")
    requirement = relationship("Requirement")
