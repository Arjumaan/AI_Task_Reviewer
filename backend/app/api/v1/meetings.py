"""
Meeting Execution, Bot Orchestration, Transcripts, and Briefing Closeout.
"""
from datetime import datetime, timezone, timedelta
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Request
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from backend.app.core.database import get_db
from backend.app.core.config import settings
from backend.app.models.user import User, UserRole
from backend.app.models.task import Task, TaskStatus, TaskVersion, TaskDocument
from backend.app.models.meeting import (
    Meeting, MeetingAttempt, Transcript, Recording,
    MeetingType, MeetingStatus, JoinStatus, TranscriptSource
)
from backend.app.models.audit import AuditLog
from backend.app.models.review import (
    Submission, ReviewRound, RoundStatus, EvaluationOutcome
)
from backend.app.schemas.meeting import (
    MeetingResponse, MeetingAttemptResponse, TranscriptResponse
)
import subprocess
import os
import sys
import json
from backend.app.services.email_service import EmailService
from backend.app.services.scheduling import SchedulingService
from backend.app.services.meeting_baas import MeetingBaasService
from backend.app.services.task_intelligence import TaskIntelligenceService
from backend.app.api.deps import get_current_user, require_roles

router = APIRouter(prefix="/meetings", tags=["Meetings"])

# Track active bot state in memory (Supports MeetingBaas cloud bots and local fallbacks)
active_bot_state = {
    "process": None,
    "pid": None,
    "meet_url": None,
    "started_at": None,
    "meeting_id": None,
    "task_id": None,
    "bot_id": None,
    "status": None,
    "closeout_done": None,
    "is_speaking": True
}

_completed_meeting_ids = set()

async def auto_complete_meeting_session(
    meeting_id: Optional[str] = None,
    bot_id: Optional[str] = None,
    db: Optional[AsyncSession] = None
) -> Optional[dict]:
    """
    Concludes briefing session automatically, syncs transcripts from MeetingBaas,
    advances task status to IN_PROGRESS, generates the next review Google Meet URL,
    and sends the briefing discussion summary and task documents to the intern via SMTP.
    """
    target_bot_id = bot_id or active_bot_state.get("bot_id")
    target_meeting_id = meeting_id or active_bot_state.get("meeting_id")

    if db is None:
        from backend.app.core.database import AsyncSessionLocal
        async with AsyncSessionLocal() as session:
            return await auto_complete_meeting_session(meeting_id=target_meeting_id, bot_id=target_bot_id, db=session)

    meeting = None
    if target_meeting_id:
        res = await db.execute(
            select(Meeting).where(Meeting.id == target_meeting_id).options(
                selectinload(Meeting.task).selectinload(Task.versions).selectinload(TaskVersion.requirements),
                selectinload(Meeting.task).selectinload(Task.intern),
                selectinload(Meeting.task).selectinload(Task.documents),
                selectinload(Meeting.transcripts)
            )
        )
        meeting = res.scalars().first()

    # Fallback: check by meet_url
    if not meeting and active_bot_state.get("meet_url"):
        raw_url = active_bot_state.get("meet_url")
        norm_url = MeetingBaasService.normalize_meet_url(raw_url)
        res = await db.execute(
            select(Meeting).where(
                (Meeting.google_meet_url == raw_url) |
                (Meeting.google_meet_url == norm_url)
            ).options(
                selectinload(Meeting.task).selectinload(Task.versions).selectinload(TaskVersion.requirements),
                selectinload(Meeting.task).selectinload(Task.intern),
                selectinload(Meeting.task).selectinload(Task.documents),
                selectinload(Meeting.transcripts)
            ).order_by(Meeting.created_at.desc())
        )
        meeting = res.scalars().first()

    # Fallback: find latest briefing meeting
    if not meeting:
        res = await db.execute(
            select(Meeting).where(Meeting.meeting_type == MeetingType.BRIEFING).options(
                selectinload(Meeting.task).selectinload(Task.versions).selectinload(TaskVersion.requirements),
                selectinload(Meeting.task).selectinload(Task.intern),
                selectinload(Meeting.task).selectinload(Task.documents),
                selectinload(Meeting.transcripts)
            ).order_by(Meeting.created_at.desc())
        )
        all_briefings = res.scalars().all()
        meeting = next((m for m in all_briefings if m.task and m.task.intern), None) or (all_briefings[0] if all_briefings else None)

    if not meeting or not meeting.task:
        return None

    if meeting.id in _completed_meeting_ids:
        return {"status": "ALREADY_COMPLETED", "meeting_id": meeting.id}

    _completed_meeting_ids.add(meeting.id)

    # 1. Synchronize transcripts & video from MeetingBaas
    if target_bot_id:
        try:
            await MeetingBaasService.sync_transcripts_to_db(meeting.id, target_bot_id, db)
        except Exception as e:
            pass

    # Fetch all fresh transcripts
    t_res = await db.execute(
        select(Transcript).where(Transcript.meeting_id == meeting.id).order_by(Transcript.timestamp_offset_sec.asc())
    )
    all_transcripts = t_res.scalars().all()

    task = meeting.task
    intern_name = task.intern.full_name if task.intern else "Intern"
    intern_email = task.intern.email if task.intern else (settings.SMTP_FROM_EMAIL or "arjumaan21@gmail.com")
    doc = task.documents[0] if task.documents else None

    # If this is a REVIEW session:
    if meeting.meeting_type == MeetingType.REVIEW:
        if all_transcripts:
            conversation_dialogue = "\n".join([f"• {t.speaker_label or 'Participant'}: {t.spoken_text}" for t in all_transcripts])
            discussion_summary = (
                f"Review Session #{meeting.meeting_round or 1} for '{task.title}' was conducted with {intern_name} by Subha HR.\n\n"
                f"Review Dialogue & Technical Discussion:\n{conversation_dialogue}\n\n"
                f"Session Summary:\n"
                f"- Implementation code walkthrough and demo were conducted by {intern_name}.\n"
                f"- Acceptance criteria and test coverage were reviewed by Subha HR.\n"
                f"- Review session concluded. Task is now under final HR evaluation."
            )
        else:
            discussion_summary = (
                f"Review Session #{meeting.meeting_round or 1} for '{task.title}' was conducted with {intern_name} by Subha HR.\n"
                f"The intern presented their implementation demo, code changes, and test results for evaluation."
            )

        meeting.status = MeetingStatus.COMPLETED
        meeting.feedback_summary = discussion_summary
        task.status = TaskStatus.UNDER_REVIEW
        await db.commit()

        return {
            "status": "COMPLETED",
            "meeting_id": meeting.id,
            "meeting_type": "REVIEW",
            "task_id": task.id,
            "task_title": task.title,
            "discussion_summary": discussion_summary
        }

    # Otherwise, this is a BRIEFING session:
    if all_transcripts:
        conversation_dialogue = "\n".join([f"• {t.speaker_label or 'Participant'}: {t.spoken_text}" for t in all_transcripts])
        discussion_summary = (
            f"The task briefing for '{task.title}' was conducted with {intern_name} by Subha HR.\n\n"
            f"Meeting Dialogue & Key Questions Discussed:\n{conversation_dialogue}\n\n"
            f"Key Takeaways & Alignment:\n"
            f"- Subha HR briefed the intern on core requirements, edge cases, and test expectations.\n"
            f"- The intern asked clarifying questions and confirmed understanding of the technical scope.\n"
            f"- The deadline was confirmed, and the intern was cleared to proceed with implementation."
        )
    else:
        discussion_summary = (
            f"The task briefing for '{task.title}' was conducted with {intern_name} by Subha HR.\n"
            f"Deliverables, prerequisites, and evaluation rubric were reviewed and confirmed."
        )

    # 3. Schedule next Review Meeting at task deadline (only if one doesn't exist)
    now_utc = datetime.now(timezone.utc)
    current_version = task.versions[-1] if task.versions else None
    if current_version and current_version.deadline_utc:
        review_start_utc = current_version.deadline_utc
        tz_str = current_version.display_timezone or "Asia/Kolkata"
    else:
        review_start_utc = now_utc + timedelta(days=7)
        tz_str = "Asia/Kolkata"

    m_check = await db.execute(
        select(Meeting).where(
            Meeting.task_id == task.id,
            Meeting.meeting_type == MeetingType.REVIEW
        ).order_by(Meeting.created_at.desc())
    )
    existing_rev = m_check.scalars().first()

    if existing_rev:
        new_meet_url = existing_rev.google_meet_url
        review_date_formatted = SchedulingService.format_to_local(existing_rev.scheduled_start_utc, tz_str)
    else:
        event_id, new_meet_url, conf_id, is_dry = await SchedulingService.create_meeting_event(
            task_id=task.id,
            meeting_type=MeetingType.REVIEW,
            start_utc=review_start_utc,
            duration_minutes=45,
            display_tz=tz_str,
            attendee_emails=[intern_email]
        )
        review_meeting = Meeting(
            task_id=task.id,
            meeting_type=MeetingType.REVIEW,
            status=MeetingStatus.SCHEDULED,
            scheduled_start_utc=review_start_utc,
            scheduled_end_utc=review_start_utc + timedelta(minutes=45),
            timezone=tz_str,
            google_meet_url=new_meet_url,
            google_event_id=event_id,
            conference_id=conf_id,
            meeting_round=1,
            is_dry_run=is_dry
        )
        db.add(review_meeting)
        review_date_formatted = SchedulingService.format_to_local(review_start_utc, tz_str)

    # 4. Advance meeting & task status
    meeting.status = MeetingStatus.COMPLETED
    meeting.feedback_summary = discussion_summary
    task.status = TaskStatus.IN_PROGRESS
    await db.flush()

    # 5. Send post-meeting feedback email via SMTP
    deadline_formatted = review_date_formatted

    doc_path = doc.file_path if (doc and doc.file_path and os.path.isfile(doc.file_path)) else None
    doc_name = doc.filename if doc else "Task_Specification.pdf"

    deliverables_text = "Deliver clean code, automated unit/integration test proofs, and complete documentation."
    if current_version and current_version.requirements:
        deliverables_text = "; ".join([r.title for r in current_version.requirements])

    email_res = await EmailService.send_meeting_feedback_email(
        db=db,
        task_id=task.id,
        to_email=intern_email,
        intern_name=intern_name,
        task_title=task.title,
        discussion_summary=discussion_summary,
        deadline_str=deadline_formatted,
        review_meeting_url=new_meet_url,
        review_meeting_time_str=review_date_formatted,
        doc_path=doc_path,
        doc_filename=doc_name,
        key_deliverables=deliverables_text,
        assigner_name="Subha HR"
    )

    await db.commit()

    return {
        "status": "COMPLETED",
        "meeting_id": meeting.id,
        "meeting_type": "BRIEFING",
        "task_id": task.id,
        "task_title": task.title,
        "email_sent_to": intern_email,
        "review_meeting_url": new_meet_url,
        "review_scheduled_at": review_date_formatted,
        "email_status": email_res
    }


class DirectBotLaunchRequest(BaseModel):
    meet_url: str
    is_speaking: bool = True
    bot_name: Optional[str] = "Subha HR"
    prompt: Optional[str] = None
    entry_message: Optional[str] = None
    task_id: Optional[str] = None

class LaunchBotRequest(BaseModel):
    is_speaking: bool = True
    bot_name: Optional[str] = "Subha HR"
    custom_prompt: Optional[str] = None
    custom_entry_message: Optional[str] = None

async def build_task_grounded_prompt(task: Task, is_review: bool = False) -> tuple[str, str]:
    """
    Builds a deeply grounded prompt and entry message for the Meeting AI Bot.
    Uses the task's latest uploaded document intelligence, requirements, and rubric.
    Adapts persona and instructions dynamically for Briefing vs Review sessions.
    """
    task_title = task.title
    intern_name = task.intern.full_name if task.intern else "Intern"
    assigner_name = task.assigner.full_name if task.assigner else "Assigner"

    current_ver = task.versions[-1] if task.versions else None
    latest_doc = task.documents[-1] if task.documents else None

    doc_title = task_title
    doc_filename = latest_doc.filename if latest_doc else "Uploaded Brief"
    exec_summary = ""
    findings_text = ""
    deliverables_text = "Clean working implementation, comprehensive test suite, and verification evidence."

    if latest_doc:
        analysis = {}
        if latest_doc.analysis_json:
            try:
                analysis = json.loads(latest_doc.analysis_json)
            except Exception:
                analysis = {}
        if not analysis and latest_doc.extracted_raw_text:
            analysis = await TaskIntelligenceService.analyze_document_comprehensively(
                latest_doc.extracted_raw_text, latest_doc.filename, task_title
            )

        if analysis:
            doc_title = analysis.get("title", task_title)
            exec_summary = analysis.get("executive_summary", "")
            findings_text = analysis.get("findings_text", "")
            deliverables_text = analysis.get("deliverables_text", deliverables_text)

    if current_ver:
        deadline_str = SchedulingService.format_to_local(current_ver.deadline_utc, current_ver.display_timezone)
        rubric_items = [
            f"- {r.title}: {r.description}"
            for r in (current_ver.requirements or [])
        ]
        rubric_text = "\n".join(rubric_items) if rubric_items else "Deliver clean code, 100% passing tests, and no regressions."
    else:
        deadline_str = "within 7 days of briefing"
        rubric_text = "- Deliver verified code and passing test reports."

    if is_review:
        entry_msg = (
            f"Hello! I am Subha HR. Welcome to your review and evaluation session for the {task_title} task. "
            f"Please share your screen, walk me through your code implementation, and show your test results."
        )
        task_prompt = f"""--- PERSONA SPECIFICATION ---
Name: Subha HR
Gender: female
Role: Senior Technical Reviewer and HR Lead
Voice: Warm, professional, natural, feminine Indian English voice
------------------------------

You are Subha HR, a female senior technical reviewer and HR lead conducting this live Google Meet REVIEW and EVALUATION session with {intern_name}.
You speak in a natural, warm, feminine Indian English accent. You are a female professional.

SESSION OBJECTIVE (CODE DEMO & EVALUATION):
This is a TECHNICAL EVALUATION session for the intern's implementation of "{task_title}".
1. Prompt {intern_name} to present their work, walk through their code changes, and demonstrate running the implementation.
2. Inquire about test suites, edge cases, error handling, and criteria adherence.
3. Keep every spoken answer or question to 2 to 3 short sentences (maximum 35 words).
4. After speaking, pause immediately and wait so {intern_name} can demo and answer.
5. Provide encouraging yet rigorous technical evaluation feedback.

GROUND TRUTH TASK KNOWLEDGE & CRITERIA:
- Task Title: {doc_title}
- Overview: {exec_summary}
- Objectives & Key Areas: {findings_text}
- Deliverables Expected: {deliverables_text}
- Criteria & Expectations:
{rubric_text}
"""
    else:
        entry_msg = (
            f"Hi, I'm Subha. The {task_title} task has been assigned to you. "
            f"Now I will explain the task in brief. Listen and ask me if you have any questions."
        )
        task_prompt = f"""--- PERSONA SPECIFICATION ---
Name: Subha HR
Gender: female
Role: Senior Female HR and Technical Review Lead
Voice: Warm, natural, conversational, feminine Indian English voice
------------------------------

You are Subha HR, a friendly, professional female HR leader and technical reviewer conducting this live Google Meet briefing session with {intern_name}.
You speak in a natural, warm, feminine Indian English accent. You are a female professional.

CORE CONVERSATIONAL INSTRUCTIONS (MUST FOLLOW):
1. ACTIVE LISTENING: Carefully listen to the participant's question or statement before replying. Understand the exact intent of their question.
2. ANSWER DIRECTLY: Answer the participant's specific question directly, clearly, and accurately using the task ground truth below.
3. CONCISE SPOKEN TURNS: Keep every spoken answer to 2 to 3 short sentences (maximum 35 words). Never monologue, never recite whole documents, and never read out long bullet lists over audio.
4. NATURAL PAUSES: As soon as you finish answering the question, stop speaking immediately and wait so {intern_name} can reply or ask follow-up questions.
5. IF ASKED TO EXPLAIN THE TASK: Provide a clear, natural 2-sentence summary of the task objective and what needs to be delivered, then ask if they have any specific doubts.
6. SPOKEN AUDIO RULES: You are speaking through real-time audio. Never say asterisks, bullet points, hashes, markdown, or raw requirement codes. Speak like a helpful, supportive human colleague.

GROUND TRUTH TASK KNOWLEDGE:
- Task Title: {doc_title}
- Summary: {exec_summary}
- Objectives & Key Areas: {findings_text}
- Deliverables: {deliverables_text}
- Deadline: {deadline_str}
- Criteria & Expectations:
{rubric_text}
"""
    return task_prompt, entry_msg


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

    # If bot transitioned to completed or call ended, trigger auto closeout
    if bot_id and status_str in ["completed", "call_ended", "ended"]:
        if active_bot_state.get("closeout_done") != bot_id:
            active_bot_state["closeout_done"] = bot_id
            import asyncio
            asyncio.create_task(auto_complete_meeting_session(meeting_id=active_bot_state.get("meeting_id"), bot_id=bot_id))

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

    # If meeting completed or call ended, auto-closeout and email
    meeting_id = active_bot_state.get("meeting_id")
    if bot_id and ("complete" in str(event_type).lower() or any(k in str(data.get("status", "")).lower() for k in ["completed", "call_ended", "ended"])):
        if active_bot_state.get("closeout_done") != bot_id:
            active_bot_state["closeout_done"] = bot_id
            try:
                await auto_complete_meeting_session(meeting_id=meeting_id, bot_id=bot_id, db=db)
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
        try:
            await MeetingBaasService.leave_meeting(bot_id)
        except Exception:
            pass
        active_bot_state["status"] = "completed"

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

    # 3. Always trigger auto-closeout and email
    closeout_res = await auto_complete_meeting_session(meeting_id=meeting_id, bot_id=bot_id, db=db)
    active_bot_state["closeout_done"] = bot_id

    return {
        "status": "stopped",
        "bot_id": bot_id,
        "closeout": closeout_res,
        "message": "Meeting finished! Transcripts synchronized and summary email dispatched to intern via SMTP."
    }

@router.post("/launch-direct")
async def launch_direct_bot(
    req: DirectBotLaunchRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    meet_url = req.meet_url.strip()
    if not meet_url:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Meeting URL or code is required")

    task = None
    if req.task_id:
        t_res = await db.execute(
            select(Task).where(Task.id == req.task_id).options(
                selectinload(Task.documents),
                selectinload(Task.versions).selectinload(TaskVersion.requirements),
                selectinload(Task.intern),
                selectinload(Task.assigner)
            )
        )
        task = t_res.scalars().first()

    if not task:
        t_res = await db.execute(
            select(Task).options(
                selectinload(Task.documents),
                selectinload(Task.versions).selectinload(TaskVersion.requirements),
                selectinload(Task.intern),
                selectinload(Task.assigner)
            ).order_by(Task.updated_at.desc())
        )
        all_t = t_res.scalars().all()
        task = next((t for t in all_t if t.documents), None) or (all_t[0] if all_t else None)

    # Determine session type:
    # First session for a task is Briefing; all subsequent sessions for the task are Review sessions.
    is_review = False
    session_type = MeetingType.BRIEFING
    meeting_round = 1
    meeting_record = None

    if task:
        m_res = await db.execute(
            select(Meeting).where(Meeting.task_id == task.id).order_by(Meeting.created_at.asc())
        )
        task_meetings = m_res.scalars().all()
        has_briefing = any(m.meeting_type == MeetingType.BRIEFING for m in task_meetings)

        if not has_briefing:
            session_type = MeetingType.BRIEFING
            meeting_round = 1
            is_review = False
        else:
            session_type = MeetingType.REVIEW
            review_count = sum(1 for m in task_meetings if m.meeting_type == MeetingType.REVIEW)
            meeting_round = review_count + 1
            is_review = True

        # Check if an existing scheduled or in-progress meeting exists for this session type
        pending_meeting = next((
            m for m in reversed(task_meetings)
            if m.meeting_type == session_type and m.status in [MeetingStatus.SCHEDULED, MeetingStatus.IN_PROGRESS]
        ), None)

        if pending_meeting:
            meeting_record = pending_meeting
            meeting_record.status = MeetingStatus.IN_PROGRESS
            meeting_record.google_meet_url = meet_url
        else:
            meeting_record = Meeting(
                task_id=task.id,
                meeting_type=session_type,
                status=MeetingStatus.IN_PROGRESS,
                google_meet_url=meet_url,
                timezone="Asia/Kolkata",
                scheduled_start_utc=datetime.now(timezone.utc),
                scheduled_end_utc=datetime.now(timezone.utc) + timedelta(minutes=45 if is_review else 30),
                meeting_round=meeting_round
            )
            db.add(meeting_record)
            await db.flush()

        attempt = MeetingAttempt(
            meeting_id=meeting_record.id,
            attempt_number=1,
            join_status=JoinStatus.JOINED,
            bot_display_name="Subha HR",
            join_time_utc=datetime.now(timezone.utc)
        )
        db.add(attempt)
        await db.commit()

    task_prompt = req.prompt
    entry_msg = req.entry_message

    if task and (not task_prompt or not entry_msg):
        generated_prompt, generated_entry = await build_task_grounded_prompt(task, is_review=is_review)
        if not task_prompt:
            task_prompt = generated_prompt
        if not entry_msg:
            entry_msg = generated_entry

    # Deploy via MeetingBaas Cloud Bot (Speaking mode or Silent recording mode)
    deploy_res = await MeetingBaasService.deploy_bot(
        meeting_url=meet_url,
        bot_name=req.bot_name or "Subha HR",
        entry_message=entry_msg,
        prompt=task_prompt,
        is_speaking=req.is_speaking
    )

    if deploy_res.get("success"):
        bot_id = deploy_res.get("bot_id")
        active_bot_state["bot_id"] = bot_id
        active_bot_state["status"] = deploy_res.get("status", "joining")
        active_bot_state["meet_url"] = deploy_res.get("meeting_url")
        active_bot_state["started_at"] = datetime.now(timezone.utc).isoformat()
        active_bot_state["meeting_id"] = meeting_record.id if meeting_record else None
        active_bot_state["task_id"] = task.id if task else None
        active_bot_state["closeout_done"] = None
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

@router.post("/{meeting_id}/launch-bot")
async def launch_meeting_bot(
    meeting_id: str,
    req: LaunchBotRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    res = await db.execute(
        select(Meeting)
        .where(Meeting.id == meeting_id)
        .options(
            selectinload(Meeting.task).selectinload(Task.documents),
            selectinload(Meeting.task).selectinload(Task.versions).selectinload(TaskVersion.requirements),
            selectinload(Meeting.task).selectinload(Task.intern),
            selectinload(Meeting.task).selectinload(Task.assigner)
        )
    )
    meeting = res.scalars().first()
    if not meeting:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Meeting not found")

    meet_url = meeting.google_meet_url or settings.DEFAULT_GOOGLE_MEET_URL or "https://meet.google.com/meet/rqp-ctfg-nri"
    task = meeting.task
    is_review = (meeting.meeting_type == MeetingType.REVIEW)

    task_prompt = req.custom_prompt
    entry_msg = req.custom_entry_message
    if task and (not task_prompt or not entry_msg):
        generated_prompt, generated_entry = await build_task_grounded_prompt(task, is_review=is_review)
        if not task_prompt:
            task_prompt = generated_prompt
        if not entry_msg:
            entry_msg = generated_entry

    meeting.status = MeetingStatus.IN_PROGRESS
    attempt = MeetingAttempt(
        meeting_id=meeting.id,
        attempt_number=1,
        join_status=JoinStatus.JOINED,
        bot_display_name="Subha HR",
        join_time_utc=datetime.now(timezone.utc)
    )
    db.add(attempt)
    await db.commit()

    deploy_res = await MeetingBaasService.deploy_bot(
        meeting_url=meet_url,
        bot_name=req.bot_name or "Subha HR",
        entry_message=entry_msg,
        prompt=task_prompt,
        is_speaking=req.is_speaking
    )

    if deploy_res.get("success"):
        bot_id = deploy_res.get("bot_id")
        active_bot_state["bot_id"] = bot_id
        active_bot_state["status"] = deploy_res.get("status", "joining")
        active_bot_state["meet_url"] = deploy_res.get("meeting_url")
        active_bot_state["started_at"] = datetime.now(timezone.utc).isoformat()
        active_bot_state["meeting_id"] = meeting.id
        active_bot_state["task_id"] = task.id if task else None
        active_bot_state["closeout_done"] = None
        active_bot_state["is_speaking"] = req.is_speaking

        mode_desc = "Interactive Speaking Mode (Unmuted Voice AI)" if req.is_speaking else "Silent Recording Mode"
        return {
            "status": "launched",
            "bot_id": bot_id,
            "meeting_id": meeting.id,
            "is_speaking": req.is_speaking,
            "google_meet_url": deploy_res.get("meeting_url"),
            "message": f"AI Bot dispatched for {meeting.meeting_type.value} session in {mode_desc}!"
        }
    else:
        os.makedirs("storage/logs", exist_ok=True)
        log_file = open("storage/logs/meet_bot.log", "a", encoding="utf-8")
        cmd = [sys.executable, "poc/meet_bot.py", meet_url]
        p = subprocess.Popen(cmd, cwd=os.getcwd(), stdout=log_file, stderr=subprocess.STDOUT)
        
        active_bot_state["process"] = p
        active_bot_state["pid"] = p.pid
        active_bot_state["meet_url"] = meet_url
        active_bot_state["started_at"] = datetime.now(timezone.utc).isoformat()
        active_bot_state["meeting_id"] = meeting.id
        active_bot_state["task_id"] = task.id if task else None
        active_bot_state["is_speaking"] = req.is_speaking

        return {
            "status": "launched",
            "pid": p.pid,
            "meeting_id": meeting.id,
            "is_speaking": req.is_speaking,
            "google_meet_url": meet_url,
            "message": f"AI Bot launched for {meeting.meeting_type.value} session!"
        }

@router.get("/", response_model=List[MeetingResponse])
async def list_all_meetings(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Lists all scheduled and past meetings with attempts, transcripts, and recordings."""
    res = await db.execute(
        select(Meeting).options(
            selectinload(Meeting.attempts),
            selectinload(Meeting.transcripts),
            selectinload(Meeting.recordings)
        ).order_by(Meeting.created_at.desc())
    )
    return res.scalars().all()

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
        bot_display_name="Subha HR",
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
    current_user: User = Depends(require_roles([UserRole.ASSIGNER, UserRole.ADMIN]))
):
    """
    Concludes an intern briefing session:
    1. Marks the meeting as COMPLETED.
    2. Generates an AI summary of the briefing conversation and feedback.
    3. Updates task status to IN_PROGRESS.
    4. Automatically schedules the Review Meeting at the task completion deadline with a NEW Google Meet URL.
    5. Dispatches an email to the intern with session feedback and new review meeting details.
    """
    res = await db.execute(
        select(Meeting)
        .where(Meeting.id == meeting_id)
        .options(
            selectinload(Meeting.task).selectinload(Task.versions),
            selectinload(Meeting.task).selectinload(Task.intern),
            selectinload(Meeting.transcripts)
        )
    )
    meeting = res.scalars().first()
    if not meeting:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Meeting not found")

    task = meeting.task
    if not task:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Meeting has no associated task")

    meeting.status = MeetingStatus.COMPLETED

    # 1. Synthesize transcript feedback
    transcript_text = " ".join([t.spoken_text for t in meeting.transcripts]) if meeting.transcripts else ""
    if transcript_text:
        feedback = f"Briefing session completed. The intern engaged with Subha regarding '{task.title}'. Key objectives and rubrics were clarified successfully."
    else:
        feedback = f"Briefing session for '{task.title}' was conducted by Subha. The intern received an overview of deliverables, prerequisites, and rubric expectations."

    meeting.feedback_summary = feedback

    # 2. Advance task status to IN_PROGRESS
    task.status = TaskStatus.IN_PROGRESS

    # 3. Determine Review meeting time (at task deadline)
    now_utc = datetime.now(timezone.utc)
    current_version = task.versions[-1] if task.versions else None
    if current_version and current_version.deadline_utc:
        review_start_utc = current_version.deadline_utc
        tz_str = current_version.display_timezone or "Asia/Kolkata"
    else:
        review_start_utc = now_utc + timedelta(days=7)
        tz_str = "Asia/Kolkata"

    # 4. Generate NEW Google Meet link for Review session
    event_id, new_meet_url, conf_id, is_dry = await SchedulingService.create_meeting_event(
        task_id=task.id,
        meeting_type=MeetingType.REVIEW,
        start_utc=review_start_utc,
        duration_minutes=45,
        display_tz=tz_str,
        attendee_emails=[task.intern.email] if task.intern else []
    )

    # 5. Create new Review Meeting record
    review_meeting = Meeting(
        task_id=task.id,
        meeting_type=MeetingType.REVIEW,
        status=MeetingStatus.SCHEDULED,
        scheduled_start_utc=review_start_utc,
        scheduled_end_utc=review_start_utc + timedelta(minutes=45),
        timezone=tz_str,
        google_meet_url=new_meet_url,
        google_event_id=event_id,
        conference_id=conf_id,
        meeting_round=1,
        is_dry_run=is_dry
    )
    db.add(review_meeting)
    await db.flush()

    # 6. Send notification email via SMTP
    review_date_formatted = SchedulingService.format_to_local(review_start_utc, tz_str)
    if task.intern:
        email_status = await EmailService.send_task_assignment_email(
            db=db,
            task_id=task.id,
            to_email=task.intern.email,
            intern_name=task.intern.full_name,
            task_title=task.title,
            deadline_str=review_date_formatted,
            meeting_url=new_meet_url,
            doc_filename=f"Briefing_Feedback_{task.title[:20]}.txt",
            task_objective=feedback,
            assigner_name="Subha (AI Technical Reviewer)"
        )

    await db.commit()

    return {
        "status": "COMPLETED",
        "feedback_summary": feedback,
        "task_status": task.status.value,
        "review_meeting_id": review_meeting.id,
        "review_meeting_url": new_meet_url,
        "review_scheduled_at": review_date_formatted
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



class CompleteReviewRequest(BaseModel):
    passed: bool
    feedback: str
    gaps: Optional[List[str]] = None

@router.post("/{meeting_id}/complete-review")
async def complete_review_session(
    meeting_id: str,
    req: CompleteReviewRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles([UserRole.ASSIGNER, UserRole.ADMIN]))
):
    """
    Evaluates the review meeting outcome:
    - If PASSED: updates status to PASSED and sends congratulations email.
    - If REVISION_REQUIRED: updates status to REVISION_REQUIRED, generates next review date and NEW meet link, and sends email.
    """
    res = await db.execute(
        select(Meeting)
        .where(Meeting.id == meeting_id)
        .options(
            selectinload(Meeting.task).selectinload(Task.versions),
            selectinload(Meeting.task).selectinload(Task.intern),
            selectinload(Meeting.task).selectinload(Task.submissions).selectinload(Submission.review_rounds)
        )
    )
    meeting = res.scalars().first()
    task = None
    if meeting:
        task = meeting.task
    else:
        # Check if meeting_id was actually passed as task_id
        t_res = await db.execute(
            select(Task)
            .where(Task.id == meeting_id)
            .options(
                selectinload(Task.versions),
                selectinload(Task.intern),
                selectinload(Task.meetings),
                selectinload(Task.submissions).selectinload(Submission.review_rounds)
            )
        )
        task = t_res.scalars().first()
        if task:
            meeting = next((m for m in (task.meetings or []) if m.meeting_type == MeetingType.REVIEW), None)
            if not meeting and task.meetings:
                meeting = task.meetings[-1]
            if not meeting:
                meeting = Meeting(
                    task_id=task.id,
                    meeting_type=MeetingType.REVIEW,
                    status=MeetingStatus.COMPLETED,
                    scheduled_start_utc=datetime.now(timezone.utc),
                    scheduled_end_utc=datetime.now(timezone.utc) + timedelta(minutes=45),
                    timezone="Asia/Kolkata",
                    google_meet_url=f"https://meet.google.com/rev-{task.id[:4]}-{task.id[-4:]}",
                    meeting_round=1
                )
                db.add(meeting)
                await db.flush()

    if not task:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Meeting or associated Task not found")

    meeting.status = MeetingStatus.COMPLETED
    meeting.feedback_summary = req.feedback
    now_utc = datetime.now(timezone.utc)
    current_version = task.versions[-1] if task.versions else None
    tz_str = current_version.display_timezone if current_version else "Asia/Kolkata"

    # Find active review round if available
    active_round = None
    if task.submissions:
        latest_sub = task.submissions[-1]
        if latest_sub.review_rounds:
            active_round = latest_sub.review_rounds[-1]

    if req.passed:
        task.status = TaskStatus.PASSED
        if active_round:
            active_round.outcome = EvaluationOutcome.PASS
            active_round.total_score = 100.0
            active_round.status = RoundStatus.COMPLETED
            active_round.summary_notes = req.feedback
            active_round.completed_at = now_utc

        # Send completion congratulations email
        if task.intern:
            await EmailService.send_task_passed_email(
                db=db,
                task_id=task.id,
                to_email=task.intern.email,
                intern_name=task.intern.full_name,
                task_title=task.title,
                feedback=req.feedback,
                score=100.0,
                assigner_name="Subha HR"
            )

        audit = AuditLog(
            actor_id=current_user.id,
            actor_email=current_user.email,
            action="REVIEW_EVALUATION_PASSED",
            resource_type="task",
            resource_id=task.id,
            details_json=f'{{"outcome": "PASSED", "feedback": "{req.feedback[:200]}"}}'
        )
        db.add(audit)
        await db.commit()
        return {
            "status": "PASSED",
            "message": "Task marked as PASSED. Completion notice dispatched to intern.",
            "task_id": task.id
        }

    else:
        task.status = TaskStatus.REVISION_REQUIRED
        gaps_list = req.gaps or [req.feedback]
        gaps_text = "; ".join(gaps_list)

        if active_round:
            active_round.outcome = EvaluationOutcome.REVISION_REQUIRED
            active_round.status = RoundStatus.COMPLETED
            active_round.summary_notes = f"Revision Required: {gaps_text}"
            active_round.completed_at = now_utc

        # Calculate next review date (+2 days)
        next_review_utc = now_utc + timedelta(days=2)
        next_round = (meeting.meeting_round or 1) + 1

        # Generate NEW Google Meet link for subsequent review
        event_id, next_meet_url, conf_id, is_dry = await SchedulingService.create_meeting_event(
            task_id=task.id,
            meeting_type=MeetingType.REVIEW,
            start_utc=next_review_utc,
            duration_minutes=45,
            display_tz=tz_str,
            attendee_emails=[task.intern.email] if task.intern else []
        )

        next_meeting = Meeting(
            task_id=task.id,
            meeting_type=MeetingType.REVIEW,
            status=MeetingStatus.SCHEDULED,
            scheduled_start_utc=next_review_utc,
            scheduled_end_utc=next_review_utc + timedelta(minutes=45),
            timezone=tz_str,
            google_meet_url=next_meet_url,
            google_event_id=event_id,
            conference_id=conf_id,
            meeting_round=next_round,
            is_dry_run=is_dry
        )
        db.add(next_meeting)

        # Create new pending review round if submissions exist
        if task.submissions:
            latest_sub = task.submissions[-1]
            new_rev_round = ReviewRound(
                task_id=task.id,
                submission_id=latest_sub.id,
                round_number=next_round,
                status=RoundStatus.PENDING
            )
            db.add(new_rev_round)

        await db.flush()

        next_review_formatted = SchedulingService.format_to_local(next_review_utc, tz_str)

        # Dispatch revision notice email
        if task.intern:
            await EmailService.send_task_revision_email(
                db=db,
                task_id=task.id,
                to_email=task.intern.email,
                intern_name=task.intern.full_name,
                task_title=task.title,
                gaps=gaps_list,
                next_review_time_str=next_review_formatted,
                next_review_meet_url=next_meet_url,
                assigner_name="Subha HR"
            )

        audit = AuditLog(
            actor_id=current_user.id,
            actor_email=current_user.email,
            action="REVIEW_EVALUATION_REVISION_REQUIRED",
            resource_type="task",
            resource_id=task.id,
            details_json=f'{{"outcome": "REVISION_REQUIRED", "gaps": {gaps_list}, "next_meet_url": "{next_meet_url}"}}'
        )
        db.add(audit)
        await db.commit()
        return {
            "status": "REVISION_REQUIRED",
            "message": "Task marked as REVISION_REQUIRED. Next review scheduled and notice dispatched.",
            "next_meeting_id": next_meeting.id,
            "next_meeting_url": next_meet_url,
            "next_review_scheduled_at": next_review_formatted,
            "gaps": gaps_list
        }
