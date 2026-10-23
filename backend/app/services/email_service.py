"""
Email Notification Service.
Generates transcript-grounded briefing summaries and evaluation emails.
Supports Gmail API delivery with dry-run/console audit fallback.
"""
import base64
import logging
from datetime import datetime, timezone
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Optional, List, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from backend.app.core.config import settings
from backend.app.models.notification import (
    Notification, NotificationType, NotificationStatus, DeliveryProvider
)

logger = logging.getLogger(__name__)

class EmailService:
    @classmethod
    async def send_briefing_summary_email(
        cls,
        db: AsyncSession,
        task_id: str,
        recipient_email: str,
        task_title: str,
        objective: str,
        requirements: List[Dict[str, Any]],
        deliverables: str,
        deadline_str: str,
        timezone_str: str,
        review_meeting_url: str,
        review_meeting_time_str: str,
        transcripts: List[str],
        unresolved_questions: List[str]
    ) -> Notification:
        """
        Constructs and dispatches transcript-grounded briefing summary email.
        """
        # Idempotency check: Don't send duplicate briefing email for same task & recipient
        existing = await db.execute(
            select(Notification).where(
                Notification.task_id == task_id,
                Notification.recipient_email == recipient_email,
                Notification.notification_type == NotificationType.BRIEFING_SUMMARY,
                Notification.status.in_([NotificationStatus.SENT, NotificationStatus.DRY_RUN])
            )
        )
        if existing.scalars().first():
            logger.info(f"[EMAIL] Briefing email already delivered to {recipient_email} for task {task_id}. Skipping.")
            return existing.scalars().first()

        subject = f"[Task Briefing Summary] {task_title} — Deliverables & Schedule"

        req_text = "\n".join([f"- [{r.get('req_code', 'REQ')}] {r.get('title', '')}: {r.get('description', '')}" for r in requirements])
        unresolved_text = "\n".join([f"- {q}" for q in unresolved_questions]) if unresolved_questions else "None recorded."
        transcript_snippet = "\n".join([f"> {t}" for t in transcripts[-6:]]) if transcripts else "Audio briefing completed."

        body_text = f"""Hello,

This is the automated briefing summary from the Task Reviewer AI for assignment: "{task_title}".

1. OBJECTIVE:
{objective}

2. REQUIREMENTS:
{req_text}

3. DELIVERABLES:
{deliverables}

4. DEADLINE:
{deadline_str} ({timezone_str})

5. UNRESOLVED QUESTIONS / ASSIGNER ESCALATIONS:
{unresolved_text}

6. NEXT REVIEW MEETING:
Scheduled for: {review_meeting_time_str} ({timezone_str})
Meeting Link: {review_meeting_url}

7. BRIEFING TRANSCRIPT EXCERPT:
{transcript_snippet}

Please reply to this email or contact your task assigner if you have any questions before the submission deadline.

Best regards,
Task Reviewer AI (Autonomous System)
"""

        body_html = f"""
        <div style="font-family: Arial, sans-serif; line-height: 1.6; color: #1e293b; max-width: 600px; margin: 0 auto; border: 1px solid #e2e8f0; border-radius: 8px; padding: 24px;">
            <h2 style="color: #4f46e5; margin-top: 0;">Task Briefing Summary</h2>
            <p><strong>Assignment:</strong> {task_title}</p>
            <hr style="border: 0; border-top: 1px solid #e2e8f0;" />
            <h3>Objective</h3>
            <p>{objective}</p>
            <h3>Requirements</h3>
            <pre style="background: #f8fafc; padding: 12px; border-radius: 6px; font-size: 13px;">{req_text}</pre>
            <h3>Deadline</h3>
            <p style="color: #b91c1c; font-weight: bold;">{deadline_str} ({timezone_str})</p>
            <h3>Next Review Session</h3>
            <p><strong>Time:</strong> {review_meeting_time_str} ({timezone_str})<br>
            <strong>Verified Meeting Link:</strong> <a href="{review_meeting_url}">{review_meeting_url}</a></p>
            <hr style="border: 0; border-top: 1px solid #e2e8f0;" />
            <p style="font-size: 11px; color: #64748b;">Notice: This message was generated automatically by the Task Reviewer AI following your briefing session.</p>
        </div>
        """

        notification = Notification(
            task_id=task_id,
            recipient_email=recipient_email,
            recipient_role="INTERN",
            notification_type=NotificationType.BRIEFING_SUMMARY,
            subject=subject,
            body_text=body_text,
            body_html=body_html,
            status=NotificationStatus.PENDING,
            delivery_provider=DeliveryProvider.DRY_RUN_CONSOLE if settings.GOOGLE_DRY_RUN else DeliveryProvider.GMAIL_API
        )
        db.add(notification)
        await db.commit()
        await db.refresh(notification)

        # Dispatch
        await cls._dispatch_email(db, notification)
        return notification

    @classmethod
    async def _dispatch_email(cls, db: AsyncSession, notification: Notification):
        """Dispatches notification via Gmail API or dry-run logger."""
        if settings.GOOGLE_DRY_RUN or not settings.GOOGLE_CLIENT_ID:
            logger.info(
                f"[EMAIL DRY-RUN] Message to {notification.recipient_email} logged to console.\n"
                f"Subject: {notification.subject}\n"
                f"Body Preview:\n{notification.body_text[:200]}..."
            )
            notification.status = NotificationStatus.DRY_RUN
            notification.sent_at = datetime.now(timezone.utc)
            notification.attempts += 1
            await db.commit()
            return

        # Real Gmail API Dispatch
        try:
            from google.oauth2.credentials import Credentials
            from googleapiclient.discovery import build

            creds = Credentials(
                token=None,
                refresh_token=settings.GOOGLE_REFRESH_TOKEN,
                token_uri="https://oauth2.googleapis.com/token",
                client_id=settings.GOOGLE_CLIENT_ID,
                client_secret=settings.GOOGLE_CLIENT_SECRET,
                scopes=["https://www.googleapis.com/auth/gmail.send"]
            )
            service = build("gmail", "v1", credentials=creds)

            msg = MIMEMultipart("alternative")
            msg["Subject"] = notification.subject
            msg["To"] = notification.recipient_email
            msg["From"] = "me"
            msg.attach(MIMEText(notification.body_text, "plain"))
            if notification.body_html:
                msg.attach(MIMEText(notification.body_html, "html"))

            raw_msg = base64.urlsafe_b64encode(msg.as_bytes()).decode("utf-8")
            sent_msg = service.users().messages().send(userId="me", body={"raw": raw_msg}).execute()

            notification.status = NotificationStatus.SENT
            notification.external_message_id = sent_msg.get("id")
            notification.sent_at = datetime.now(timezone.utc)
            notification.attempts += 1
            await db.commit()
            logger.info(f"[GMAIL] Successfully sent message {notification.id} to {notification.recipient_email}")

        except Exception as e:
            logger.error(f"[GMAIL ERROR] Delivery failed for {notification.id}: {e}")
            notification.status = NotificationStatus.FAILED
            notification.error_message = str(e)
            notification.attempts += 1
            await db.commit()
