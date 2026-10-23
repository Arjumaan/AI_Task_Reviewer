"""
Base Model Classes and Mixins.
Provides UUID primary keys and UTC timestamps.
"""
import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, DateTime
from backend.app.core.database import Base

def generate_uuid() -> str:
    return str(uuid.uuid4())

def get_utc_now() -> datetime:
    return datetime.now(timezone.utc)

class TimestampMixin:
    created_at = Column(DateTime(timezone=True), default=get_utc_now, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=get_utc_now, onupdate=get_utc_now, nullable=False)

class UUIDPrimaryKeyMixin:
    id = Column(String(36), primary_key=True, default=generate_uuid, index=True)
