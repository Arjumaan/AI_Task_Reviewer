"""
Notification and Email Delivery Schemas.
"""
from datetime import datetime
from typing import Optional
from pydantic import BaseModel
from backend.app.models.notification import (
    NotificationType, NotificationStatus, DeliveryProvider
)

class NotificationResponse(BaseModel):
    id: str
    task_id: Optional[str]
    recipient_email: str
    recipient_role: str
    notification_type: NotificationType
    subject: str
    body_text: str
    status: NotificationStatus
    delivery_provider: DeliveryProvider
    external_message_id: Optional[str]
    attempts: int
    error_message: Optional[str]
    sent_at: Optional[datetime]
    created_at: datetime

    class Config:
        from_attributes = True
