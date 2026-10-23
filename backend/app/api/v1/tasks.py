"""
Task Lifecycle, Document Upload, AI Extraction, and Specification Approval Endpoints.
"""
import uuid
import shutil
from pathlib import Path
from typing import List, Optional
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from backend.app.core.database import get_db
from backend.app.core.config import settings
from backend.app.models.user import User, UserRole
from backend.app.models.task import (
    Task, TaskVersion, TaskDocument, Requirement, AcceptanceCriterion,
    RubricItem, TaskStatus
)
from backend.app.models.meeting import Meeting
from backend.app.models.review import Submission, ReviewRound
from backend.app.models.audit import AuditLog
from backend.app.schemas.task import (
    TaskCreateRequest, TaskResponse, TaskSpecificationDraft,
    ApproveSpecificationRequest, TaskVersionResponse, TaskUpdateRequest,
    VoiceChatRequest, VoiceChatResponse, SynthesizeSpeechRequest
)
from backend.app.services.task_intelligence import TaskIntelligenceService
from backend.app.services.scheduling import SchedulingService
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
    await db.commit()
    await db.refresh(task)

    audit = AuditLog(
        actor_id=current_user.id,
        actor_email=current_user.email,
        action="TASK_CREATED",
        resource_type="task",
        resource_id=task.id
    )
    db.add(audit)
    await db.commit()

    return task

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
    if request.intern_id is not None:
        if request.intern_id == "":
            task.intern_id = None
        else:
            i_res = await db.execute(select(User).where(User.id == request.intern_id))
            intern_obj = i_res.scalars().first()
            if not intern_obj:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Intern not found")
            task.intern_id = intern_obj.id

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

    task_doc = TaskDocument(
        task_id=task.id,
        filename=file.filename,
        file_path=str(saved_path),
        file_size_bytes=saved_path.stat().st_size,
        mime_type=file.content_type or "application/octet-stream",
        file_hash_sha256=sha256_hash,
        extracted_raw_text=raw_text,
        extraction_warnings="; ".join(warnings) if warnings else None
    )
    db.add(task_doc)
    await db.commit()
    await db.refresh(task_doc)

    return {
        "document_id": task_doc.id,
        "filename": task_doc.filename,
        "hash": sha256_hash,
        "characters_extracted": len(raw_text),
        "security_warnings": warnings
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

