"""
Recording Access Control and Retention Management Endpoints.
"""
from datetime import datetime, timezone
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from backend.app.core.database import get_db
from backend.app.models.user import User, UserRole
from backend.app.models.meeting import Recording, Meeting
from backend.app.models.audit import AuditLog
from backend.app.schemas.meeting import RecordingResponse
from backend.app.api.deps import get_current_user, require_roles

router = APIRouter(prefix="/recordings", tags=["Recordings"])

@router.get("/meeting/{meeting_id}", response_model=List[RecordingResponse])
async def get_meeting_recordings(
    meeting_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    res = await db.execute(
        select(Recording).where(Recording.meeting_id == meeting_id, Recording.is_deleted == False)
    )
    return res.scalars().all()

@router.delete("/{recording_id}")
async def delete_recording(
    recording_id: str,
    reason: str = "Retention period expired or user deletion request",
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles([UserRole.ADMIN]))
):
    res = await db.execute(select(Recording).where(Recording.id == recording_id))
    rec = res.scalars().first()
    if not rec:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Recording not found")

    rec.is_deleted = True
    rec.deleted_at = datetime.now(timezone.utc)
    rec.deletion_reason = reason

    audit = AuditLog(
        actor_id=current_user.id,
        actor_email=current_user.email,
        action="RECORDING_DELETED",
        resource_type="recording",
        resource_id=rec.id,
        details_json=f'{{"reason": "{reason}"}}'
    )
    db.add(audit)
    await db.commit()

    return {"status": "ok", "message": f"Recording {recording_id} marked deleted with audit log."}
