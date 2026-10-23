"""
Audit Logging and Model Benchmark Metrics Models.
"""
import enum
from sqlalchemy import Column, String, Text, Integer, Float, Boolean, ForeignKey, DateTime
from sqlalchemy.orm import relationship
from backend.app.core.database import Base
from backend.app.models.base import UUIDPrimaryKeyMixin, TimestampMixin, get_utc_now

class AuditLog(Base, UUIDPrimaryKeyMixin):
    __tablename__ = "audit_logs"

    actor_id = Column(String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    actor_email = Column(String(255), nullable=True)
    action = Column(String(128), nullable=False, index=True) # e.g. TASK_APPROVED, RECORDING_DELETED, EVALUATION_OVERRIDDEN
    resource_type = Column(String(64), nullable=False, index=True) # e.g. task, recording, review_round
    resource_id = Column(String(64), nullable=False, index=True)
    details_json = Column(Text, nullable=True)
    ip_address = Column(String(64), nullable=True)
    timestamp = Column(DateTime(timezone=True), default=get_utc_now, nullable=False, index=True)

    actor = relationship("User", back_populates="audit_logs")

class ModelBenchmark(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "model_benchmarks"

    model_name = Column(String(128), nullable=False)
    quantization = Column(String(64), nullable=True)
    task_type = Column(String(64), nullable=False) # LLM_INFERENCE, TTS_SYNTHESIS, STT_TRANSCRIPTION
    latency_ms = Column(Float, nullable=False)
    tokens_per_second = Column(Float, nullable=True)
    memory_mb = Column(Float, nullable=True)
    success = Column(Boolean, default=True, nullable=False)
    notes = Column(Text, nullable=True)
