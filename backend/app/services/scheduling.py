"""
Scheduling Service with Asia/Kolkata Timezone Engine & Google Calendar Integration.
Supports full dry-run mode and real Google Calendar API with Google Meet conference generation.
"""
import uuid
import logging
from datetime import datetime, timezone, timedelta
from typing import Optional, Tuple, Dict, Any
from zoneinfo import ZoneInfo
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from backend.app.core.config import settings
from backend.app.models.meeting import Meeting, MeetingType, MeetingStatus

logger = logging.getLogger(__name__)

class SchedulingService:
    @staticmethod
    def parse_to_utc(iso_string: str, default_tz_str: str = "Asia/Kolkata") -> datetime:
        """Parses any date/time string, applies default timezone if naive, and returns UTC datetime."""
        try:
            cleaned = (iso_string or "").strip().replace("Z", "+00:00")
            dt = datetime.fromisoformat(cleaned)
        except Exception:
            # Fallback to 7 days ahead if ISO string was an unparsed template or invalid
            return datetime.now(timezone.utc) + timedelta(days=7)

        if dt.tzinfo is None:
            tz = ZoneInfo(default_tz_str)
            dt = dt.replace(tzinfo=tz)
        return dt.astimezone(timezone.utc)

    @staticmethod
    def format_to_local(utc_dt: datetime, tz_str: str = "Asia/Kolkata") -> str:
        """Formats a UTC datetime into a human-readable string in the target timezone."""
        tz = ZoneInfo(tz_str)
        local_dt = utc_dt.astimezone(tz)
        return local_dt.strftime("%A, %d %B %Y at %I:%M %p %Z")

    @classmethod
    async def create_meeting_event(
        cls,
        task_id: str,
        meeting_type: MeetingType,
        start_utc: datetime,
        duration_minutes: int = 30,
        display_tz: str = "Asia/Kolkata",
        attendee_emails: Optional[list] = None
    ) -> Tuple[str, str, Optional[str], bool]:
        """
        Creates meeting event.
        Returns: (google_event_id, google_meet_url, conference_id, is_dry_run)
        """
        end_utc = start_utc + timedelta(minutes=duration_minutes)
        conf_id = f"meet-{uuid.uuid4().hex[:3]}-{uuid.uuid4().hex[:4]}-{uuid.uuid4().hex[:3]}"
        
        if settings.GOOGLE_DRY_RUN or not settings.GOOGLE_CLIENT_ID:
            logger.info(
                f"[SCHEDULING DRY-RUN] Creating synthetic meeting for Task {task_id} ({meeting_type.value})",
                extra={"task_id": task_id}
            )
            # User-configured default Google Meet URL
            meet_url = getattr(settings, "DEFAULT_GOOGLE_MEET_URL", "https://meet.google.com/meet/rqp-ctfg-nri")
            conf_id = "rqp-ctfg-nri"
            event_id = f"mock-cal-event-{uuid.uuid4().hex[:12]}"
            return event_id, meet_url, conf_id, True

        # Real Google Calendar API integration
        try:
            from google.oauth2.credentials import Credentials
            from googleapiclient.discovery import build

            creds = Credentials(
                token=None,
                refresh_token=settings.GOOGLE_REFRESH_TOKEN,
                token_uri="https://oauth2.googleapis.com/token",
                client_id=settings.GOOGLE_CLIENT_ID,
                client_secret=settings.GOOGLE_CLIENT_SECRET,
                scopes=["https://www.googleapis.com/auth/calendar.events"]
            )
            service = build("calendar", "v3", credentials=creds)

            event_body = {
                "summary": f"Task Reviewer AI — {meeting_type.value.capitalize()} Meeting",
                "description": (
                    "Automated briefing/review meeting conducted by Task Reviewer AI. "
                    "Note: This session is recorded and transcribed for evaluation purposes."
                ),
                "start": {"dateTime": start_utc.isoformat()},
                "end": {"dateTime": end_utc.isoformat()},
                "conferenceData": {
                    "createRequest": {
                        "requestId": str(uuid.uuid4()),
                        "conferenceSolutionKey": {"type": "hangoutsMeet"}
                    }
                },
                "attendees": [{"email": e} for e in (attendee_emails or [])]
            }

            created_event = service.events().insert(
                calendarId="primary",
                body=event_body,
                conferenceDataVersion=1
            ).execute()

            event_id = created_event.get("id")
            meet_url = created_event.get("hangoutLink", f"https://meet.google.com/{conf_id}")
            conference_data = created_event.get("conferenceData", {})
            actual_conf_id = conference_data.get("conferenceId", conf_id)

            logger.info(f"[GOOGLE CALENDAR] Successfully created event {event_id} with Meet URL: {meet_url}")
            return event_id, meet_url, actual_conf_id, False

        except Exception as err:
            logger.error(f"[GOOGLE CALENDAR ERROR] Failed to create Google event: {err}. Falling back to dry-run details.")
            meet_url = getattr(settings, "DEFAULT_GOOGLE_MEET_URL", "https://meet.google.com/meet/rqp-ctfg-nri")
            return f"fallback-event-{uuid.uuid4().hex[:8]}", meet_url, "rqp-ctfg-nri", True
