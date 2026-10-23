"""
Revision Loop and Task Lifecycle State Machine.
Enforces max review round policies, schedules subsequent reviews,
and guarantees deterministic task state transitions.
"""
import logging
from datetime import datetime, timezone, timedelta
from typing import Optional, Tuple
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from backend.app.core.config import settings
from backend.app.models.task import Task, TaskStatus
from backend.app.models.review import ReviewRound, EvaluationOutcome, RoundStatus
from backend.app.models.meeting import MeetingType
from backend.app.services.scheduling import SchedulingService
from backend.app.models.meeting import Meeting, MeetingStatus

logger = logging.getLogger(__name__)

class RevisionLoopService:
    @classmethod
    async def process_round_completion(
        cls,
        db: AsyncSession,
        task: Task,
        current_round: ReviewRound,
        outcome: EvaluationOutcome,
        score: float,
        summary: str
    ) -> TaskStatus:
        """
        Transitions review round and task according to deterministic policy rules.
        """
        current_round.outcome = outcome
        current_round.total_score = score
        current_round.summary_notes = summary
        current_round.status = RoundStatus.COMPLETED
        current_round.completed_at = datetime.now(timezone.utc)

        if outcome == EvaluationOutcome.PASS:
            task.status = TaskStatus.PASSED
            logger.info(f"[LIFECYCLE] Task {task.id} PASSED on round {current_round.round_number}")
            await db.commit()
            return task.status

        if outcome == EvaluationOutcome.HUMAN_REVIEW_REQUIRED:
            task.status = TaskStatus.HUMAN_REVIEW_REQUIRED
            logger.info(f"[LIFECYCLE] Task {task.id} requires human assigner intervention.")
            await db.commit()
            return task.status

        # If REVISION_REQUIRED
        if current_round.round_number >= settings.MAX_REVISION_ROUNDS:
            task.status = TaskStatus.ESCALATED
            logger.warning(
                f"[LIFECYCLE] Task {task.id} exceeded maximum allowed revision rounds "
                f"({settings.MAX_REVISION_ROUNDS}). Escalating to human assigner."
            )
            await db.commit()
            return task.status

        # Schedule next review round
        task.status = TaskStatus.REVISION_REQUIRED
        next_round_number = current_round.round_number + 1
        next_review_time = datetime.now(timezone.utc) + timedelta(days=3)

        # Create scheduled review meeting
        evt_id, meet_url, conf_id, is_dry = await SchedulingService.create_meeting_event(
            task_id=task.id,
            meeting_type=MeetingType.REVIEW,
            start_utc=next_review_time,
            duration_minutes=30,
            display_tz=settings.DEFAULT_TIMEZONE
        )

        next_meeting = Meeting(
            task_id=task.id,
            meeting_type=MeetingType.REVIEW,
            status=MeetingStatus.SCHEDULED,
            scheduled_start_utc=next_review_time,
            scheduled_end_utc=next_review_time + timedelta(minutes=30),
            timezone=settings.DEFAULT_TIMEZONE,
            google_event_id=evt_id,
            google_meet_url=meet_url,
            conference_id=conf_id,
            is_dry_run=is_dry
        )
        db.add(next_meeting)

        # Create placeholder for next review round
        new_round = ReviewRound(
            task_id=task.id,
            round_number=next_round_number,
            status=RoundStatus.PENDING
        )
        db.add(new_round)

        await db.commit()
        logger.info(f"[LIFECYCLE] Task {task.id} revision round {next_round_number} scheduled at {meet_url}")
        return task.status
