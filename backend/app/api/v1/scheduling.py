import os
"""
Meeting Scheduling and Calendar Endpoints.
"""
from datetime import datetime, timezone, timedelta
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from backend.app.core.database import get_db
from backend.app.core.config import settings
from backend.app.models.user import User, UserRole
from backend.app.models.task import Task, TaskStatus
from backend.app.models.meeting import Meeting, MeetingType, MeetingStatus
from backend.app.models.audit import AuditLog
from backend.app.schemas.meeting import (
    ScheduleMeetingRequest, RescheduleMeetingRequest, MeetingResponse
)
from backend.app.services.scheduling import SchedulingService
from backend.app.api.deps import get_current_user, require_roles

router = APIRouter(prefix="/scheduling", tags=["Scheduling"])

@router.post("/schedule", response_model=MeetingResponse, status_code=status.HTTP_201_CREATED)
@router.post("/meetings", response_model=MeetingResponse, status_code=status.HTTP_201_CREATED)
async def schedule_meeting(
    request: ScheduleMeetingRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles([UserRole.ASSIGNER, UserRole.ADMIN]))
):
    # Verify task exists
    res = await db.execute(select(Task).where(Task.id == request.task_id).options(selectinload(Task.intern), selectinload(Task.versions), selectinload(Task.documents)))
    task = res.scalars().first()
    if not task:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found")

    if request.meeting_type == MeetingType.BRIEFING and task.status == TaskStatus.DRAFT:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot schedule briefing before task specification is approved."
        )

    start_utc = SchedulingService.parse_to_utc(request.start_time_iso, request.timezone)
    end_utc = start_utc + timedelta(minutes=request.duration_minutes)

    attendees = [current_user.email]
    if task.intern and task.intern.email:
        attendees.append(task.intern.email)

    event_id, meet_url, conf_id, is_dry = await SchedulingService.create_meeting_event(
        task_id=task.id,
        meeting_type=request.meeting_type,
        start_utc=start_utc,
        duration_minutes=request.duration_minutes,
        display_tz=request.timezone,
        attendee_emails=attendees
    )

    if request.custom_meet_url and request.custom_meet_url.strip():
        raw_custom = request.custom_meet_url.strip()
        meet_url = raw_custom if raw_custom.startswith("http") else f"https://meet.google.com/{raw_custom}"

    meeting = Meeting(
        task_id=task.id,
        meeting_type=request.meeting_type,
        status=MeetingStatus.SCHEDULED,
        scheduled_start_utc=start_utc,
        scheduled_end_utc=end_utc,
        timezone=request.timezone,
        google_event_id=event_id,
        google_meet_url=meet_url,
        conference_id=conf_id,
        is_dry_run=is_dry
    )
    db.add(meeting)

    if request.meeting_type == MeetingType.BRIEFING:
        task.status = TaskStatus.BRIEFING_SCHEDULED

    # Dispatch assignment email to intern if assigned
    if request.meeting_type == MeetingType.BRIEFING and task.intern and task.intern.email:
        current_version = task.versions[-1] if task.versions else None
        deadline_str = "within 7 days"
        if current_version and current_version.deadline_utc:
            deadline_str = SchedulingService.format_to_local(
                current_version.deadline_utc,
                current_version.display_timezone or request.timezone
            )
        else:
            deadline_str = SchedulingService.format_to_local(
                start_utc + timedelta(days=7),
                request.timezone
            )

        doc = task.documents[0] if (task.documents and len(task.documents) > 0) else None
        doc_filename = doc.filename if doc else "Task_Specification.pdf"
        doc_path = doc.file_path if (doc and doc.file_path and os.path.isfile(doc.file_path)) else None
        task_obj = current_version.objective if current_version else None

        try:
            from backend.app.services.email_service import EmailService
            await EmailService.send_task_assignment_email(
                db=db,
                task_id=task.id,
                to_email=task.intern.email,
                intern_name=task.intern.full_name or "Intern",
                task_title=task.title,
                deadline_str=deadline_str,
                meeting_url=meet_url,
                doc_filename=doc_filename,
                doc_path=doc_path,
                task_objective=task_obj,
                assigner_name=current_user.full_name or "Task Assigner (HR)"
            )
        except Exception as e:
            import logging
            logging.getLogger(__name__).error(f"[SCHEDULING] Failed to dispatch assignment email: {e}")

    await db.commit()
    await db.refresh(meeting)

    audit = AuditLog(
        actor_id=current_user.id,
        actor_email=current_user.email,
        action="MEETING_SCHEDULED",
        resource_type="meeting",
        resource_id=meeting.id,
        details_json=f'{{"type": "{request.meeting_type.value}", "start": "{start_utc.isoformat()}", "meet_url": "{meet_url}"}}'
    )
    db.add(audit)
    await db.commit()

    return meeting

@router.post("/meetings/{meeting_id}/reschedule", response_model=MeetingResponse)
async def reschedule_meeting(
    meeting_id: str,
    request: RescheduleMeetingRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles([UserRole.ASSIGNER, UserRole.ADMIN]))
):
    res = await db.execute(select(Meeting).where(Meeting.id == meeting_id))
    meeting = res.scalars().first()
    if not meeting:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Meeting not found")

    new_start_utc = SchedulingService.parse_to_utc(request.new_start_time_iso, meeting.timezone)
    meeting.scheduled_start_utc = new_start_utc
    meeting.scheduled_end_utc = new_start_utc + timedelta(minutes=request.duration_minutes)
    meeting.status = MeetingStatus.RESCHEDULED
    meeting.cancellation_reason = f"Rescheduled: {request.reason}"

    await db.commit()
    await db.refresh(meeting)

    audit = AuditLog(
        actor_id=current_user.id,
        actor_email=current_user.email,
        action="MEETING_RESCHEDULED",
        resource_type="meeting",
        resource_id=meeting.id,
        details_json=f'{{"reason": "{request.reason}", "new_start": "{new_start_utc.isoformat()}"}}'
    )
    db.add(audit)
    await db.commit()

    return meeting

@router.get("/task/{task_id}", response_model=List[MeetingResponse])
@router.get("/tasks/{task_id}/meetings", response_model=List[MeetingResponse])
async def list_task_meetings(
    task_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    res = await db.execute(
        select(Meeting)
        .where(Meeting.task_id == task_id)
        .options(selectinload(Meeting.attempts), selectinload(Meeting.transcripts), selectinload(Meeting.recordings))
    )
    return res.scalars().all()
