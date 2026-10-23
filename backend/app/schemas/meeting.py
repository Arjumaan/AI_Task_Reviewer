"""
Meeting, Attendance, Transcripts, and Recording Schemas.
"""
from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, Field
from backend.app.models.meeting import (
    MeetingType, MeetingStatus, JoinStatus, TranscriptSource
)

class ScheduleMeetingRequest(BaseModel):
    task_id: str
    meeting_type: MeetingType = MeetingType.BRIEFING
    start_time_iso: str = Field(..., example="2026-10-25T10:00:00+05:30")
    duration_minutes: int = Field(30, ge=10, le=120)
    timezone: str = "Asia/Kolkata"
    custom_meet_url: Optional[str] = None

class RescheduleMeetingRequest(BaseModel):
    new_start_time_iso: str
    duration_minutes: int = 30
    reason: str = Field(..., min_length=5)

class TranscriptResponse(BaseModel):
    id: str
    speaker_label: str
    spoken_text: str
    confidence: float
    timestamp_offset_sec: float
    source: TranscriptSource
    created_at: datetime

    class Config:
        from_attributes = True

class RecordingResponse(BaseModel):
    id: str
    meeting_id: str
    file_path: Optional[str] = None
    file_size_bytes: int
    duration_seconds: float
    format: str
    consent_confirmed: bool
    consent_recorded_at: Optional[datetime]
    retention_until: Optional[datetime]
    is_deleted: bool
    created_at: datetime

    class Config:
        from_attributes = True

class MeetingAttemptResponse(BaseModel):
    id: str
    attempt_number: int
    join_status: JoinStatus
    bot_display_name: str
    join_time_utc: Optional[datetime]
    leave_time_utc: Optional[datetime]
    failure_reason: Optional[str]
    created_at: datetime

    class Config:
        from_attributes = True

class MeetingResponse(BaseModel):
    id: str
    task_id: str
    meeting_type: MeetingType
    status: MeetingStatus
    scheduled_start_utc: datetime
    scheduled_end_utc: datetime
    timezone: str
    google_event_id: Optional[str]
    google_meet_url: str
    conference_id: Optional[str]
    is_dry_run: bool
    created_at: datetime
    attempts: List[MeetingAttemptResponse] = []
    transcripts: List[TranscriptResponse] = []
    recordings: List[RecordingResponse] = []

    class Config:
        from_attributes = True
