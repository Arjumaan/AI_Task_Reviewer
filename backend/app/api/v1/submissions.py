"""
Task Submission Endpoints for Interns.
"""
from datetime import datetime, timezone
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from backend.app.core.database import get_db
from backend.app.models.user import User, UserRole
from backend.app.models.task import Task, TaskStatus
from backend.app.models.review import Submission, ReviewRound, RoundStatus
from backend.app.models.audit import AuditLog
from backend.app.schemas.review import SubmissionCreateRequest, SubmissionResponse
from backend.app.api.deps import get_current_user

router = APIRouter(prefix="/submissions", tags=["Submissions"])

@router.post("/", response_model=SubmissionResponse, status_code=status.HTTP_201_CREATED)
async def submit_deliverables(
    req: SubmissionCreateRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    res = await db.execute(select(Task).where(Task.id == req.task_id).options(selectinload(Task.submissions)))
    task = res.scalars().first()
    if not task:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found")

    round_num = len(task.submissions) + 1
    submission = Submission(
        task_id=task.id,
        intern_id=current_user.id,
        round_number=round_num,
        repository_url=req.repository_url,
        commit_hash=req.commit_hash,
        notes=req.notes,
        submitted_at=datetime.now(timezone.utc)
    )
    db.add(submission)
    await db.flush()

    # Create associated ReviewRound
    review_round = ReviewRound(
        task_id=task.id,
        submission_id=submission.id,
        round_number=round_num,
        status=RoundStatus.PENDING
    )
    db.add(review_round)

    task.status = TaskStatus.UNDER_REVIEW
    await db.commit()

    res = await db.execute(
        select(Submission)
        .where(Submission.id == submission.id)
        .options(
            selectinload(Submission.review_rounds).selectinload(ReviewRound.evaluation_results),
            selectinload(Submission.review_rounds).selectinload(ReviewRound.revision_requests),
            selectinload(Submission.review_rounds).selectinload(ReviewRound.questions)
        )
    )
    loaded_sub = res.scalars().first()

    audit = AuditLog(
        actor_id=current_user.id,
        actor_email=current_user.email,
        action="SUBMISSION_RECEIVED",
        resource_type="submission",
        resource_id=submission.id,
        details_json=f'{{"round": {round_num}, "repo": "{req.repository_url}"}}'
    )
    db.add(audit)
    await db.commit()

    return loaded_sub

@router.get("/task/{task_id}", response_model=List[SubmissionResponse])
async def list_task_submissions(
    task_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    res = await db.execute(
        select(Submission)
        .where(Submission.task_id == task_id)
        .options(selectinload(Submission.review_rounds))
    )
    return res.scalars().all()
