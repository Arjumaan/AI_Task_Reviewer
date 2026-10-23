"""
Review Rounds, Evidence-Based Evaluation, and Appeal Endpoints.
"""
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from backend.app.core.database import get_db
from backend.app.models.user import User, UserRole
from backend.app.models.task import Task, TaskStatus
from backend.app.models.review import (
    ReviewRound, EvaluationResult, RevisionRequest, RoundStatus, EvaluationOutcome
)
from backend.app.models.audit import AuditLog
from backend.app.schemas.review import (
    ReviewRoundResponse, AppealRequest
)
from backend.app.services.evaluation_engine import EvaluationEngine
from backend.app.services.revision_loop import RevisionLoopService
from backend.app.api.deps import get_current_user, require_roles

router = APIRouter(prefix="/reviews", tags=["Reviews"])

class RunEvaluationRequest(BaseModel):
    test_output: Optional[str] = "pytest: 12 passed in 0.45s (100% pass)"
    repo_url: Optional[str] = "https://github.com/intern/project"
    meeting_transcripts: List[str] = []

@router.post("/{round_id}/evaluate", response_model=ReviewRoundResponse)
async def evaluate_review_round(
    round_id: str,
    req: RunEvaluationRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles([UserRole.ASSIGNER, UserRole.ADMIN]))
):
    res = await db.execute(
        select(ReviewRound).where(ReviewRound.id == round_id).options(
            selectinload(ReviewRound.task),
            selectinload(ReviewRound.evaluation_results),
            selectinload(ReviewRound.revision_requests),
            selectinload(ReviewRound.questions)
        )
    )
    review_round = res.scalars().first()
    if not review_round:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Review round not found")

    task = review_round.task
    artifacts = {
        "test_output": req.test_output,
        "repo_url": req.repo_url
    }

    outcome, score, eval_results, revisions = await EvaluationEngine.evaluate_round(
        db=db,
        review_round=review_round,
        submitted_artifacts=artifacts,
        transcripts=req.meeting_transcripts
    )

    for er in eval_results:
        db.add(er)
    for rev in revisions:
        db.add(rev)

    # Process lifecycle transitions through deterministic revision loop service
    await RevisionLoopService.process_round_completion(
        db=db,
        task=task,
        current_round=review_round,
        outcome=outcome,
        score=score,
        summary=f"Evaluation complete. Outcome: {outcome.value}. Score: {score:.1f}%."
    )

    audit = AuditLog(
        actor_id=current_user.id,
        actor_email=current_user.email,
        action="EVALUATION_COMPLETED",
        resource_type="review_round",
        resource_id=review_round.id,
        details_json=f'{{"outcome": "{outcome.value}", "score": {score:.1f}}}'
    )
    db.add(audit)
    await db.commit()
    db.expire_all()

    return await get_review_round(round_id, db, current_user)

@router.get("/{round_id}", response_model=ReviewRoundResponse)
async def get_review_round(
    round_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    res = await db.execute(
        select(ReviewRound).where(ReviewRound.id == round_id).options(
            selectinload(ReviewRound.evaluation_results),
            selectinload(ReviewRound.revision_requests),
            selectinload(ReviewRound.questions)
        )
    )
    round_obj = res.scalars().first()
    if not round_obj:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Review round not found")
    return round_obj

@router.post("/{round_id}/appeal", response_model=ReviewRoundResponse)
async def submit_appeal(
    round_id: str,
    req: AppealRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    res = await db.execute(
        select(ReviewRound).where(ReviewRound.id == round_id).options(
            selectinload(ReviewRound.task)
        )
    )
    round_obj = res.scalars().first()
    if not round_obj:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Review round not found")

    round_obj.appeal_requested = True
    round_obj.appeal_reason = req.reason
    round_obj.outcome = EvaluationOutcome.HUMAN_REVIEW_REQUIRED
    round_obj.task.status = TaskStatus.HUMAN_REVIEW_REQUIRED

    audit = AuditLog(
        actor_id=current_user.id,
        actor_email=current_user.email,
        action="EVALUATION_APPEALED",
        resource_type="review_round",
        resource_id=round_obj.id,
        details_json=f'{{"appeal_reason": "{req.reason}"}}'
    )
    db.add(audit)
    await db.commit()

    return await get_review_round(round_id, db, current_user)

@router.get("/task/{task_id}/rounds", response_model=List[ReviewRoundResponse])
async def list_task_rounds(
    task_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    res = await db.execute(
        select(ReviewRound).where(ReviewRound.task_id == task_id).options(
            selectinload(ReviewRound.evaluation_results),
            selectinload(ReviewRound.revision_requests),
            selectinload(ReviewRound.questions)
        ).order_by(ReviewRound.round_number)
    )
    return res.scalars().all()
