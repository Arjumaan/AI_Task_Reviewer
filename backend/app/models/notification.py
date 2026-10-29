"""
Notifications and Email Delivery Audit Models.
"""
import enum
from sqlalchemy import Column, String, Text, Integer, Enum, ForeignKey, DateTime
from backend.app.core.database import Base
from backend.app.models.base import UUIDPrimaryKeyMixin, TimestampMixin

class NotificationType(str, enum.Enum):
    TASK_ASSIGNED = "TASK_ASSIGNED"
    BRIEFING_SUMMARY = "BRIEFING_SUMMARY"
    REVIEW_FEEDBACK = "REVIEW_FEEDBACK"
    REVISION_REQUEST = "REVISION_REQUEST"
    TASK_PASSED = "TASK_PASSED"
    MEETING_REMINDER = "MEETING_REMINDER"

class NotificationStatus(str, enum.Enum):
    PENDING = "PENDING"
    SENT = "SENT"
    FAILED = "FAILED"
    DRY_RUN = "DRY_RUN"

class DeliveryProvider(str, enum.Enum):
    SMTP = "SMTP"
    GMAIL_API = "GMAIL_API"
    DRY_RUN_CONSOLE = "DRY_RUN_CONSOLE"

class Notification(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "notifications"

    task_id = Column(String(36), ForeignKey("tasks.id", ondelete="CASCADE"), nullable=True, index=True)
    recipient_email = Column(String(255), nullable=False)
    recipient_role = Column(String(64), nullable=False)
    notification_type = Column(Enum(NotificationType), nullable=False, index=True)
    subject = Column(String(255), nullable=False)
    body_text = Column(Text, nullable=False)
    body_html = Column(Text, nullable=True)
    status = Column(Enum(NotificationStatus), default=NotificationStatus.PENDING, nullable=False, index=True)
    delivery_provider = Column(Enum(DeliveryProvider), default=DeliveryProvider.DRY_RUN_CONSOLE, nullable=False)
    external_message_id = Column(String(255), nullable=True)
    attempts = Column(Integer, default=0, nullable=False)
    error_message = Column(Text, nullable=True)
    sent_at = Column(DateTime(timezone=True), nullable=True)
