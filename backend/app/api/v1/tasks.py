import os
"""
Task Lifecycle, Document Upload, AI Extraction, and Specification Approval Endpoints.
"""
import uuid
import shutil
import json
from pathlib import Path
from typing import List, Optional
from datetime import datetime, timezone, timedelta
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form
from fastapi.responses import FileResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete, delete
from sqlalchemy.orm import selectinload

from backend.app.core.database import get_db
from backend.app.core.config import settings
from backend.app.core.security import hash_password
from backend.app.models.user import User, UserRole
from backend.app.models.task import (
    Task, TaskVersion, TaskDocument, Requirement, AcceptanceCriterion,
    RubricItem, TaskStatus
)
from backend.app.models.meeting import Meeting, MeetingType, MeetingStatus, MeetingAttempt, Transcript, Recording
from backend.app.models.review import Submission, ReviewRound, EvaluationResult, RevisionRequest, Question
from backend.app.models.notification import Notification
from backend.app.models.audit import AuditLog
from backend.app.services.email_service import EmailService
from backend.app.schemas.task import (
    TaskCreateRequest, TaskResponse, TaskSpecificationDraft,
    ApproveSpecificationRequest, TaskVersionResponse, TaskUpdateRequest,
    VoiceChatRequest, VoiceChatResponse, SynthesizeSpeechRequest
)
from backend.app.services.task_intelligence import TaskIntelligenceService
from backend.app.services.scheduling import SchedulingService
from backend.app.services.excel_task_parser import ExcelTaskParser
from backend.app.api.deps import get_current_user, require_roles

router = APIRouter(prefix="/tasks", tags=["Tasks"])

@router.post("/", response_model=TaskResponse, status_code=status.HTTP_201_CREATED)
async def create_task(
    request: TaskCreateRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles([UserRole.ASSIGNER, UserRole.ADMIN]))
):
    task = Task(
        title=request.title,
        status=TaskStatus.DRAFT,
        assigner_id=current_user.id,
        intern_id=request.intern_id
    )
    db.add(task)
    await db.flush()

    if request.deadline_iso:
        deadline_utc = SchedulingService.parse_to_utc(request.deadline_iso, request.display_timezone or "Asia/Kolkata")
        initial_version = TaskVersion(
            task_id=task.id,
            version_number=1,
            objective=f"Complete requirements for {task.title}",
            scope=f"Implementation scope for {task.title}",
            deliverables="Clean working code, tests, and documentation.",
            submission_method="GitHub Repository & Test Reports",
            deadline_utc=deadline_utc,
            display_timezone=request.display_timezone or "Asia/Kolkata",
            is_approved=True,
            approved_by=current_user.id,
            approved_at=datetime.now(timezone.utc),
            changelog="Initial task created with assigned deadline."
        )
        db.add(initial_version)
        await db.flush()
        task.current_version_id = initial_version.id
        task.status = TaskStatus.SPECIFICATION_APPROVED

    await db.commit()
    await db.refresh(task)

    audit = AuditLog(
        actor_id=current_user.id,
        actor_email=current_user.email,
        action="TASK_CREATED",
        resource_type="task",
        resource_id=task.id,
        details_json=json.dumps({"has_deadline": bool(request.deadline_iso)})
    )
    db.add(audit)
    await db.commit()

    return await get_task(task.id, db, current_user)

@router.get("/", response_model=List[TaskResponse])
async def list_tasks(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    query = select(Task).options(
        selectinload(Task.documents),
        selectinload(Task.versions).selectinload(TaskVersion.requirements).selectinload(Requirement.acceptance_criteria),
        selectinload(Task.versions).selectinload(TaskVersion.rubric_items),
        selectinload(Task.meetings),
        selectinload(Task.submissions).selectinload(Submission.review_rounds).selectinload(ReviewRound.evaluation_results),
        selectinload(Task.submissions).selectinload(Submission.review_rounds).selectinload(ReviewRound.revision_requests),
        selectinload(Task.submissions).selectinload(Submission.review_rounds).selectinload(ReviewRound.questions)
    )
    if current_user.role == UserRole.INTERN:
        query = query.where(Task.intern_id == current_user.id)
    elif current_user.role == UserRole.ASSIGNER:
        query = query.where(Task.assigner_id == current_user.id)

    result = await db.execute(query)
    return result.scalars().all()


@router.delete("/{task_id}")
async def delete_task(
    task_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles([UserRole.ASSIGNER, UserRole.ADMIN]))
):
    """
    Permanently deletes a task and all associated meetings, transcripts, documents,
    versions, requirements, rubrics, submissions, and notifications.
    """
    res = await db.execute(select(Task).where(Task.id == task_id))
    task = res.scalars().first()
    if not task:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found")

    task_title = task.title

    # 1. Clean up Submissions & Review Rounds
    subs_res = await db.execute(select(Submission).where(Submission.task_id == task_id))
    submissions = subs_res.scalars().all()
    for sub in submissions:
        rounds_res = await db.execute(select(ReviewRound).where(ReviewRound.submission_id == sub.id))
        rounds = rounds_res.scalars().all()
        for r in rounds:
            await db.execute(delete(EvaluationResult).where(EvaluationResult.review_round_id == r.id))
            await db.execute(delete(RevisionRequest).where(RevisionRequest.review_round_id == r.id))
            await db.execute(delete(Question).where(Question.review_round_id == r.id))
            await db.delete(r)
        await db.delete(sub)

    # 2. Clean up Meetings, Attempts, Transcripts, Recordings
    m_res = await db.execute(select(Meeting).where(Meeting.task_id == task_id))
    meetings = m_res.scalars().all()
    for m in meetings:
        await db.execute(delete(MeetingAttempt).where(MeetingAttempt.meeting_id == m.id))
        await db.execute(delete(Transcript).where(Transcript.meeting_id == m.id))
        await db.execute(delete(Recording).where(Recording.meeting_id == m.id))
        await db.delete(m)

    # 3. Clean up Task Versions, Requirements, Rubrics, Acceptance Criteria
    v_res = await db.execute(select(TaskVersion).where(TaskVersion.task_id == task_id))
    versions = v_res.scalars().all()
    for v in versions:
        await db.execute(delete(RubricItem).where(RubricItem.task_version_id == v.id))
        reqs_res = await db.execute(select(Requirement).where(Requirement.task_version_id == v.id))
        reqs = reqs_res.scalars().all()
        for req in reqs:
            await db.execute(delete(AcceptanceCriterion).where(AcceptanceCriterion.requirement_id == req.id))
            await db.delete(req)
        await db.delete(v)

    # 4. Clean up Documents & storage files on disk
    doc_res = await db.execute(select(TaskDocument).where(TaskDocument.task_id == task_id))
    docs = doc_res.scalars().all()
    for d in docs:
        await db.delete(d)

    task_dir = Path(settings.UPLOAD_STORAGE_PATH) / task_id
    if task_dir.exists():
        try:
            shutil.rmtree(task_dir, ignore_errors=True)
        except Exception:
            pass

    # 5. Clean up Notifications
    await db.execute(delete(Notification).where(Notification.task_id == task_id))

    # 6. Delete Task itself
    await db.delete(task)
    await db.commit()

    # 7. Audit Log
    audit = AuditLog(
        actor_id=current_user.id,
        actor_email=current_user.email,
        action="TASK_DELETED",
        resource_type="task",
        resource_id=task_id,
        details_json=json.dumps({"title": task_title})
    )
    db.add(audit)
    await db.commit()

    return {
        "status": "success",
        "deleted_task_id": task_id,
        "title": task_title,
        "message": f"Task '{task_title}' and all associated records have been permanently deleted."
    }


@router.get("/excel-template")
async def download_excel_template(
    current_user: User = Depends(require_roles([UserRole.ASSIGNER, UserRole.ADMIN]))
):
    """Generates and serves a formatted Excel template for multi-task assignment."""
    template_dir = Path(settings.UPLOAD_STORAGE_PATH) / "templates"
    template_dir.mkdir(parents=True, exist_ok=True)
    template_path = template_dir / "Task_Assignment_Template.xlsx"
    ExcelTaskParser.generate_template(str(template_path))
    return FileResponse(
        path=str(template_path),
        filename="Task_Assignment_Template.xlsx",
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )

@router.get("/diagnostics/smtp")
async def test_smtp_diagnostic(
    current_user: User = Depends(require_roles([UserRole.ASSIGNER, UserRole.ADMIN]))
):
    """Checks SMTP connection and returns diagnostic configuration status."""
    return EmailService.test_smtp_connection()

@router.get("/{task_id}", response_model=TaskResponse)
async def get_task(
    task_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    query = select(Task).where(Task.id == task_id).options(
        selectinload(Task.documents),
        selectinload(Task.versions).selectinload(TaskVersion.requirements).selectinload(Requirement.acceptance_criteria),
        selectinload(Task.versions).selectinload(TaskVersion.rubric_items),
        selectinload(Task.meetings),
        selectinload(Task.submissions).selectinload(Submission.review_rounds).selectinload(ReviewRound.evaluation_results),
        selectinload(Task.submissions).selectinload(Submission.review_rounds).selectinload(ReviewRound.revision_requests),
        selectinload(Task.submissions).selectinload(Submission.review_rounds).selectinload(ReviewRound.questions)
    )
    result = await db.execute(query)
    task = result.scalars().first()
    if not task:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found")

    # Authorization check
    if current_user.role == UserRole.INTERN and task.intern_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied to this task")

    return task

@router.patch("/{task_id}", response_model=TaskResponse)
async def update_task(
    task_id: str,
    request: TaskUpdateRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles([UserRole.ASSIGNER, UserRole.ADMIN]))
):
    task = await get_task(task_id, db, current_user)
    if request.title is not None:
        task.title = request.title.strip()
    if request.deadline_iso is not None:
        if request.deadline_iso:
            deadline_utc = SchedulingService.parse_to_utc(request.deadline_iso, request.display_timezone or "Asia/Kolkata")
            if task.versions and len(task.versions) > 0:
                latest_ver = task.versions[-1]
                latest_ver.deadline_utc = deadline_utc
                latest_ver.display_timezone = request.display_timezone or "Asia/Kolkata"
            else:
                ver = TaskVersion(
                    task_id=task.id,
                    version_number=1,
                    objective=f"Complete requirements for {task.title}",
                    deadline_utc=deadline_utc,
                    display_timezone=request.display_timezone or "Asia/Kolkata",
                    is_approved=True,
                    approved_by=current_user.id,
                    approved_at=datetime.now(timezone.utc),
                    changelog="Assigned task deadline."
                )
                db.add(ver)
                await db.flush()
                task.current_version_id = ver.id
                task.status = TaskStatus.SPECIFICATION_APPROVED
    if request.intern_id is not None:
        if request.intern_id == "":
            task.intern_id = None
        else:
            i_res = await db.execute(select(User).where(User.id == request.intern_id))
            intern_obj = i_res.scalars().first()
            if not intern_obj:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Intern not found")
            task.intern_id = intern_obj.id

            # If task already has a scheduled briefing meeting, dispatch assignment email to newly assigned intern
            if task.meetings:
                briefing_meeting = next((m for m in task.meetings if m.meeting_type == MeetingType.BRIEFING), None)
                if briefing_meeting and briefing_meeting.google_meet_url:
                    current_version = task.versions[-1] if task.versions else None
                    deadline_str = "within 7 days"
                    if current_version and current_version.deadline_utc:
                        deadline_str = SchedulingService.format_to_local(
                            current_version.deadline_utc,
                            current_version.display_timezone or "Asia/Kolkata"
                        )
                    doc = task.documents[0] if (task.documents and len(task.documents) > 0) else None
                    doc_filename = doc.filename if doc else "Task_Specification.pdf"
                    doc_path = doc.file_path if (doc and doc.file_path and os.path.isfile(doc.file_path)) else None

                    try:
                        await EmailService.send_task_assignment_email(
                            db=db,
                            task_id=task.id,
                            to_email=intern_obj.email,
                            intern_name=intern_obj.full_name or "Intern",
                            task_title=task.title,
                            deadline_str=deadline_str,
                            meeting_url=briefing_meeting.google_meet_url,
                            doc_filename=doc_filename,
                            doc_path=doc_path,
                            task_objective=current_version.objective if current_version else None,
                            assigner_name=current_user.full_name or "Task Assigner (HR)"
                        )
                    except Exception as ex:
                        pass

    await db.commit()
    return await get_task(task_id, db, current_user)

@router.post("/{task_id}/upload")
async def upload_document(
    task_id: str,
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles([UserRole.ASSIGNER, UserRole.ADMIN]))
):
    # Verify task exists and is created by current user
    res = await db.execute(select(Task).where(Task.id == task_id))
    task = res.scalars().first()
    if not task:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found")

    # Validate file extension
    ext = Path(file.filename).suffix.lower()
    if ext not in [".pdf", ".docx", ".txt", ".md"]:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Unsupported file format. Please upload PDF, DOCX, or TXT.")

    # Save to storage
    upload_dir = Path(settings.UPLOAD_STORAGE_PATH) / task_id
    upload_dir.mkdir(parents=True, exist_ok=True)
    saved_filename = f"{uuid.uuid4().hex}_{file.filename}"
    saved_path = upload_dir / saved_filename

    with open(saved_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    # Extract text safely
    raw_text, sha256_hash, warnings = TaskIntelligenceService.extract_text_from_file(saved_path, file.filename)

    # Automatically run comprehensive document intelligence
    doc_analysis = await TaskIntelligenceService.analyze_document_comprehensively(raw_text, file.filename, task.title)
    analysis_json_str = json.dumps(doc_analysis)

    task_doc = TaskDocument(
        task_id=task.id,
        filename=file.filename,
        file_path=str(saved_path),
        file_size_bytes=saved_path.stat().st_size,
        mime_type=file.content_type or "application/octet-stream",
        file_hash_sha256=sha256_hash,
        extracted_raw_text=raw_text,
        extraction_warnings="; ".join(warnings) if warnings else None,
        analysis_json=analysis_json_str
    )
    db.add(task_doc)
    await db.flush()

    # Automatically generate & approve task specification version from the document
    draft = await TaskIntelligenceService.generate_specification_draft(raw_text, doc_analysis.get("title") or task.title)
    
    ver_res = await db.execute(select(TaskVersion).where(TaskVersion.task_id == task.id))
    existing_versions = ver_res.scalars().all()
    new_version_num = len(existing_versions) + 1
    existing_deadline_utc = next((v.deadline_utc for v in reversed(existing_versions) if v.deadline_utc), None)
    deadline_utc = existing_deadline_utc or SchedulingService.parse_to_utc(draft.deadline_iso, draft.display_timezone)

    version = TaskVersion(
        task_id=task.id,
        version_number=new_version_num,
        objective=draft.objective,
        scope=draft.scope,
        prerequisites=draft.prerequisites,
        deliverables=draft.deliverables,
        submission_method=draft.submission_method,
        deadline_utc=deadline_utc,
        display_timezone=draft.display_timezone,
        is_approved=True,
        approved_by=current_user.id,
        approved_at=datetime.now(timezone.utc),
        changelog=f"Document '{file.filename}' analyzed and ingested. Specification automatically created and approved."
    )
    db.add(version)
    await db.flush()

    # Save requirements & acceptance criteria & rubric items from document
    for r in draft.requirements:
        req = Requirement(
            task_version_id=version.id,
            req_code=r.req_code,
            title=r.title,
            description=r.description,
            priority=r.priority,
            is_mandatory=r.is_mandatory
        )
        db.add(req)
        await db.flush()

        for c in r.acceptance_criteria:
            ac = AcceptanceCriterion(
                requirement_id=req.id,
                criterion_code=c.criterion_code,
                description=c.description,
                verification_method=c.verification_method,
                pass_threshold=c.pass_threshold,
                is_mandatory=c.is_mandatory
            )
            db.add(ac)
            await db.flush()

            matching_rubric = next((rub for rub in draft.rubric if rub.criterion_code == c.criterion_code), None)
            rub = RubricItem(
                task_version_id=version.id,
                criterion_id=ac.id,
                name=matching_rubric.name if matching_rubric else f"Rubric for {c.criterion_code}",
                description=matching_rubric.description if matching_rubric else c.description,
                weight=matching_rubric.weight if matching_rubric else 1.0,
                max_score=matching_rubric.max_score if matching_rubric else 10.0,
                evaluation_guide=matching_rubric.evaluation_guide if matching_rubric else "Verify against threshold."
            )
            db.add(rub)

    # Update task title if default/generic
    if task.title in ["New Task", "Review", "AI Agentic Task Reviewer", "[DEMO] Enterprise Task Review Automation Engine"] and doc_analysis.get("title"):
        task.title = doc_analysis["title"][:250]

    task.status = TaskStatus.SPECIFICATION_APPROVED
    task.current_version_id = version.id
    await db.commit()
    await db.refresh(task_doc)

    audit = AuditLog(
        actor_id=current_user.id,
        actor_email=current_user.email,
        action="DOCUMENT_ANALYZED_AND_INGESTED",
        resource_type="task",
        resource_id=task.id,
        details_json=json.dumps({
            "filename": file.filename,
            "title": doc_analysis.get("title"),
            "findings_count": len(doc_analysis.get("findings", [])),
            "characters": len(raw_text)
        })
    )
    db.add(audit)
    await db.commit()

    return {
        "document_id": task_doc.id,
        "filename": task_doc.filename,
        "hash": sha256_hash,
        "characters_extracted": len(raw_text),
        "security_warnings": warnings,
        "analysis": doc_analysis,
        "message": f"Document '{file.filename}' analyzed and ingested. The AI Bot now fully understands the document and is prepared to explain it in Google Meet."
    }

@router.post("/{task_id}/extract-draft", response_model=TaskSpecificationDraft)
async def generate_draft_specification(
    task_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles([UserRole.ASSIGNER, UserRole.ADMIN]))
):
    res = await db.execute(select(Task).where(Task.id == task_id).options(selectinload(Task.documents)))
    task = res.scalars().first()
    if not task:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found")
    if not task.documents:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No document uploaded for this task")

    latest_doc = task.documents[-1]
    draft = await TaskIntelligenceService.generate_specification_draft(
        latest_doc.extracted_raw_text,
        task.title
    )
    return draft

@router.post("/{task_id}/approve-specification", response_model=TaskResponse)
async def approve_specification(
    task_id: str,
    draft: TaskSpecificationDraft,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles([UserRole.ASSIGNER, UserRole.ADMIN]))
):
    res = await db.execute(
        select(Task).where(Task.id == task_id).options(
            selectinload(Task.versions)
        )
    )
    task = res.scalars().first()
    if not task:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found")

    new_version_num = len(task.versions) + 1
    deadline_utc = SchedulingService.parse_to_utc(draft.deadline_iso, draft.display_timezone)

    version = TaskVersion(
        task_id=task.id,
        version_number=new_version_num,
        objective=draft.objective,
        scope=draft.scope,
        prerequisites=draft.prerequisites,
        deliverables=draft.deliverables,
        submission_method=draft.submission_method,
        deadline_utc=deadline_utc,
        display_timezone=draft.display_timezone,
        is_approved=True,
        approved_by=current_user.id,
        approved_at=datetime.now(timezone.utc),
        changelog=f"Specification approved by {current_user.full_name} ({current_user.email})."
    )
    db.add(version)
    await db.flush()

    # Save Requirements & Criteria
    for r in draft.requirements:
        req = Requirement(
            task_version_id=version.id,
            req_code=r.req_code,
            title=r.title,
            description=r.description,
            priority=r.priority,
            is_mandatory=r.is_mandatory
        )
        db.add(req)
        await db.flush()

        for c in r.acceptance_criteria:
            ac = AcceptanceCriterion(
                requirement_id=req.id,
                criterion_code=c.criterion_code,
                description=c.description,
                verification_method=c.verification_method,
                pass_threshold=c.pass_threshold,
                is_mandatory=c.is_mandatory
            )
            db.add(ac)
            await db.flush()

            # Create matching rubric item
            matching_rubric = next((rub for rub in draft.rubric if rub.criterion_code == c.criterion_code), None)
            rub = RubricItem(
                task_version_id=version.id,
                criterion_id=ac.id,
                name=matching_rubric.name if matching_rubric else f"Rubric for {c.criterion_code}",
                description=matching_rubric.description if matching_rubric else c.description,
                weight=matching_rubric.weight if matching_rubric else 1.0,
                max_score=matching_rubric.max_score if matching_rubric else 10.0,
                evaluation_guide=matching_rubric.evaluation_guide if matching_rubric else "Verify against threshold."
            )
            db.add(rub)

    task.status = TaskStatus.SPECIFICATION_APPROVED
    task.current_version_id = version.id
    await db.commit()

    # Audit log
    audit = AuditLog(
        actor_id=current_user.id,
        actor_email=current_user.email,
        action="SPECIFICATION_APPROVED",
        resource_type="task",
        resource_id=task.id,
        details_json=f'{{"version": {new_version_num}, "requirements_count": {len(draft.requirements)}}}'
    )
    db.add(audit)
    await db.commit()

    return await get_task(task.id, db, current_user)

@router.post("/{task_id}/voice-chat", response_model=VoiceChatResponse)
async def task_voice_chat(
    task_id: str,
    request: VoiceChatRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Interactive AI Voice Briefing & Review Assistant.
    Provides natural spoken conversational responses grounded in the task's approved specification.
    """
    res = await db.execute(
        select(Task).where(Task.id == task_id).options(
            selectinload(Task.versions).selectinload(TaskVersion.requirements).selectinload(Requirement.acceptance_criteria),
            selectinload(Task.versions).selectinload(TaskVersion.rubric_items),
            selectinload(Task.documents)
        )
    )
    task = res.scalars().first()
    if not task:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found")

    # Authorize: Intern assigned to this task or Assigner or Admin
    if current_user.role == UserRole.INTERN and task.intern_id and task.intern_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied to this task voice briefing")

    # Extract version details
    approved_ver = next((v for v in reversed(task.versions) if v.is_approved), None)
    latest_ver = task.versions[-1] if task.versions else None
    active_ver = approved_ver or latest_ver

    task_title = task.title
    objective = active_ver.objective if active_ver else "Review task requirements and deliverables"
    deliverables = active_ver.deliverables if active_ver else "Code repository with tests and documentation"
    
    # Format deadline nicely
    if active_ver and active_ver.deadline_utc:
        deadline_dt = active_ver.deadline_utc
        from zoneinfo import ZoneInfo
        try:
            tz = ZoneInfo(active_ver.display_timezone or "Asia/Kolkata")
            loc_dt = deadline_dt.astimezone(tz)
            deadline_str = loc_dt.strftime("%A, %B %d, %Y at %I:%M %p ") + (active_ver.display_timezone or "IST")
        except Exception:
            deadline_str = deadline_dt.strftime("%Y-%m-%d %H:%M UTC")
    else:
        deadline_str = "within 7 days of assignment in Asia/Kolkata timezone"

    reqs_str = ""
    if active_ver and active_ver.requirements:
        req_lines = []
        for r in active_ver.requirements:
            criteria_desc = ", ".join([ac.description for ac in r.acceptance_criteria]) if r.acceptance_criteria else ""
            req_lines.append(f"{r.req_code}: {r.title}. Criteria: {criteria_desc}")
        reqs_str = "; ".join(req_lines)
    else:
        reqs_str = "Code implementation passing all tests and clean repository delivery."

    rubric_str = ""
    if active_ver and active_ver.rubric_items:
        rubric_str = "; ".join([f"{rub.name} (weight {rub.weight}): {rub.description}" for rub in active_ver.rubric_items])
    else:
        rubric_str = "Deterministic test suite pass rate: 60%, Artifact quality & security: 40%."

    reply = await TaskIntelligenceService.generate_voice_response(
        task_title=task_title,
        objective=objective,
        deliverables=deliverables,
        deadline_str=deadline_str,
        requirements_summary=reqs_str,
        rubric_summary=rubric_str,
        user_message=request.message,
        session_type=request.session_type or "BRIEFING"
    )

    # Synthesize natural human speech with Cartesia Subha neural voice
    from backend.app.services.cartesia_tts import CartesiaTTSService
    audio_base64 = await CartesiaTTSService.synthesize_speech_base64(reply)

    return VoiceChatResponse(
        reply=reply,
        speaker=f"AI Reviewer ({settings.CARTESIA_VOICE_NAME.split()[0] if settings.CARTESIA_VOICE_NAME else 'Subha'})",
        task_title=task_title,
        session_type=request.session_type or "BRIEFING",
        audio_base64=audio_base64,
        voice_name=settings.CARTESIA_VOICE_NAME or "Subha (Indian English)"
    )

@router.post("/synthesize-speech")
async def synthesize_speech_direct(
    request: SynthesizeSpeechRequest,
    current_user: User = Depends(get_current_user)
):
    """Synthesizes text into high-fidelity Cartesia humanized voice audio."""
    from backend.app.services.cartesia_tts import CartesiaTTSService
    audio_b64 = await CartesiaTTSService.synthesize_speech_base64(request.text)
    if not audio_b64:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to synthesize speech")
    return {
        "audio_base64": audio_b64,
        "voice_name": settings.CARTESIA_VOICE_NAME or "Subha (Indian English)",
        "voice_id": settings.CARTESIA_VOICE_ID
    }

@router.post("/bulk-assign")
async def bulk_assign_tasks(
    file: UploadFile = File(...),
    intern_ids: str = Form(...),
    meeting_url: str = Form(...),
    custom_title: Optional[str] = Form(None),
    deadline_iso: Optional[str] = Form(None),
    timezone_str: str = Form("Asia/Kolkata"),
    scheduled_meeting_time_iso: Optional[str] = Form(None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles([UserRole.ASSIGNER, UserRole.ADMIN]))
):
    """
    Bulk assigns one common task document to multiple interns simultaneously.
    - Saves and analyzes the common document once.
    - Creates a Task, TaskDocument, approved TaskVersion (with requirements and rubrics) for each intern.
    - Schedules a common briefing Meeting with the provided Google Meet URL.
    - Sends an email to each intern via SMTP with the task details, document, and meeting URL.
    """
    # 1. Parse and validate intern_ids
    try:
        intern_id_list = json.loads(intern_ids)
        if not isinstance(intern_id_list, list) or len(intern_id_list) == 0:
            raise ValueError("intern_ids must be a non-empty list of UUIDs")
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid intern_ids parameter: {e}. Provide a valid JSON array of intern UUIDs."
        )

    # 2. Fetch all selected interns from database
    intern_query = await db.execute(
        select(User).where(User.id.in_(intern_id_list), User.role == UserRole.INTERN)
    )
    interns = intern_query.scalars().all()
    if len(interns) == 0:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="None of the specified interns could be found in the system."
        )

    # 3. Validate file extension
    ext = Path(file.filename).suffix.lower()
    if ext not in [".pdf", ".docx", ".txt", ".md"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Unsupported file format. Please upload PDF, DOCX, TXT, or MD."
        )

    # 4. Save master common document
    bulk_dir = Path(settings.UPLOAD_STORAGE_PATH) / "bulk_common"
    bulk_dir.mkdir(parents=True, exist_ok=True)
    master_file_name = f"{uuid.uuid4().hex}_{file.filename}"
    master_file_path = bulk_dir / master_file_name

    with open(master_file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    # 5. Extract text and run comprehensive document intelligence
    raw_text, sha256_hash, warnings = TaskIntelligenceService.extract_text_from_file(master_file_path, file.filename)
    doc_analysis = await TaskIntelligenceService.analyze_document_comprehensively(
        raw_text, file.filename, custom_title or "Common Task Specification"
    )
    analysis_json_str = json.dumps(doc_analysis)

    # 6. Generate specification draft
    draft = await TaskIntelligenceService.generate_specification_draft(
        raw_text, doc_analysis.get("title") or custom_title or "Common Task Specification"
    )

    # 7. Final task title
    final_title = (custom_title.strip() if custom_title and custom_title.strip() else None) or \
                  doc_analysis.get("title") or \
                  Path(file.filename).stem.replace("_", " ").title()

    # 8. Compute deadlines and meeting schedules
    now_utc = datetime.now(timezone.utc)
    target_deadline_iso = deadline_iso or draft.deadline_iso
    try:
        deadline_utc = SchedulingService.parse_to_utc(target_deadline_iso, timezone_str)
    except Exception:
        deadline_utc = now_utc + timedelta(days=7)

    deadline_formatted = SchedulingService.format_to_local(deadline_utc, timezone_str)

    if scheduled_meeting_time_iso:
        try:
            meeting_start_utc = SchedulingService.parse_to_utc(scheduled_meeting_time_iso, timezone_str)
        except Exception:
            meeting_start_utc = now_utc + timedelta(hours=2)
    else:
        meeting_start_utc = now_utc + timedelta(hours=2)

    meeting_end_utc = meeting_start_utc + timedelta(minutes=45)

    created_tasks = []
    email_dispatch_results = []

    # 9. Fan-out creation for each intern
    for intern_user in interns:
        task = Task(
            title=final_title,
            status=TaskStatus.BRIEFING_SCHEDULED,
            assigner_id=current_user.id,
            intern_id=intern_user.id
        )
        db.add(task)
        await db.flush()

        task_doc = TaskDocument(
            task_id=task.id,
            filename=file.filename,
            file_path=str(master_file_path),
            file_size_bytes=master_file_path.stat().st_size,
            mime_type=file.content_type or "application/octet-stream",
            file_hash_sha256=sha256_hash,
            extracted_raw_text=raw_text,
            extraction_warnings="; ".join(warnings) if warnings else None,
            analysis_json=analysis_json_str
        )
        db.add(task_doc)
        await db.flush()

        version = TaskVersion(
            task_id=task.id,
            version_number=1,
            objective=draft.objective,
            scope=draft.scope,
            prerequisites=draft.prerequisites,
            deliverables=draft.deliverables,
            submission_method=draft.submission_method,
            deadline_utc=deadline_utc,
            display_timezone=timezone_str,
            is_approved=True,
            approved_by=current_user.id,
            approved_at=now_utc,
            changelog=f"Bulk-assigned common brief '{file.filename}' by {current_user.full_name}."
        )
        db.add(version)
        await db.flush()
        task.current_version_id = version.id

        for r in draft.requirements:
            req = Requirement(
                task_version_id=version.id,
                req_code=r.req_code,
                title=r.title,
                description=r.description,
                priority=r.priority,
                is_mandatory=r.is_mandatory
            )
            db.add(req)
            await db.flush()

            for c in r.acceptance_criteria:
                ac = AcceptanceCriterion(
                    requirement_id=req.id,
                    criterion_code=c.criterion_code,
                    description=c.description,
                    verification_method=c.verification_method,
                    pass_threshold=c.pass_threshold,
                    is_mandatory=c.is_mandatory
                )
                db.add(ac)
                await db.flush()

                matching_rubric = next((rub for rub in draft.rubric if rub.criterion_code == c.criterion_code), None)
                rub = RubricItem(
                    task_version_id=version.id,
                    criterion_id=ac.id,
                    name=matching_rubric.name if matching_rubric else f"Rubric for {c.criterion_code}",
                    description=matching_rubric.description if matching_rubric else c.description,
                    weight=matching_rubric.weight if matching_rubric else 1.0,
                    max_score=matching_rubric.max_score if matching_rubric else 10.0,
                    evaluation_guide=matching_rubric.evaluation_guide if matching_rubric else None
                )
                db.add(rub)

        meeting = Meeting(
            task_id=task.id,
            meeting_type=MeetingType.BRIEFING,
            status=MeetingStatus.SCHEDULED,
            scheduled_start_utc=meeting_start_utc,
            scheduled_end_utc=meeting_end_utc,
            timezone=timezone_str,
            google_meet_url=meeting_url.strip(),
            is_dry_run=False
        )
        db.add(meeting)
        await db.flush()

        # Send SMTP notification email
        email_status = await EmailService.send_task_assignment_email(
            db=db,
            task_id=task.id,
            to_email=intern_user.email,
            intern_name=intern_user.full_name,
            task_title=final_title,
            deadline_str=deadline_formatted,
            meeting_url=meeting_url.strip(),
            doc_filename=file.filename,
            doc_path=str(master_file_path),
            task_objective=draft.objective,
            assigner_name=current_user.full_name
        )
        email_dispatch_results.append(email_status)

        created_tasks.append({
            "task_id": task.id,
            "intern_id": intern_user.id,
            "intern_name": intern_user.full_name,
            "intern_email": intern_user.email,
            "meeting_id": meeting.id,
            "email_status": email_status.get("mode") or ("SENT" if email_status.get("sent") else "FAILED")
        })

    audit = AuditLog(
        actor_id=current_user.id,
        actor_email=current_user.email,
        action="BULK_TASKS_ASSIGNED",
        resource_type="task",
        resource_id=created_tasks[0]["task_id"] if created_tasks else None
    )
    db.add(audit)
    await db.commit()

    return {
        "message": f"Successfully created {len(created_tasks)} task assignment(s) and dispatched notifications.",
        "task_title": final_title,
        "common_document": file.filename,
        "common_meeting_url": meeting_url.strip(),
        "deadline": deadline_formatted,
        "timezone": timezone_str,
        "assigned_count": len(created_tasks),
        "tasks": created_tasks,
        "email_dispatch_summary": email_dispatch_results
    }

@router.get("/diagnostics/smtp")
async def test_smtp_diagnostic(
    current_user: User = Depends(require_roles([UserRole.ASSIGNER, UserRole.ADMIN]))
):
    """Checks SMTP connection and returns diagnostic configuration status."""
    return EmailService.test_smtp_connection()

@router.get("/excel-template")
async def download_excel_template(
    current_user: User = Depends(require_roles([UserRole.ASSIGNER, UserRole.ADMIN]))
):
    """Generates and serves a formatted Excel template for multi-task assignment."""
    template_dir = Path(settings.UPLOAD_STORAGE_PATH) / "templates"
    template_dir.mkdir(parents=True, exist_ok=True)
    template_path = template_dir / "Task_Assignment_Template.xlsx"
    ExcelTaskParser.generate_template(str(template_path))
    return FileResponse(
        path=str(template_path),
        filename="Task_Assignment_Template.xlsx",
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )

@router.post("/excel-assign")
async def excel_assign_tasks(
    file: UploadFile = File(...),
    timezone_str: str = Form("Asia/Kolkata"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles([UserRole.ASSIGNER, UserRole.ADMIN]))
):
    """
    Parses an Excel spreadsheet or CSV file containing individual task assignments for multiple interns.
    Auto-provisions or matches intern accounts, generates unique Google Meet briefing links,
    and dispatches individual SMTP notification emails.
    """
    ext = Path(file.filename).suffix.lower()
    if ext not in [".xlsx", ".xls", ".csv"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Unsupported file format. Please upload an Excel (.xlsx/.xls) or CSV (.csv) file."
        )

    excel_dir = Path(settings.UPLOAD_STORAGE_PATH) / "excel_uploads"
    excel_dir.mkdir(parents=True, exist_ok=True)
    saved_filename = f"{uuid.uuid4().hex}_{file.filename}"
    saved_file_path = excel_dir / saved_filename

    content = await file.read()
    with open(saved_file_path, "wb") as f:
        f.write(content)

    try:
        if ext == ".csv":
            parsed_rows = ExcelTaskParser.parse_csv(content)
        else:
            parsed_rows = ExcelTaskParser.parse_xlsx(str(saved_file_path))
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to parse spreadsheet: {str(e)}"
        )

    if not parsed_rows:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No valid task assignment rows found in the uploaded file."
        )

    created_assignments = []
    now_utc = datetime.now(timezone.utc)

    for row in parsed_rows:
        intern_email = row["email"].lower().strip()
        intern_name = row["name"].strip()
        task_title = row["title"].strip()
        task_objective = row.get("objective", "").strip() or f"Complete assignment: {task_title}"

        # 1. Match or auto-provision intern user account
        user_res = await db.execute(select(User).where(User.email == intern_email))
        intern_user = user_res.scalars().first()

        if not intern_user:
            intern_user = User(
                email=intern_email,
                full_name=intern_name,
                role=UserRole.INTERN,
                hashed_password=hash_password("InternPass123!"),
                is_active=True
            )
            db.add(intern_user)
            await db.flush()

        # 2. Create individual Task
        task = Task(
            title=task_title,
            status=TaskStatus.BRIEFING_SCHEDULED,
            assigner_id=current_user.id,
            intern_id=intern_user.id
        )
        db.add(task)
        await db.flush()

        # 3. Compute deadlines & meeting times
        deadline_utc = SchedulingService.parse_to_utc(row.get("deadline"), timezone_str)
        meeting_start_utc = SchedulingService.parse_to_utc(row.get("meeting_time"), timezone_str)

        # 4. Generate unique meeting event and room link
        event_id, meet_url, conf_id, is_dry = await SchedulingService.create_meeting_event(
            task_id=task.id,
            meeting_type=MeetingType.BRIEFING,
            start_utc=meeting_start_utc,
            duration_minutes=30,
            display_tz=timezone_str,
            attendee_emails=[intern_user.email]
        )

        # 5. Create approved TaskVersion
        version = TaskVersion(
            task_id=task.id,
            version_number=1,
            objective=task_objective,
            scope=task_objective,
            deliverables="GitHub Repository & Live Screen Share Walkthrough",
            submission_method="GitHub Repository Link",
            deadline_utc=deadline_utc,
            display_timezone=timezone_str,
            is_approved=True,
            approved_by=current_user.id,
            approved_at=now_utc,
            changelog=f"Imported from Excel file '{file.filename}' by {current_user.full_name}."
        )
        db.add(version)
        await db.flush()
        task.current_version_id = version.id

        # 6. Create Meeting
        meeting = Meeting(
            task_id=task.id,
            meeting_type=MeetingType.BRIEFING,
            status=MeetingStatus.SCHEDULED,
            scheduled_start_utc=meeting_start_utc,
            scheduled_end_utc=meeting_start_utc + timedelta(minutes=30),
            timezone=timezone_str,
            google_meet_url=meet_url,
            google_event_id=event_id,
            conference_id=conf_id,
            meeting_round=1,
            is_dry_run=is_dry
        )
        db.add(meeting)
        await db.flush()

        # 7. Dispatch individual SMTP assignment email
        deadline_formatted = SchedulingService.format_to_local(deadline_utc, timezone_str)
        email_status = await EmailService.send_task_assignment_email(
            db=db,
            task_id=task.id,
            to_email=intern_user.email,
            intern_name=intern_user.full_name,
            task_title=task_title,
            deadline_str=deadline_formatted,
            meeting_url=meet_url,
            doc_filename=file.filename,
            doc_path=str(saved_file_path),
            task_objective=task_objective,
            assigner_name=current_user.full_name
        )

        created_assignments.append({
            "task_id": task.id,
            "intern_id": intern_user.id,
            "intern_name": intern_user.full_name,
            "intern_email": intern_user.email,
            "task_title": task_title,
            "meeting_id": meeting.id,
            "meeting_url": meet_url,
            "deadline": deadline_formatted,
            "email_status": email_status.get("mode") or ("SENT" if email_status.get("sent") else "FAILED")
        })

    audit = AuditLog(
        actor_id=current_user.id,
        actor_email=current_user.email,
        action="EXCEL_TASKS_BULK_ASSIGNED",
        resource_type="task",
        resource_id=created_assignments[0]["task_id"] if created_assignments else None,
        details_json=json.dumps({"count": len(created_assignments), "source_file": file.filename})
    )
    db.add(audit)
    await db.commit()

    return {
        "message": f"Successfully parsed {len(created_assignments)} task assignment(s) and dispatched notifications.",
        "source_file": file.filename,
        "assigned_count": len(created_assignments),
        "assignments": created_assignments
    }



