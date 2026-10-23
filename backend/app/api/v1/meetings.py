"""
Meeting Execution, Bot Orchestration, Transcripts, and Briefing Closeout.
"""
from datetime import datetime, timezone
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Request
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from backend.app.core.database import get_db
from backend.app.core.config import settings
from backend.app.models.user import User, UserRole
from backend.app.models.task import Task, TaskStatus, TaskVersion
from backend.app.models.meeting import (
    Meeting, MeetingAttempt, Transcript, Recording,
    MeetingType, MeetingStatus, JoinStatus, TranscriptSource
)
from backend.app.models.audit import AuditLog
from backend.app.schemas.meeting import (
    MeetingResponse, MeetingAttemptResponse, TranscriptResponse
)
import subprocess
import os
import sys
from backend.app.services.email_service import EmailService
from backend.app.services.scheduling import SchedulingService
from backend.app.services.meeting_baas import MeetingBaasService
from backend.app.api.deps import get_current_user

router = APIRouter(prefix="/meetings", tags=["Meetings"])

# Track active bot state in memory (Supports MeetingBaas cloud bots and local fallbacks)
active_bot_state = {
    "process": None,
    "pid": None,
    "meet_url": None,
    "started_at": None,
    "meeting_id": None,
    "bot_id": None,
    "status": None,
    "is_speaking": True
}

class DirectBotLaunchRequest(BaseModel):
    meet_url: str
    is_speaking: bool = True
    bot_name: Optional[str] = "AI Task Reviewer"
    prompt: Optional[str] = None
    entry_message: Optional[str] = None

class LaunchBotRequest(BaseModel):
    is_speaking: bool = True
    bot_name: Optional[str] = "AI Task Reviewer"
    custom_prompt: Optional[str] = None
    custom_entry_message: Optional[str] = None

class AddTranscriptRequest(BaseModel):
    speaker_label: str
    spoken_text: str
    confidence: float = 1.0
    timestamp_offset_sec: float = 0.0
    source: TranscriptSource = TranscriptSource.CLOSED_CAPTIONS

class ConsentRequest(BaseModel):
    consent_confirmed: bool

@router.get("/google-auth-status")
async def get_google_auth_status(current_user: User = Depends(get_current_user)):
    """Checks if the bot's persistent Chrome profile has Google authentication session cookies."""
    import sqlite3
    cookies_path = os.path.abspath("storage/bot_browser_profile/Default/Network/Cookies")
    authenticated = False
    if os.path.exists(cookies_path):
        try:
            conn = sqlite3.connect(f"file:{cookies_path}?mode=ro", uri=True)
            cur = conn.cursor()
            cur.execute("SELECT 1 FROM cookies WHERE name IN ('SID', 'SSID') AND host_key LIKE '%google.com%' LIMIT 1")
            row = cur.fetchone()
            if row:
                authenticated = True
            conn.close()
        except Exception:
            pass

    return {"authenticated": authenticated}

@router.post("/launch-google-login")
async def launch_google_login(current_user: User = Depends(get_current_user)):
    """Opens Chrome directly to Google Sign-In so the user can authenticate the bot. Only for Admin and Assigner."""
    if current_user.role == UserRole.INTERN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Forbidden: Intern accounts cannot configure bot Google authentication."
        )
    cmd = [sys.executable, "poc/meet_bot.py", "--login"]
    p = subprocess.Popen(cmd, cwd=os.getcwd())
    return {
        "status": "launched",
        "pid": p.pid,
        "message": "Chrome opened to Google Sign-In. Complete login in the Chrome window to authenticate the AI Bot."
    }

@router.get("/bot-status")
async def get_bot_status(current_user: User = Depends(get_current_user)):
    bot_id = active_bot_state.get("bot_id")
    status_str = active_bot_state.get("status")
    duration = None
    has_video = False
    has_transcription = False

    # 1. Check MeetingBaas Cloud Bot
    if bot_id:
        baas_res = await MeetingBaasService.get_bot(bot_id)
        if baas_res.get("success"):
            data = baas_res.get("data", {})
            status_str = data.get("status", status_str)
            active_bot_state["status"] = status_str
            duration = data.get("duration_seconds")
            has_video = bool(data.get("video"))
            has_transcription = bool(data.get("transcription") or data.get("raw_transcription"))
    else:
        # Check if an active bot exists under the account
        try:
            active_bots = await MeetingBaasService.list_bots()
            recording_bots = [b for b in active_bots if b.get("status") in ["in_call_recording", "joining", "in_waiting_room"]]
            if recording_bots:
                adopted = recording_bots[0]
                active_bot_state["bot_id"] = adopted.get("bot_id")
                active_bot_state["status"] = adopted.get("status")
                active_bot_state["meet_url"] = adopted.get("meeting_url")
                active_bot_state["started_at"] = adopted.get("created_at")
                bot_id = adopted.get("bot_id")
                status_str = adopted.get("status")
        except Exception:
            pass

    is_running = status_str in ["in_call_recording", "joining", "in_waiting_room", "in_call_not_recording"]

    # Fallback check local process if not running on BaaS
    if not is_running:
        proc = active_bot_state.get("process")
        if proc is not None and proc.poll() is None:
            is_running = True
            status_str = "local_process_active"

    return {
        "is_running": is_running,
        "bot_id": bot_id,
        "status": status_str or ("idle" if not is_running else "active"),
        "is_speaking": active_bot_state.get("is_speaking", True),
        "meet_url": active_bot_state.get("meet_url"),
        "meeting_id": active_bot_state.get("meeting_id"),
        "duration_seconds": duration,
        "has_video": has_video,
        "has_transcription": has_transcription,
        "pid": active_bot_state.get("pid") if active_bot_state.get("process") else None
    }

@router.post("/baas-webhook")
async def meetingbaas_webhook(
    request: Request,
    db: AsyncSession = Depends(get_db)
):
    """
    Receives real-time asynchronous webhook updates from Meeting BaaS:
    - bot.status_change (joining, in_waiting_room, in_call_recording, call_ended)
    - complete (recording ready, full transcription available)
    - error / failed
    """
    try:
        payload = await request.json()
    except Exception:
        return {"status": "ignored", "reason": "invalid_json"}

    event_type = payload.get("event") or payload.get("type") or "unknown"
    data = payload.get("data") or payload
    bot_id = data.get("bot_id") or payload.get("bot_id")

    # Update active bot state in memory
    if bot_id and (active_bot_state.get("bot_id") == bot_id or not active_bot_state.get("bot_id")):
        raw_status = data.get("status")
        status_code = raw_status.get("code") if isinstance(raw_status, dict) else raw_status
        if status_code:
            active_bot_state["status"] = status_code

    # If meeting completed or transcript ready, auto-sync transcripts & recordings into DB
    meeting_id = active_bot_state.get("meeting_id")
    if bot_id and ("complete" in str(event_type) or "completed" in str(data.get("status", ""))):
        if not meeting_id:
            m_res = await db.execute(
                select(MeetingAttempt).where(MeetingAttempt.bot_display_name.like(f"%{bot_id}%"))
            )
            attempt = m_res.scalars().first()
            if attempt:
                meeting_id = attempt.meeting_id

        if meeting_id:
            try:
                await MeetingBaasService.sync_transcripts_to_db(meeting_id, bot_id, db)
            except Exception as e:
                pass

    return {"status": "success", "event": event_type, "bot_id": bot_id}

@router.post("/stop-bot")
async def stop_meet_bot(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    bot_id = active_bot_state.get("bot_id")
    meeting_id = active_bot_state.get("meeting_id")

    # 1. Stop MeetingBaas Bot if active
    if bot_id:
        baas_res = await MeetingBaasService.leave_meeting(bot_id)
        if meeting_id:
            try:
                await MeetingBaasService.sync_transcripts_to_db(meeting_id, bot_id, db)
            except Exception as e:
                logger.warning(f"Auto-sync on stop failed: {e}")
        
        active_bot_state["status"] = "completed"
        return {
            "status": "stopped",
            "bot_id": bot_id,
            "message": "MeetingBaas AI Bot dismissed from meeting. Transcripts and recordings are finalizing."
        }

    # 2. Fallback stop local process
    proc = active_bot_state.get("process")
    if proc is not None and proc.poll() is None:
        try:
            proc.terminate()
            proc.wait(timeout=3)
        except Exception:
            try:
                proc.kill()
            except Exception:
                pass
        active_bot_state["process"] = None
        active_bot_state["pid"] = None
        return {"status": "stopped", "message": "Bot process terminated successfully."}
    return {"status": "not_running", "message": "No active bot process was running."}

@router.post("/launch-direct")
async def launch_direct_bot(
    req: DirectBotLaunchRequest,
    current_user: User = Depends(get_current_user)
):
    meet_url = req.meet_url.strip()
    if not meet_url:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Meeting URL or code is required")
        
    # Deploy via MeetingBaas Cloud Bot (Speaking mode or Silent recording mode)
    deploy_res = await MeetingBaasService.deploy_bot(
        meeting_url=meet_url,
        bot_name=req.bot_name or "AI Task Reviewer",
        entry_message=req.entry_message,
        prompt=req.prompt,
        is_speaking=req.is_speaking
    )

    if deploy_res.get("success"):
        bot_id = deploy_res.get("bot_id")
        active_bot_state["bot_id"] = bot_id
        active_bot_state["status"] = deploy_res.get("status", "joining")
        active_bot_state["meet_url"] = deploy_res.get("meeting_url")
        active_bot_state["started_at"] = datetime.now(timezone.utc).isoformat()
        active_bot_state["meeting_id"] = None
        active_bot_state["is_speaking"] = req.is_speaking

        mode_desc = "Interactive Speaking Mode (Unmuted Voice AI)" if req.is_speaking else "Silent Recording Mode"
        return {
            "status": "launched",
            "bot_id": bot_id,
            "is_speaking": req.is_speaking,
            "meet_url": deploy_res.get("meeting_url"),
            "message": f"AI Bot dispatched via MeetingBaas in {mode_desc}! It will enter {meet_url} directly or knock for admission."
        }
    else:
        # Fallback to local subprocess
        os.makedirs("storage/logs", exist_ok=True)
        log_file = open("storage/logs/meet_bot.log", "a", encoding="utf-8")
        cmd = [sys.executable, "poc/meet_bot.py", meet_url]
        p = subprocess.Popen(cmd, cwd=os.getcwd(), stdout=log_file, stderr=subprocess.STDOUT)
        
        active_bot_state["process"] = p
        active_bot_state["pid"] = p.pid
        active_bot_state["meet_url"] = meet_url
        active_bot_state["started_at"] = datetime.now(timezone.utc).isoformat()
        active_bot_state["meeting_id"] = None
        active_bot_state["is_speaking"] = req.is_speaking

        return {
            "status": "launched",
            "pid": p.pid,
            "is_speaking": req.is_speaking,
            "meet_url": meet_url,
            "message": "AI Bot launched! It will join open calls directly or request host admission."
        }

@router.get("/{meeting_id}", response_model=MeetingResponse)
async def get_meeting(
    meeting_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    res = await db.execute(
        select(Meeting).where(Meeting.id == meeting_id).options(
            selectinload(Meeting.attempts),
            selectinload(Meeting.transcripts),
            selectinload(Meeting.recordings)
        )
    )
    meeting = res.scalars().first()
    if not meeting:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Meeting not found")
    return meeting

@router.post("/{meeting_id}/attempts", response_model=MeetingAttemptResponse)
async def record_meeting_attempt(
    meeting_id: str,
    join_status: JoinStatus,
    failure_reason: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    res = await db.execute(select(Meeting).where(Meeting.id == meeting_id).options(selectinload(Meeting.attempts)))
    meeting = res.scalars().first()
    if not meeting:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Meeting not found")

    attempt = MeetingAttempt(
        meeting_id=meeting.id,
        attempt_number=len(meeting.attempts) + 1,
        join_status=join_status,
        bot_display_name="Task Reviewer AI (Assistant)",
        join_time_utc=datetime.now(timezone.utc) if join_status == JoinStatus.JOINED else None,
        failure_reason=failure_reason
    )
    db.add(attempt)
    if join_status == JoinStatus.JOINED:
        meeting.status = MeetingStatus.IN_PROGRESS

    await db.commit()
    await db.refresh(attempt)
    return attempt

@router.post("/{meeting_id}/transcripts", response_model=TranscriptResponse)
async def add_transcript(
    meeting_id: str,
    req: AddTranscriptRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    res = await db.execute(select(Meeting).where(Meeting.id == meeting_id))
    meeting = res.scalars().first()
    if not meeting:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Meeting not found")

    transcript = Transcript(
        meeting_id=meeting.id,
        speaker_label=req.speaker_label,
        spoken_text=req.spoken_text,
        confidence=req.confidence,
        timestamp_offset_sec=req.timestamp_offset_sec,
        source=req.source
    )
    db.add(transcript)
    await db.commit()
    await db.refresh(transcript)
    return transcript

@router.post("/{meeting_id}/consent")
async def record_consent(
    meeting_id: str,
    req: ConsentRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    res = await db.execute(select(Meeting).where(Meeting.id == meeting_id))
    meeting = res.scalars().first()
    if not meeting:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Meeting not found")

    recording = Recording(
        meeting_id=meeting.id,
        file_path=f"storage/recordings/{meeting.id}.wav",
        consent_confirmed=req.consent_confirmed,
        consent_recorded_at=datetime.now(timezone.utc) if req.consent_confirmed else None
    )
    db.add(recording)

    audit = AuditLog(
        actor_id=current_user.id,
        actor_email=current_user.email,
        action="RECORDING_CONSENT_RECORDED",
        resource_type="meeting",
        resource_id=meeting.id,
        details_json=f'{{"consent_confirmed": {str(req.consent_confirmed).lower()}}}'
    )
    db.add(audit)
    await db.commit()
    return {"status": "ok", "consent_confirmed": req.consent_confirmed}

@router.post("/{meeting_id}/complete-briefing")
async def complete_briefing_session(
    meeting_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Marks briefing meeting completed, generates transcript-grounded summary email,
    and updates task state to BRIEFING_COMPLETED.
    """
    res = await db.execute(
        select(Meeting).where(Meeting.id == meeting_id).options(
            selectinload(Meeting.task).selectinload(Task.versions).selectinload(TaskVersion.requirements),
            selectinload(Meeting.task).selectinload(Task.intern),
            selectinload(Meeting.transcripts)
        )
    )
    meeting = res.scalars().first()
    if not meeting:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Meeting not found")

    task = meeting.task
    current_ver = task.versions[-1] if task.versions else None
    if not current_ver:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No approved version for task")

    meeting.status = MeetingStatus.COMPLETED
    task.status = TaskStatus.BRIEFING_COMPLETED

    # Send transcript-grounded briefing email
    recipient = task.intern.email if task.intern else current_user.email
    transcript_texts = [f"{t.speaker_label}: {t.spoken_text}" for t in meeting.transcripts]

    review_time_str = SchedulingService.format_to_local(current_ver.deadline_utc, current_ver.display_timezone)
    req_dicts = [{"req_code": r.req_code, "title": r.title, "description": r.description} for r in current_ver.requirements]

    await EmailService.send_briefing_summary_email(
        db=db,
        task_id=task.id,
        recipient_email=recipient,
        task_title=task.title,
        objective=current_ver.objective,
        requirements=req_dicts,
        deliverables=current_ver.deliverables,
        deadline_str=review_time_str,
        timezone_str=current_ver.display_timezone,
        review_meeting_url=meeting.google_meet_url,
        review_meeting_time_str=review_time_str,
        transcripts=transcript_texts,
        unresolved_questions=[]
    )

    audit = AuditLog(
        actor_id=current_user.id,
        actor_email=current_user.email,
        action="BRIEFING_COMPLETED",
        resource_type="task",
        resource_id=task.id
    )
    db.add(audit)
    await db.commit()

    return {"status": "ok", "message": "Briefing session completed and summary email dispatched."}

@router.post("/{meeting_id}/launch-bot")
async def launch_meet_bot(
    meeting_id: str,
    req: Optional[LaunchBotRequest] = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Launches the autonomous Google Meet bot via MeetingBaas Cloud API with target meeting URL.
    Supports Interactive Speaking Mode with task rubric ground-truth injection and Silent Recording Mode.
    """
    is_speaking = req.is_speaking if req is not None else True
    bot_name = (req.bot_name if req is not None else None) or "AI Task Reviewer"

    res = await db.execute(
        select(Meeting).where(Meeting.id == meeting_id).options(
            selectinload(Meeting.attempts),
            selectinload(Meeting.task).selectinload(Task.versions).selectinload(TaskVersion.requirements),
            selectinload(Meeting.task).selectinload(Task.intern),
            selectinload(Meeting.task).selectinload(Task.assigner)
        )
    )
    meeting = res.scalars().first()
    if not meeting:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Meeting not found")

    meet_url = meeting.google_meet_url

    # Build task-grounded prompt and entry message
    task = meeting.task
    task_prompt = None
    entry_msg = None

    if task:
        current_ver = task.versions[-1] if task.versions else None
        task_title = task.title
        intern_name = task.intern.full_name if task.intern else "Intern"
        assigner_name = task.assigner.full_name if task.assigner else "Assigner"

        if current_ver:
            deadline_str = SchedulingService.format_to_local(current_ver.deadline_utc, current_ver.display_timezone)
            rubric_items = [
                f"- [{r.req_code}] {r.title}: {r.description}"
                for r in (current_ver.requirements or [])
            ]
            rubric_text = "\n".join(rubric_items) if rubric_items else "Follow standard engineering best practices."

            task_prompt = f"""You are Subha, the AI Task Reviewer bot participating live in this Google Meet session.
You are speaking directly with {intern_name} (the assigned intern) and {assigner_name} (the task assigner).
You have a warm, natural Indian English accent.

CRITICAL CONVERSATIONAL RULES (MUST FOLLOW):
1. DO NOT recite, summarize, or read the task specifications or rubric when joining.
2. Say at most 1 short sentence on join, then immediately STOP and WAIT for a participant to speak.
3. Keep all spoken answers strictly under 2 short sentences (maximum 25 words).
4. Never monologue or list multiple points at once. Answer directly, then pause to let the human speak.
5. Do NOT output markdown, bullet points, asterisks, or numbered lists—your text is read aloud over Text-To-Speech audio.
6. Only provide details from the task specification below when explicitly asked by a human.

GROUND TRUTH TASK SPECIFICATION (REFERENCE ONLY - DO NOT RECITE UNPROMPTED):
Task: {task_title}
Objective: {current_ver.objective}
Deliverables: {current_ver.deliverables}
Deadline: {deadline_str} ({current_ver.display_timezone})

EVALUATION RUBRIC & REQUIREMENTS:
{rubric_text}
"""
            entry_msg = f"Hi everyone! I am Subha, your AI Reviewer for '{task_title}'. What questions can I answer for you?"

    if req and req.custom_prompt:
        task_prompt = req.custom_prompt
    if req and req.custom_entry_message:
        entry_msg = req.custom_entry_message

    # 1. Deploy via MeetingBaas Cloud Bot
    deploy_res = await MeetingBaasService.deploy_bot(
        meeting_url=meet_url,
        bot_name=bot_name,
        entry_message=entry_msg,
        prompt=task_prompt,
        is_speaking=is_speaking
    )

    if deploy_res.get("success"):
        bot_id = deploy_res.get("bot_id")
        active_bot_state["bot_id"] = bot_id
        active_bot_state["status"] = deploy_res.get("status", "joining")
        active_bot_state["meet_url"] = deploy_res.get("meeting_url")
        active_bot_state["started_at"] = datetime.now(timezone.utc).isoformat()
        active_bot_state["meeting_id"] = meeting.id
        active_bot_state["is_speaking"] = is_speaking

        attempt = MeetingAttempt(
            meeting_id=meeting.id,
            attempt_number=len(meeting.attempts) + 1 if meeting.attempts else 1,
            join_status=JoinStatus.JOINED,
            bot_display_name=f"AI Task Reviewer ({'Speaking' if is_speaking else 'Recording'})",
            join_time_utc=datetime.now(timezone.utc)
        )
        db.add(attempt)
        meeting.status = MeetingStatus.IN_PROGRESS
        await db.commit()

        mode_desc = "Interactive Speaking Mode" if is_speaking else "Silent Recording Mode"
        return {
            "status": "launched",
            "bot_id": bot_id,
            "is_speaking": is_speaking,
            "meeting_id": meeting.id,
            "google_meet_url": meeting.google_meet_url,
            "message": f"AI Bot dispatched via MeetingBaas in {mode_desc}! It will enter your Google Meet, speak aloud, and record & transcribe."
        }
    else:
        # Fallback local runner
        os.makedirs("storage/logs", exist_ok=True)
        log_file = open("storage/logs/meet_bot.log", "a", encoding="utf-8")
        cmd = [sys.executable, "poc/meet_bot.py", meet_url]
        p = subprocess.Popen(cmd, cwd=os.getcwd(), stdout=log_file, stderr=subprocess.STDOUT)

        active_bot_state["process"] = p
        active_bot_state["pid"] = p.pid
        active_bot_state["meet_url"] = meet_url
        active_bot_state["started_at"] = datetime.now(timezone.utc).isoformat()
        active_bot_state["meeting_id"] = meeting.id
        active_bot_state["is_speaking"] = is_speaking

        return {
            "status": "launched_fallback",
            "pid": p.pid,
            "is_speaking": is_speaking,
            "meeting_id": meeting.id,
            "google_meet_url": meeting.google_meet_url,
            "message": "AI Bot launched via local fallback process."
        }

@router.get("/baas/bots")
async def list_baas_bots(current_user: User = Depends(get_current_user)):
    """Lists all bots deployed under the MeetingBaas account."""
    return await MeetingBaasService.list_bots()

@router.post("/{meeting_id}/sync-baas")
async def sync_baas_transcripts(
    meeting_id: str,
    bot_id: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Synchronizes speaker-diarized transcripts and MP4 recordings from MeetingBaas into the database.
    """
    target_bot_id = bot_id or active_bot_state.get("bot_id")
    if not target_bot_id:
        # Find the most recent bot matching the meeting URL
        res = await db.execute(select(Meeting).where(Meeting.id == meeting_id))
        m = res.scalars().first()
        if m and m.google_meet_url:
            all_bots = await MeetingBaasService.list_bots()
            for b in all_bots:
                if b.get("meeting_url") and (m.google_meet_url in b.get("meeting_url") or b.get("meeting_url") in m.google_meet_url):
                    target_bot_id = b.get("bot_id")
                    break

    if not target_bot_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No MeetingBaas bot ID found to synchronize transcripts."
        )

    sync_result = await MeetingBaasService.sync_transcripts_to_db(meeting_id, target_bot_id, db)
    return sync_result

