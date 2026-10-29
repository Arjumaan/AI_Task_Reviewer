"""
Task, Versioning, Document Ingestion, Requirements, Acceptance Criteria, and Rubrics.
"""
import enum
from sqlalchemy import Column, String, Text, Integer, Float, Boolean, Enum, ForeignKey, DateTime
from sqlalchemy.orm import relationship
from backend.app.core.database import Base
from backend.app.models.base import UUIDPrimaryKeyMixin, TimestampMixin

class TaskStatus(str, enum.Enum):
    DRAFT = "DRAFT"
    SPECIFICATION_APPROVED = "SPECIFICATION_APPROVED"
    BRIEFING_SCHEDULED = "BRIEFING_SCHEDULED"
    BRIEFING_COMPLETED = "BRIEFING_COMPLETED"
    IN_PROGRESS = "IN_PROGRESS"
    UNDER_REVIEW = "UNDER_REVIEW"
    REVISION_REQUIRED = "REVISION_REQUIRED"
    PASSED = "PASSED"
    HUMAN_REVIEW_REQUIRED = "HUMAN_REVIEW_REQUIRED"
    CLOSED = "CLOSED"
    SUBMITTED = "SUBMITTED"
    REVIEW_SCHEDULED = "REVIEW_SCHEDULED"
    ESCALATED = "ESCALATED"

class RequirementPriority(str, enum.Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"

class VerificationMethod(str, enum.Enum):
    DETERMINISTIC_TEST = "DETERMINISTIC_TEST"
    ARTIFACT_INSPECTION = "ARTIFACT_INSPECTION"
    AI_JUDGMENT = "AI_JUDGMENT"
    HUMAN_AUDIT = "HUMAN_AUDIT"

class Task(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "tasks"

    title = Column(String(255), nullable=False)
    status = Column(Enum(TaskStatus), default=TaskStatus.DRAFT, nullable=False, index=True)
    assigner_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    intern_id = Column(String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    current_version_id = Column(String(36), nullable=True)

    # Relationships
    assigner = relationship("User", back_populates="assigned_tasks", foreign_keys=[assigner_id])
    intern = relationship("User", back_populates="intern_tasks", foreign_keys=[intern_id])
    versions = relationship("TaskVersion", back_populates="task", cascade="all, delete-orphan", order_by="TaskVersion.version_number", lazy="selectin")
    documents = relationship("TaskDocument", back_populates="task", cascade="all, delete-orphan", lazy="selectin")
    meetings = relationship("Meeting", back_populates="task", cascade="all, delete-orphan", lazy="selectin")
    submissions = relationship("Submission", back_populates="task", cascade="all, delete-orphan", lazy="selectin")
    review_rounds = relationship("ReviewRound", back_populates="task", cascade="all, delete-orphan", lazy="selectin")

class TaskVersion(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "task_versions"

    task_id = Column(String(36), ForeignKey("tasks.id", ondelete="CASCADE"), nullable=False, index=True)
    version_number = Column(Integer, default=1, nullable=False)
    objective = Column(Text, nullable=False)
    scope = Column(Text, nullable=False)
    prerequisites = Column(Text, nullable=True)
    deliverables = Column(Text, nullable=False)
    submission_method = Column(String(255), default="GitHub Repository & Test Reports", nullable=False)
    deadline_utc = Column(DateTime(timezone=True), nullable=False)
    display_timezone = Column(String(64), default="Asia/Kolkata", nullable=False)
    is_approved = Column(Boolean, default=False, nullable=False)
    approved_by = Column(String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    approved_at = Column(DateTime(timezone=True), nullable=True)
    changelog = Column(Text, nullable=True)

    # Relationships
    task = relationship("Task", back_populates="versions")
    requirements = relationship("Requirement", back_populates="task_version", cascade="all, delete-orphan", lazy="selectin")
    rubric_items = relationship("RubricItem", back_populates="task_version", cascade="all, delete-orphan", lazy="selectin")

class TaskDocument(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "task_documents"

    task_id = Column(String(36), ForeignKey("tasks.id", ondelete="CASCADE"), nullable=False, index=True)
    filename = Column(String(255), nullable=False)
    file_path = Column(String(512), nullable=False)
    file_size_bytes = Column(Integer, nullable=False)
    mime_type = Column(String(128), nullable=False)
    file_hash_sha256 = Column(String(64), nullable=False)
    extracted_raw_text = Column(Text, nullable=False)
    extraction_warnings = Column(Text, nullable=True)
    analysis_json = Column(Text, nullable=True)

    task = relationship("Task", back_populates="documents")

class Requirement(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "requirements"

    task_version_id = Column(String(36), ForeignKey("task_versions.id", ondelete="CASCADE"), nullable=False, index=True)
    req_code = Column(String(32), nullable=False) # e.g. REQ-01
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=False)
    is_mandatory = Column(Boolean, default=True, nullable=False)
    priority = Column(Enum(RequirementPriority), default=RequirementPriority.HIGH, nullable=False)

    task_version = relationship("TaskVersion", back_populates="requirements")
    acceptance_criteria = relationship("AcceptanceCriterion", back_populates="requirement", cascade="all, delete-orphan", lazy="selectin")

class AcceptanceCriterion(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "acceptance_criteria"

    requirement_id = Column(String(36), ForeignKey("requirements.id", ondelete="CASCADE"), nullable=False, index=True)
    criterion_code = Column(String(32), nullable=False) # e.g. AC-01.1
    description = Column(Text, nullable=False)
    verification_method = Column(Enum(VerificationMethod), default=VerificationMethod.DETERMINISTIC_TEST, nullable=False)
    pass_threshold = Column(String(128), default="100% pass", nullable=False)
    is_mandatory = Column(Boolean, default=True, nullable=False)

    requirement = relationship("Requirement", back_populates="acceptance_criteria")
    rubric_item = relationship("RubricItem", back_populates="criterion", uselist=False)

class RubricItem(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "rubric_items"

    task_version_id = Column(String(36), ForeignKey("task_versions.id", ondelete="CASCADE"), nullable=False, index=True)
    criterion_id = Column(String(36), ForeignKey("acceptance_criteria.id", ondelete="CASCADE"), nullable=False, unique=True)
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=False)
    weight = Column(Float, default=1.0, nullable=False)
    max_score = Column(Float, default=10.0, nullable=False)
    evaluation_guide = Column(Text, nullable=True)

    task_version = relationship("TaskVersion", back_populates="rubric_items")
    criterion = relationship("AcceptanceCriterion", back_populates="rubric_item")
