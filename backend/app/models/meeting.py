"""
Meeting Orchestration, Attempts, Transcripts, and Recording Models.
"""
import enum
from sqlalchemy import Column, String, Text, Integer, Float, Boolean, Enum, ForeignKey, DateTime
from sqlalchemy.orm import relationship
from backend.app.core.database import Base
from backend.app.models.base import UUIDPrimaryKeyMixin, TimestampMixin

class MeetingType(str, enum.Enum):
    BRIEFING = "BRIEFING"
    REVIEW = "REVIEW"

class MeetingStatus(str, enum.Enum):
    SCHEDULED = "SCHEDULED"
    IN_PROGRESS = "IN_PROGRESS"
    COMPLETED = "COMPLETED"
    RESCHEDULED = "RESCHEDULED"
    CANCELLED = "CANCELLED"
    FAILED = "FAILED"

class JoinStatus(str, enum.Enum):
    JOINED = "JOINED"
    ADMISSION_PENDING = "ADMISSION_PENDING"
    ADMISSION_TIMEOUT = "ADMISSION_TIMEOUT"
    FAILED_TO_JOIN = "FAILED_TO_JOIN"
    DISCONNECTED = "DISCONNECTED"

class TranscriptSource(str, enum.Enum):
    CLOSED_CAPTIONS = "CLOSED_CAPTIONS"
    LOCAL_WHISPER = "LOCAL_WHISPER"
    LOCAL_VOICE_ROOM = "LOCAL_VOICE_ROOM"

class Meeting(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "meetings"

    task_id = Column(String(36), ForeignKey("tasks.id", ondelete="CASCADE"), nullable=False, index=True)
    meeting_type = Column(Enum(MeetingType), default=MeetingType.BRIEFING, nullable=False, index=True)
    status = Column(Enum(MeetingStatus), default=MeetingStatus.SCHEDULED, nullable=False, index=True)
    scheduled_start_utc = Column(DateTime(timezone=True), nullable=False)
    scheduled_end_utc = Column(DateTime(timezone=True), nullable=False)
    timezone = Column(String(64), default="Asia/Kolkata", nullable=False)
    google_event_id = Column(String(255), nullable=True)
    google_meet_url = Column(String(512), nullable=False)
    conference_id = Column(String(64), nullable=True)
    is_dry_run = Column(Boolean, default=False, nullable=False)
    cancellation_reason = Column(Text, nullable=True)
    meeting_round = Column(Integer, default=1, nullable=False)
    feedback_summary = Column(Text, nullable=True)  # AI-generated post-session feedback

    task = relationship("Task", back_populates="meetings")
    attempts = relationship("MeetingAttempt", back_populates="meeting", cascade="all, delete-orphan", lazy="selectin")
    transcripts = relationship("Transcript", back_populates="meeting", cascade="all, delete-orphan", order_by="Transcript.timestamp_offset_sec", lazy="selectin")
    recordings = relationship("Recording", back_populates="meeting", cascade="all, delete-orphan", lazy="selectin")

class MeetingAttempt(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "meeting_attempts"

    meeting_id = Column(String(36), ForeignKey("meetings.id", ondelete="CASCADE"), nullable=False, index=True)
    attempt_number = Column(Integer, default=1, nullable=False)
    join_status = Column(Enum(JoinStatus), default=JoinStatus.ADMISSION_PENDING, nullable=False)
    bot_display_name = Column(String(128), default="Subha HR", nullable=False)
    join_time_utc = Column(DateTime(timezone=True), nullable=True)
    leave_time_utc = Column(DateTime(timezone=True), nullable=True)
    failure_reason = Column(Text, nullable=True)

    meeting = relationship("Meeting", back_populates="attempts")

class Transcript(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "transcripts"

    meeting_id = Column(String(36), ForeignKey("meetings.id", ondelete="CASCADE"), nullable=False, index=True)
    speaker_label = Column(String(128), default="Participant", nullable=False)
    spoken_text = Column(Text, nullable=False)
    confidence = Column(Float, default=1.0, nullable=False)
    timestamp_offset_sec = Column(Float, default=0.0, nullable=False)
    source = Column(Enum(TranscriptSource), default=TranscriptSource.CLOSED_CAPTIONS, nullable=False)

    meeting = relationship("Meeting", back_populates="transcripts")

class Recording(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "recordings"

    meeting_id = Column(String(36), ForeignKey("meetings.id", ondelete="CASCADE"), nullable=False, index=True)
    file_path = Column(String(512), nullable=False)
    file_size_bytes = Column(Integer, default=0, nullable=False)
    duration_seconds = Column(Float, default=0.0, nullable=False)
    format = Column(String(32), default="wav", nullable=False)
    consent_confirmed = Column(Boolean, default=False, nullable=False)
    consent_recorded_at = Column(DateTime(timezone=True), nullable=True)
    retention_until = Column(DateTime(timezone=True), nullable=True)
    is_deleted = Column(Boolean, default=False, nullable=False)
    deleted_at = Column(DateTime(timezone=True), nullable=True)
    deletion_reason = Column(String(255), nullable=True)

    meeting = relationship("Meeting", back_populates="recordings")
