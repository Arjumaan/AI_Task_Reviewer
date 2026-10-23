"""
MeetingBaas Cloud Meeting Bot Service.
Integrates with api.meetingbaas.com for autonomous bot deployment, recording,
speaker-diarized transcription, and lifecycle synchronization with the review engine.
"""
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone
import httpx
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from backend.app.core.config import settings
from backend.app.models.meeting import (
    Meeting, MeetingStatus, MeetingAttempt, JoinStatus,
    Transcript, TranscriptSource, Recording
)

logger = logging.getLogger(__name__)

class MeetingBaasService:
    @classmethod
    def _get_headers(cls) -> Dict[str, str]:
        return {
            "x-meeting-baas-api-key": settings.MEETING_BAAS_API_KEY,
            "Content-Type": "application/json"
        }

    @classmethod
    def normalize_meet_url(cls, url_or_code: str) -> str:
        """Converts raw code (e.g. 'ktj-kjkj-xwk') into full valid Google Meet URL."""
        cleaned = url_or_code.strip()
        if not cleaned:
            return ""
        if cleaned.startswith("http://") or cleaned.startswith("https://"):
            return cleaned
        # If bare code like abc-defg-hij
        return f"https://meet.google.com/{cleaned}"

    @classmethod
    async def deploy_bot(
        cls,
        meeting_url: str,
        bot_name: str = "AI Task Reviewer",
        entry_message: Optional[str] = None,
        prompt: Optional[str] = None,
        is_speaking: bool = True,
        webhook_url: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Deploys an autonomous MeetingBaas bot into a Google Meet / Zoom / Teams call.
        Supports both Interactive Speaking Bots (via Pipecat Voice AI) and Silent Recording Bots.
        """
        full_url = cls.normalize_meet_url(meeting_url)
        headers = cls._get_headers()

        if is_speaking:
            url = f"{settings.MEETING_BAAS_SPEAKING_URL}/bots"
            default_entry = (
                "Hi everyone! I am Subha, your AI Reviewer. I'm ready to answer any questions about the task and rubric. What would you like to know?"
            )
            default_prompt = (
                "You are Subha, an AI Task Reviewer participating in this live Google Meet call with an intern and assigner. "
                "You have a natural, conversational Indian English accent. "
                "STRICT CONVERSATIONAL RULES (MUST FOLLOW): "
                "1. DO NOT recite, summarize, or read the task specifications or rubric on entry. "
                "2. When joining, give at most a 1-sentence greeting, then immediately STOP and WAIT for a participant to speak. "
                "3. Keep all answers under 2 short sentences (maximum 25 words). "
                "4. Immediately stop talking after answering so participants can speak. "
                "5. Never monologue or list multiple points at once. Answer directly and concisely."
            )
            payload: Dict[str, Any] = {
                "meeting_url": full_url,
                "bot_name": bot_name or "AI Task Reviewer (Subha)",
                "entry_message": entry_message or default_entry,
                "prompt": prompt or default_prompt,
                "personas": ["helpful_assistant"],
                "credentials": {
                    "tts_api_key": settings.CARTESIA_API_KEY
                } if settings.CARTESIA_API_KEY else None,
                "extra": {
                    "cartesia_voice_id": settings.CARTESIA_VOICE_ID,
                    "voice_id": settings.CARTESIA_VOICE_ID,
                    "cartesia_model_id": settings.CARTESIA_MODEL_ID or "sonic-3.6"
                } if settings.CARTESIA_VOICE_ID else None,
                "turn_config": {
                    "confidence": 0.30,      # High sensitivity so user voice is detected
                    "start_secs": 0.10,      # Instant speech detection (0.10s)
                    "stop_secs": 0.50,       # Fast handoff: 0.5s pause allows natural conversation flow
                    "min_volume": 0.04       # Low threshold so quiet microphones trigger turn-taking
                },
                "speech_speed": 1.05,
                "llm_provider": "openai",
                "enable_tools": False,       # Disable weather/time tools so LLM outputs direct speech
                "transcription_enabled": True,
                "transcription_provider": "gladia"
            }
            # Strip out None values
            payload = {k: v for k, v in payload.items() if v is not None}
        else:
            url = f"{settings.MEETING_BAAS_BASE_URL}/bots"
            default_entry = (
                "Hello! I am the AI Task Reviewer bot. This session is recorded and transcribed "
                "for objective evaluation against task rubric criteria."
            )
            payload = {
                "meeting_url": full_url,
                "bot_name": bot_name or "AI Task Reviewer",
                "entry_message": entry_message or default_entry,
                "recording_mode": "speaker_view",
                "speech_to_text": "gladia"
            }
        target_webhook = webhook_url or settings.MEETING_BAAS_WEBHOOK_URL
        if target_webhook:
            payload["webhook_url"] = target_webhook

        async with httpx.AsyncClient(timeout=25.0) as client:
            res = await client.post(url, json=payload, headers=headers)
            if res.status_code in [200, 201]:
                data = res.json()
                bot_info = data.get("data", data)
                return {
                    "success": True,
                    "bot_id": bot_info.get("bot_id"),
                    "status": bot_info.get("status", "joining"),
                    "is_speaking": is_speaking,
                    "meeting_url": full_url,
                    "data": bot_info
                }
            else:
                logger.error(f"[MEETINGBAAS ERROR] Failed to deploy bot: {res.status_code} - {res.text}")
                return {
                    "success": False,
                    "status_code": res.status_code,
                    "error": res.text
                }

    @classmethod
    async def get_bot(cls, bot_id: str) -> Dict[str, Any]:
        """Retrieves live bot state, duration, recording URL, and diarized transcript."""
        url = f"{settings.MEETING_BAAS_BASE_URL}/bots/{bot_id}"
        headers = cls._get_headers()

        async with httpx.AsyncClient(timeout=15.0) as client:
            res = await client.get(url, headers=headers)
            if res.status_code == 200:
                data = res.json()
                return {"success": True, "data": data.get("data", data)}
            else:
                return {"success": False, "status_code": res.status_code, "error": res.text}

    @classmethod
    async def list_bots(cls) -> List[Dict[str, Any]]:
        """Lists active and recent bots under this account."""
        url = f"{settings.MEETING_BAAS_BASE_URL}/bots"
        headers = cls._get_headers()

        async with httpx.AsyncClient(timeout=15.0) as client:
            res = await client.get(url, headers=headers)
            if res.status_code == 200:
                data = res.json()
                return data.get("data", [])
            return []

    @classmethod
    async def leave_meeting(cls, bot_id: str) -> Dict[str, Any]:
        """Commands the bot to leave the meeting and initiate artifact processing."""
        headers = cls._get_headers()

        # 1. Attempt speaking bot dismissal
        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                res = await client.request(
                    "DELETE",
                    f"{settings.MEETING_BAAS_SPEAKING_URL}/bots/{bot_id}",
                    json={"bot_id": bot_id},
                    headers=headers
                )
                if res.status_code in [200, 204]:
                    return {"success": True, "message": "Speaking bot dismissed from meeting successfully."}
        except Exception as e:
            logger.warning(f"Speaking bot leave attempt failed for {bot_id}: {e}")

        # 2. Fallback to v2 API delete
        url = f"{settings.MEETING_BAAS_BASE_URL}/bots/{bot_id}"
        async with httpx.AsyncClient(timeout=15.0) as client:
            res = await client.delete(url, headers=headers)
            if res.status_code in [200, 204]:
                return {"success": True, "message": "Bot dismissed from meeting successfully."}
            else:
                return {"success": False, "status_code": res.status_code, "error": res.text}

    @classmethod
    async def sync_transcripts_to_db(
        cls,
        meeting_id: str,
        bot_id: str,
        db: AsyncSession
    ) -> Dict[str, Any]:
        """
        Synchronizes MeetingBaas speaker-diarized transcript and video recording into our database.
        """
        bot_res = await cls.get_bot(bot_id)
        if not bot_res.get("success"):
            return {"success": False, "error": bot_res.get("error")}

        bot_data = bot_res.get("data", {})
        status = bot_data.get("status", "unknown")
        video_url = bot_data.get("video")
        duration = bot_data.get("duration_seconds") or 0.0

        # Fetch meeting
        res = await db.execute(select(Meeting).where(Meeting.id == meeting_id))
        meeting = res.scalars().first()
        if not meeting:
            return {"success": False, "error": "Meeting not found in database"}

        # Ingest Transcripts
        transcript_entries: List[Dict[str, Any]] = []
        raw_transcription = bot_data.get("transcription") or bot_data.get("raw_transcription")

        if isinstance(raw_transcription, list):
            for seg in raw_transcription:
                speaker = seg.get("speaker") or "Participant"
                text = seg.get("text") or seg.get("words") or ""
                offset = seg.get("start_time") or seg.get("start") or 0.0
                if text.strip():
                    transcript_entries.append({
                        "speaker": speaker,
                        "text": text.strip(),
                        "offset": float(offset)
                    })
        elif isinstance(raw_transcription, dict) and "segments" in raw_transcription:
            for seg in raw_transcription.get("segments", []):
                speaker = seg.get("speaker") or "Participant"
                text = seg.get("text") or ""
                offset = seg.get("start") or 0.0
                if text.strip():
                    transcript_entries.append({
                        "speaker": speaker,
                        "text": text.strip(),
                        "offset": float(offset)
                    })

        # Save to Transcript table if not already populated
        inserted_count = 0
        if transcript_entries:
            # Check existing transcripts count
            ex_res = await db.execute(select(Transcript).where(Transcript.meeting_id == meeting.id))
            existing_transcripts = ex_res.scalars().all()

            if len(existing_transcripts) < len(transcript_entries):
                # Clear previous partial transcripts and insert clean diarized transcript
                for ex in existing_transcripts:
                    await db.delete(ex)

                for item in transcript_entries:
                    t = Transcript(
                        meeting_id=meeting.id,
                        speaker_label=item["speaker"],
                        spoken_text=item["text"],
                        timestamp_offset_sec=item["offset"],
                        source=TranscriptSource.CLOSED_CAPTIONS
                    )
                    db.add(t)
                    inserted_count += 1

        # Save Recording URL
        if video_url:
            rec_res = await db.execute(select(Recording).where(Recording.meeting_id == meeting.id))
            rec = rec_res.scalars().first()
            if not rec:
                rec = Recording(
                    meeting_id=meeting.id,
                    file_path=video_url,
                    duration_seconds=float(duration),
                    format="mp4",
                    consent_confirmed=True,
                    consent_recorded_at=datetime.now(timezone.utc)
                )
                db.add(rec)
            else:
                rec.file_path = video_url
                rec.duration_seconds = float(duration)

        # Update meeting status if completed or ended
        if status in ["completed", "ended", "call_ended", "processed"]:
            meeting.status = MeetingStatus.COMPLETED

        await db.commit()

        return {
            "success": True,
            "meeting_id": meeting.id,
            "bot_status": status,
            "transcripts_synced": inserted_count,
            "video_url": video_url,
            "duration_seconds": duration
        }
