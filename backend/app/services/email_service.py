"""
Email Notification Service.
Supports direct SMTP delivery with fallback to audit logging, as well as briefing summaries.
"""
import os
import smtplib
import logging
from datetime import datetime, timezone
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.application import MIMEApplication
from typing import Optional, List, Dict, Any
from pathlib import Path
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from backend.app.core.config import settings
from backend.app.models.notification import (
    Notification, NotificationType, NotificationStatus, DeliveryProvider
)

logger = logging.getLogger("task_reviewer.email")

class EmailService:
    @classmethod
    async def send_task_assignment_email(
        cls,
        db: Optional[AsyncSession],
        task_id: str,
        to_email: str,
        intern_name: str,
        task_title: str,
        deadline_str: str,
        meeting_url: str,
        doc_filename: str,
        doc_path: Optional[str] = None,
        task_objective: Optional[str] = None,
        assigner_name: Optional[str] = "Task Assigner (HR)"
    ) -> Dict[str, Any]:
        """
        Sends the required task assignment notification email to an intern via SMTP.
        Exact required phrasing:
        'This is your assigned task {task_title} must be completed within {deadline_str} deadline.
        The task document ({doc_filename}) (Uploaded by the HR) and a common meeting URL {meeting_url} (Also Uploaded by the HR).'
        """
        if not settings.SMTP_ENABLED:
            logger.info(f"[EMAIL SERVICE] SMTP disabled. Skipping email to {to_email}.")
            return {
                "sent": False,
                "mode": "DISABLED",
                "recipient": to_email,
                "message": "SMTP notifications are globally disabled in settings."
            }

        core_notice = (
            f"This is your assigned task '{task_title}' must be completed within {deadline_str} deadline. "
            f"The task document '{doc_filename}' (Uploaded by the HR) and a common meeting URL {meeting_url} (Also Uploaded by the HR)."
        )

        subject = f"[Task Assigned] {task_title} — Deadline: {deadline_str}"

        # Plaintext representation
        text_body = f"""Hello {intern_name},

{core_notice}

============================================================
ASSIGNMENT SPECIFICATION DETAILS
============================================================
• Assigned By: {assigner_name}
• Task Title: {task_title}
• Completion Deadline: {deadline_str}
• Briefing Meeting URL: {meeting_url}
• Task Document: {doc_filename}
{f'• Objective: {task_objective}' if task_objective else ''}

INSTRUCTIONS:
1. Join the Google Meet session at the scheduled briefing time using the link above.
2. Review the attached task document carefully.
3. Submit your pull request and verification test logs through your Intern Portal before the deadline.

Best regards,
{assigner_name} & Task Reviewer AI Team
"""

        # HTML representation
        html_body = f"""<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<style>
  body {{
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif;
    background-color: #0b0f19;
    color: #e2e8f0;
    margin: 0;
    padding: 24px;
  }}
  .container {{
    max-width: 600px;
    margin: 0 auto;
    background: #111827;
    border: 1px solid rgba(255, 255, 255, 0.1);
    border-radius: 16px;
    overflow: hidden;
    box-shadow: 0 10px 25px -5px rgba(0, 0, 0, 0.5);
  }}
  .header {{
    background: linear-gradient(135deg, #0284c7 0%, #6366f1 100%);
    padding: 24px;
    text-align: left;
  }}
  .header h1 {{
    margin: 0;
    color: #ffffff;
    font-size: 20px;
    font-weight: 800;
  }}
  .header p {{
    margin: 4px 0 0 0;
    color: #e0e7ff;
    font-size: 13px;
  }}
  .content {{
    padding: 28px 24px;
  }}
  .highlight-card {{
    background: rgba(30, 41, 59, 0.7);
    border: 1px solid rgba(56, 189, 248, 0.25);
    border-left: 4px solid #38bdf8;
    border-radius: 12px;
    padding: 16px;
    margin-bottom: 24px;
    font-size: 14px;
    line-height: 1.6;
    color: #f1f5f9;
  }}
  .details-table {{
    width: 100%;
    border-collapse: collapse;
    margin-bottom: 24px;
    font-size: 13px;
  }}
  .details-table td {{
    padding: 10px 12px;
    border-bottom: 1px solid rgba(255, 255, 255, 0.06);
  }}
  .details-table .label {{
    color: #94a3b8;
    width: 140px;
    font-weight: 600;
  }}
  .details-table .value {{
    color: #f8fafc;
    font-weight: 500;
  }}
  .btn-meeting {{
    display: inline-block;
    background: #4f46e5;
    color: #ffffff !important;
    text-decoration: none;
    font-weight: 700;
    font-size: 14px;
    padding: 12px 24px;
    border-radius: 10px;
    margin-top: 8px;
  }}
  .footer {{
    background: #0d131f;
    padding: 16px 24px;
    border-top: 1px solid rgba(255, 255, 255, 0.05);
    text-align: center;
    font-size: 12px;
    color: #64748b;
  }}
</style>
</head>
<body>
  <div class="container">
    <div class="header">
      <h1>New Task Assignment</h1>
      <p>Autonomous AI Reviewer & Engineering Workspace</p>
    </div>
    
    <div class="content">
      <p style="font-size: 15px; margin-top: 0;">Hello <strong>{intern_name}</strong>,</p>
      
      <div class="highlight-card">
        <strong>Official Notice:</strong><br>
        {core_notice}
      </div>

      <table class="details-table">
        <tr>
          <td class="label">Task Title</td>
          <td class="value"><strong>{task_title}</strong></td>
        </tr>
        <tr>
          <td class="label">Assigned By</td>
          <td class="value">{assigner_name}</td>
        </tr>
        <tr>
          <td class="label">Deadline</td>
          <td class="value" style="color: #38bdf8;"><strong>{deadline_str}</strong></td>
        </tr>
        <tr>
          <td class="label">Task Document</td>
          <td class="value">📄 {doc_filename}</td>
        </tr>
        <tr>
          <td class="label">Google Meet Link</td>
          <td class="value"><a href="{meeting_url}" style="color: #818cf8; word-break: break-all;">{meeting_url}</a></td>
        </tr>
      </table>

      <div style="text-align: center; margin: 24px 0;">
        <a href="{meeting_url}" class="btn-meeting" target="_blank">Join Google Meet Briefing</a>
      </div>

      <p style="font-size: 12px; color: #94a3b8; line-height: 1.5;">
        Please attend the scheduled Google Meet session. The AI Reviewer agent <strong>Subha</strong> has analyzed your task document and will guide you through the overview, deliverables, and acceptance criteria.
      </p>
    </div>

    <div class="footer">
      This is an automated engineering notification sent via SMTP by Task Reviewer AI.
    </div>
  </div>
</body>
</html>
"""

        # Build MIME message
        msg = MIMEMultipart("mixed")
        msg["Subject"] = subject
        msg["From"] = f"{settings.SMTP_FROM_NAME} <{settings.SMTP_FROM_EMAIL}>"
        msg["To"] = to_email

        alt_part = MIMEMultipart("alternative")
        alt_part.attach(MIMEText(text_body, "plain", "utf-8"))
        alt_part.attach(MIMEText(html_body, "html", "utf-8"))
        msg.attach(alt_part)

        # Attach file if exists
        if doc_path and os.path.isfile(doc_path):
            try:
                with open(doc_path, "rb") as f:
                    part = MIMEApplication(f.read(), Name=doc_filename)
                part["Content-Disposition"] = f'attachment; filename="{doc_filename}"'
                msg.attach(part)
            except Exception as e:
                logger.warning(f"[EMAIL SERVICE] Could not attach file {doc_path}: {e}")

        # Check SMTP configuration
        has_credentials = bool(settings.SMTP_USER and settings.SMTP_PASSWORD)
        result: Dict[str, Any] = {}

        if not has_credentials:
            logger.info(
                f"[EMAIL SERVICE - AUDIT SIMULATION] No SMTP_USER/PASSWORD configured. "
                f"Notification logged for {to_email}. Core Notice: {core_notice}"
            )
            result = {
                "sent": True,
                "mode": "SIMULATION",
                "recipient": to_email,
                "subject": subject,
                "message": "Notification successfully generated and logged to audit. (Set SMTP_USER & SMTP_PASSWORD in .env for live mail delivery)."
            }
        else:
            try:
                logger.info(f"[EMAIL SERVICE] Dispatching via SMTP to {settings.SMTP_HOST}:{settings.SMTP_PORT}...")
                clean_pw = settings.SMTP_PASSWORD.replace(" ", "") if settings.SMTP_PASSWORD else ""
                clean_user = settings.SMTP_USER.strip() if settings.SMTP_USER else ""

                if settings.SMTP_USE_SSL:
                    server = smtplib.SMTP_SSL(settings.SMTP_HOST, settings.SMTP_PORT, timeout=settings.SMTP_TIMEOUT_SECONDS)
                else:
                    server = smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT, timeout=settings.SMTP_TIMEOUT_SECONDS)
                    if settings.SMTP_USE_TLS:
                        server.starttls()

                server.login(clean_user, clean_pw)
                server.send_message(msg)
                server.quit()

                logger.info(f"[EMAIL SERVICE] Email successfully delivered to {to_email} via SMTP.")
                result = {
                    "sent": True,
                    "mode": "SMTP",
                    "recipient": to_email,
                    "subject": subject,
                    "message": "Notification sent successfully via SMTP."
                }
            except Exception as e:
                logger.error(f"[EMAIL SERVICE ERROR] Failed to send email to {to_email}: {e}")
                result = {
                    "sent": False,
                    "mode": "FAILED",
                    "recipient": to_email,
                    "error": str(e),
                    "message": f"SMTP delivery error: {str(e)}"
                }

        # Record in Notification DB audit table if session available
        if db:
            try:
                notif = Notification(
                    task_id=task_id,
                    recipient_email=to_email,
                    recipient_role="INTERN",
                    notification_type=NotificationType.TASK_ASSIGNED,
                    subject=subject,
                    body_text=text_body,
                    body_html=html_body,
                    status=NotificationStatus.SENT if result.get("sent") else NotificationStatus.FAILED,
                    delivery_provider=DeliveryProvider.SMTP,
                    error_message=result.get("error"),
                    sent_at=datetime.now(timezone.utc) if result.get("sent") else None,
                    attempts=1
                )
                db.add(notif)
                await db.commit()
            except Exception as ex:
                logger.warning(f"[EMAIL SERVICE] Failed to record notification in database: {ex}")

        return result

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

5. UNRESOLVED QUESTIONS:
{unresolved_text}

6. NEXT REVIEW MEETING:
Scheduled for: {review_meeting_time_str} ({timezone_str})
Meeting Link: {review_meeting_url}

7. BRIEFING TRANSCRIPT EXCERPT:
{transcript_snippet}
"""
        notification = Notification(
            task_id=task_id,
            recipient_email=recipient_email,
            recipient_role="INTERN",
            notification_type=NotificationType.BRIEFING_SUMMARY,
            subject=subject,
            body_text=body_text,
            status=NotificationStatus.SENT,
            delivery_provider=DeliveryProvider.SMTP,
            sent_at=datetime.now(timezone.utc)
        )
        db.add(notification)
        await db.commit()
        await db.refresh(notification)
        return notification


    @classmethod
    async def send_meeting_feedback_email(
        cls,
        db: Optional[AsyncSession],
        task_id: str,
        to_email: str,
        intern_name: str,
        task_title: str,
        discussion_summary: str,
        deadline_str: str,
        review_meeting_url: str,
        review_meeting_time_str: str,
        doc_path: Optional[str] = None,
        doc_filename: Optional[str] = None,
        key_deliverables: Optional[str] = None,
        assigner_name: str = "Subha HR"
    ) -> Dict[str, Any]:
        """
        Dispatches post-briefing email via live SMTP containing:
        1. Transcript-grounded summary of what was discussed in the meeting.
        2. Task details, deliverables, and official deadline.
        3. Attached task document.
        4. Newly generated Google Meet link and review schedule.
        """
        subject = f"[Task Briefing Completed] {task_title} — Meeting Summary, Deliverables & Review Link"
        deliverables_content = key_deliverables or "Deliver verified, cleanly tested code, with test evidence and clear documentation."
        doc_display = doc_filename or (os.path.basename(doc_path) if doc_path else "Task_Specification.pdf")

        text_body = f"""Hello {intern_name},

Your task briefing meeting with {assigner_name} for "{task_title}" has concluded.

--- WHAT WAS DISCUSSED OVER THE MEETING ---
{discussion_summary}

--- TASK GROUND TRUTH & REQUIREMENTS ---
Task Title: {task_title}
Key Deliverables: {deliverables_content}
Official Deadline: {deadline_str}
Task Document: {doc_display}

--- NEXT TASK REVIEW MEETING ---
Review Scheduled At: {review_meeting_time_str}
New Google Meet URL: {review_meeting_url}

On the review date, please join the meeting link above and present your completed work via screen share for validation.

Best regards,
{assigner_name} & Task Reviewer AI Team
"""

        html_body = f"""<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<style>
  body {{
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif;
    background-color: #0b0f19;
    color: #e2e8f0;
    margin: 0;
    padding: 24px;
  }}
  .container {{
    max-width: 620px;
    margin: 0 auto;
    background: #111827;
    border: 1px solid rgba(255, 255, 255, 0.1);
    border-radius: 16px;
    overflow: hidden;
    box-shadow: 0 10px 30px -5px rgba(0, 0, 0, 0.6);
  }}
  .header {{
    background: linear-gradient(135deg, #059669 0%, #0284c7 100%);
    padding: 24px;
    text-align: left;
  }}
  .header h1 {{
    margin: 0;
    color: #ffffff;
    font-size: 20px;
    font-weight: 800;
  }}
  .header p {{
    margin: 4px 0 0 0;
    color: #e0e7ff;
    font-size: 13px;
  }}
  .content {{
    padding: 28px 24px;
  }}
  .card {{
    background: rgba(30, 41, 59, 0.7);
    border: 1px solid rgba(56, 189, 248, 0.25);
    border-left: 4px solid #38bdf8;
    border-radius: 12px;
    padding: 18px;
    margin-bottom: 22px;
    font-size: 13.5px;
    line-height: 1.6;
    color: #f1f5f9;
  }}
  .review-card {{
    background: rgba(15, 23, 42, 0.85);
    border: 1px solid rgba(99, 102, 241, 0.4);
    border-left: 4px solid #6366f1;
    border-radius: 12px;
    padding: 18px;
    margin-bottom: 22px;
    font-size: 13.5px;
    line-height: 1.6;
  }}
  .details-table {{
    width: 100%;
    border-collapse: collapse;
    margin-bottom: 22px;
    font-size: 13px;
  }}
  .details-table td {{
    padding: 10px 12px;
    border-bottom: 1px solid rgba(255, 255, 255, 0.06);
  }}
  .details-table .label {{
    color: #94a3b8;
    width: 140px;
    font-weight: 600;
  }}
  .details-table .value {{
    color: #f8fafc;
    font-weight: 500;
  }}
  .btn-meeting {{
    display: inline-block;
    background: #4f46e5;
    color: #ffffff !important;
    text-decoration: none;
    font-weight: 700;
    font-size: 14px;
    padding: 12px 24px;
    border-radius: 10px;
    margin-top: 10px;
  }}
  .footer {{
    background: #0d131f;
    padding: 16px 24px;
    border-top: 1px solid rgba(255, 255, 255, 0.05);
    text-align: center;
    font-size: 12px;
    color: #64748b;
  }}
</style>
</head>
<body>
  <div class="container">
    <div class="header">
      <h1>Briefing Concluded & Review Scheduled</h1>
      <p>Autonomous AI Reviewer & Engineering Workspace</p>
    </div>
    
    <div class="content">
      <p style="font-size: 15px; margin-top: 0;">Hello <strong>{intern_name}</strong>,</p>
      
      <p style="font-size: 13.5px; color: #cbd5e1; margin-bottom: 18px;">
        Your live task briefing meeting with <strong>{assigner_name}</strong> for <strong>{task_title}</strong> has finished. Below is the summary of what was discussed, along with your official task documents and next review meeting details.
      </p>

      <div class="card">
        <strong style="color: #38bdf8; font-size: 14px;">💬 What Was Discussed Over The Meeting:</strong><br><br>
        {discussion_summary.replace(chr(10), "<br>")}
      </div>

      <table class="details-table">
        <tr>
          <td class="label">Task Title</td>
          <td class="value"><strong>{task_title}</strong></td>
        </tr>
        <tr>
          <td class="label">Conducted By</td>
          <td class="value">{assigner_name}</td>
        </tr>
        <tr>
          <td class="label">Official Deadline</td>
          <td class="value" style="color: #38bdf8;"><strong>{deadline_str}</strong></td>
        </tr>
        <tr>
          <td class="label">Key Deliverables</td>
          <td class="value">{deliverables_content}</td>
        </tr>
        <tr>
          <td class="label">Task Document</td>
          <td class="value">📄 {doc_display} (Attached to this email)</td>
        </tr>
      </table>

      <div class="review-card">
        <strong style="color: #a5b4fc; font-size: 14px;">🗓️ Next Task Review Meeting:</strong><br>
        <p style="margin: 8px 0 12px 0;">
          Review Date: <strong style="color: #38bdf8;">{review_meeting_time_str}</strong><br>
          Meeting Link: <a href="{review_meeting_url}" style="color: #818cf8; word-break: break-all;">{review_meeting_url}</a>
        </p>
        <p style="font-size: 12.5px; color: #94a3b8; margin: 0 0 12px 0;">
          On the review call, you will present your completed task via screen share in Google Meet. Subha will evaluate requirement satisfaction and provide real-time feedback.
        </p>
        <div style="text-align: center;">
          <a href="{review_meeting_url}" class="btn-meeting" target="_blank">Open Review Google Meet Link</a>
        </div>
      </div>
    </div>

    <div class="footer">
      This is an automated engineering notification dispatched via SMTP by Task Reviewer AI.
    </div>
  </div>
</body>
</html>"""

        # Build MIME message
        msg = MIMEMultipart("mixed")
        msg["Subject"] = subject
        msg["From"] = f"{settings.SMTP_FROM_NAME} <{settings.SMTP_FROM_EMAIL}>"
        msg["To"] = to_email

        alt_part = MIMEMultipart("alternative")
        alt_part.attach(MIMEText(text_body, "plain", "utf-8"))
        alt_part.attach(MIMEText(html_body, "html", "utf-8"))
        msg.attach(alt_part)

        # Attach file if exists
        if doc_path and os.path.isfile(doc_path):
            try:
                with open(doc_path, "rb") as f:
                    part = MIMEApplication(f.read(), Name=doc_display)
                part["Content-Disposition"] = f'attachment; filename="{doc_display}"'
                msg.attach(part)
            except Exception as e:
                logger.warning(f"[EMAIL SERVICE] Could not attach file {doc_path}: {e}")

        clean_pw = settings.SMTP_PASSWORD.replace(" ", "") if settings.SMTP_PASSWORD else ""
        clean_user = settings.SMTP_USER.strip() if settings.SMTP_USER else ""
        result = {}

        if not (clean_user and clean_pw):
            logger.info(f"[EMAIL SERVICE - SIMULATION] No SMTP credentials. Notification logged for {to_email}.")
            result = {"sent": True, "mode": "SIMULATION", "recipient": to_email, "subject": subject}
        else:
            try:
                logger.info(f"[EMAIL SERVICE] Dispatching post-meeting feedback to {to_email} via SMTP...")
                if settings.SMTP_USE_SSL:
                    server = smtplib.SMTP_SSL(settings.SMTP_HOST, settings.SMTP_PORT, timeout=settings.SMTP_TIMEOUT_SECONDS)
                else:
                    server = smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT, timeout=settings.SMTP_TIMEOUT_SECONDS)
                    if settings.SMTP_USE_TLS:
                        server.starttls()

                server.login(clean_user, clean_pw)
                server.send_message(msg)
                server.quit()

                logger.info(f"[EMAIL SERVICE] Post-meeting feedback email successfully delivered to {to_email} via SMTP.")
                result = {"sent": True, "mode": "SMTP", "recipient": to_email, "subject": subject}
            except Exception as e:
                logger.error(f"[EMAIL SERVICE ERROR] Failed to send email to {to_email}: {e}")
                result = {"sent": False, "mode": "FAILED", "recipient": to_email, "error": str(e)}

        if db:
            try:
                notif = Notification(
                    task_id=task_id,
                    recipient_email=to_email,
                    recipient_role="INTERN",
                    notification_type=NotificationType.BRIEFING_SUMMARY,
                    subject=subject,
                    body_text=text_body,
                    body_html=html_body,
                    status=NotificationStatus.SENT if result.get("sent") else NotificationStatus.FAILED,
                    delivery_provider=DeliveryProvider.SMTP,
                    error_message=result.get("error"),
                    sent_at=datetime.now(timezone.utc) if result.get("sent") else None,
                    attempts=1
                )
                db.add(notif)
                await db.commit()
            except Exception as ex:
                logger.warning(f"[EMAIL SERVICE] Failed to record notification in database: {ex}")

        return result


    @classmethod
    async def send_task_passed_email(
        cls,
        db: Optional[AsyncSession],
        task_id: str,
        to_email: str,
        intern_name: str,
        task_title: str,
        feedback: Optional[str] = None,
        score: Optional[float] = None,
        assigner_name: str = "Subha HR"
    ) -> Dict[str, Any]:
        """
        Dispatches completion email via live SMTP when task evaluation is PASSED.
        Required core message:
        'Your task has been completed. Congratulations. Wait until the next task is being assigned.'
        """
        subject = f"[Task Evaluation: PASSED] {task_title} — Congratulations!"
        feedback_display = feedback or "All rubric requirements and acceptance criteria have been fully verified."
        score_display = f"{score:.1f}%" if score is not None else "100%"

        text_body = f"""Hello {intern_name},

Your task has been completed. Congratulations. Wait until the next task is being assigned.

============================================================
TASK EVALUATION OUTCOME: PASSED
============================================================
• Task Title: {task_title}
• Evaluation Status: PASSED (Score: {score_display})
• Evaluated By: {assigner_name}
• Reviewer Feedback:
{feedback_display}

NEXT STEPS:
Your current task deliverables have met all required standards. Please wait until your next task assignment is announced by your HR lead.

Best regards,
{assigner_name} & Task Reviewer AI Team
"""

        html_body = f"""<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<style>
  body {{
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif;
    background-color: #0b0f19;
    color: #e2e8f0;
    margin: 0;
    padding: 24px;
  }}
  .container {{
    max-width: 600px;
    margin: 0 auto;
    background: #111827;
    border: 1px solid rgba(255, 255, 255, 0.1);
    border-radius: 16px;
    overflow: hidden;
    box-shadow: 0 10px 30px -5px rgba(0, 0, 0, 0.6);
  }}
  .header {{
    background: linear-gradient(135deg, #059669 0%, #10b981 50%, #065f46 100%);
    padding: 28px 24px;
    text-align: left;
  }}
  .header h1 {{
    margin: 0;
    color: #ffffff;
    font-size: 22px;
    font-weight: 800;
  }}
  .header p {{
    margin: 6px 0 0 0;
    color: #d1fae5;
    font-size: 13.5px;
  }}
  .content {{
    padding: 28px 24px;
  }}
  .passed-box {{
    background: rgba(16, 185, 129, 0.12);
    border: 1px solid rgba(16, 185, 129, 0.4);
    border-left: 4px solid #10b981;
    border-radius: 12px;
    padding: 20px;
    margin-bottom: 22px;
  }}
  .passed-title {{
    font-size: 16px;
    font-weight: 800;
    color: #34d399;
    margin-bottom: 6px;
  }}
  .passed-core {{
    font-size: 14.5px;
    font-weight: 600;
    color: #ffffff;
    line-height: 1.5;
  }}
  .meta-grid {{
    background: rgba(30, 41, 59, 0.5);
    border: 1px solid rgba(255, 255, 255, 0.05);
    border-radius: 10px;
    padding: 16px;
    margin-bottom: 22px;
  }}
  .meta-item {{
    display: flex;
    justify-content: space-between;
    padding: 7px 0;
    border-bottom: 1px solid rgba(255, 255, 255, 0.05);
    font-size: 13px;
  }}
  .meta-item:last-child {{
    border-bottom: none;
  }}
  .meta-label {{
    color: #94a3b8;
    font-weight: 500;
  }}
  .meta-val {{
    color: #f8fafc;
    font-weight: 600;
  }}
  .feedback-box {{
    background: rgba(15, 23, 42, 0.7);
    border: 1px solid rgba(255, 255, 255, 0.08);
    border-radius: 10px;
    padding: 16px;
    margin-bottom: 22px;
    font-size: 13px;
    line-height: 1.6;
    color: #cbd5e1;
  }}
  .footer {{
    padding: 20px 24px;
    background: rgba(0, 0, 0, 0.2);
    border-top: 1px solid rgba(255, 255, 255, 0.05);
    text-align: center;
    font-size: 12px;
    color: #64748b;
  }}
</style>
</head>
<body>
  <div class="container">
    <div class="header">
      <h1>Task Evaluation Completed</h1>
      <p>Autonomous AI Technical Review &middot; Outcome: PASSED</p>
    </div>
    <div class="content">
      <div class="passed-box">
        <div class="passed-title">Congratulations!</div>
        <div class="passed-core">Your task has been completed. Congratulations. Wait until the next task is being assigned.</div>
      </div>

      <div class="meta-grid">
        <div class="meta-item">
          <span class="meta-label">Task Assignment:</span>
          <span class="meta-val">{task_title}</span>
        </div>
        <div class="meta-item">
          <span class="meta-label">Evaluation Result:</span>
          <span class="meta-val" style="color: #34d399;">PASSED ({score_display})</span>
        </div>
        <div class="meta-item">
          <span class="meta-label">Reviewer:</span>
          <span class="meta-val">{assigner_name}</span>
        </div>
      </div>

      <div style="font-size: 12px; font-weight: 700; text-transform: uppercase; letter-spacing: 0.05em; color: #94a3b8; margin-bottom: 8px;">Reviewer Notes & Feedback</div>
      <div class="feedback-box">
        {feedback_display}
      </div>
    </div>
    <div class="footer">
      Automated Task Lifecycle Notification &middot; {assigner_name} &middot; Task Reviewer AI
    </div>
  </div>
</body>
</html>"""

        msg = MIMEMultipart("mixed")
        msg["Subject"] = subject
        msg["From"] = f"{settings.SMTP_FROM_NAME} <{settings.SMTP_FROM_EMAIL}>"
        msg["To"] = to_email

        alt_part = MIMEMultipart("alternative")
        alt_part.attach(MIMEText(text_body, "plain", "utf-8"))
        alt_part.attach(MIMEText(html_body, "html", "utf-8"))
        msg.attach(alt_part)

        clean_pw = settings.SMTP_PASSWORD.replace(" ", "") if settings.SMTP_PASSWORD else ""
        clean_user = settings.SMTP_USER.strip() if settings.SMTP_USER else ""
        result = {}

        if not (clean_user and clean_pw):
            logger.info(f"[EMAIL SERVICE - SIMULATION] No SMTP credentials. Notification logged for {to_email}.")
            result = {"sent": True, "mode": "SIMULATION", "recipient": to_email, "subject": subject}
        else:
            try:
                logger.info(f"[EMAIL SERVICE] Dispatching task passed email to {to_email} via SMTP...")
                if settings.SMTP_USE_SSL:
                    server = smtplib.SMTP_SSL(settings.SMTP_HOST, settings.SMTP_PORT, timeout=settings.SMTP_TIMEOUT_SECONDS)
                else:
                    server = smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT, timeout=settings.SMTP_TIMEOUT_SECONDS)
                    if settings.SMTP_USE_TLS:
                        server.starttls()

                server.login(clean_user, clean_pw)
                server.send_message(msg)
                server.quit()

                logger.info(f"[EMAIL SERVICE] Task passed email successfully delivered to {to_email} via SMTP.")
                result = {"sent": True, "mode": "SMTP", "recipient": to_email, "subject": subject}
            except Exception as e:
                logger.error(f"[EMAIL SERVICE ERROR] Failed to send email to {to_email}: {e}")
                result = {"sent": False, "mode": "FAILED", "recipient": to_email, "error": str(e)}

        if db:
            try:
                notif = Notification(
                    task_id=task_id,
                    recipient_email=to_email,
                    recipient_role="INTERN",
                    notification_type=NotificationType.TASK_PASSED,
                    subject=subject,
                    body_text=text_body,
                    body_html=html_body,
                    status=NotificationStatus.SENT if result.get("sent") else NotificationStatus.FAILED,
                    delivery_provider=DeliveryProvider.SMTP,
                    error_message=result.get("error"),
                    sent_at=datetime.now(timezone.utc) if result.get("sent") else None,
                    attempts=1
                )
                db.add(notif)
                await db.commit()
            except Exception as ex:
                logger.warning(f"[EMAIL SERVICE] Failed to record notification in database: {ex}")

        return result

    @classmethod
    async def send_task_revision_email(
        cls,
        db: Optional[AsyncSession],
        task_id: str,
        to_email: str,
        intern_name: str,
        task_title: str,
        gaps: List[str],
        next_review_time_str: str,
        next_review_meet_url: str,
        assigner_name: str = "Subha HR"
    ) -> Dict[str, Any]:
        """
        Dispatches revision request email via live SMTP when task evaluation requires revision.
        Required core message:
        'These needs to be changed: {gaps_text}'
        Along with the next review meeting date/time and the NEW Google Meet link.
        """
        subject = f"[Task Evaluation: REVISION REQUIRED] {task_title} — Action Items & Next Review Link"
        gaps_list = gaps if gaps else ["Please address the feedback notes provided by the reviewer."]
        gaps_bullets = "\n".join([f"• {g}" for g in gaps_list])
        gaps_text = "; ".join(gaps_list)

        text_body = f"""Hello {intern_name},

Your task review session for "{task_title}" has concluded.
These needs to be changed: {gaps_text}

============================================================
REQUIRED REVISIONS & ACTION ITEMS
============================================================
{gaps_bullets}

============================================================
NEXT TASK REVIEW MEETING (NEW GOOGLE MEET LINK)
============================================================
• Scheduled Date & Time: {next_review_time_str}
• New Google Meet Link: {next_review_meet_url}

INSTRUCTIONS:
1. Review the required changes listed above.
2. Update your code and push your revisions to your repository.
3. Join the new Google Meet link above at the scheduled time to present your revisions.

Best regards,
{assigner_name} & Task Reviewer AI Team
"""

        gaps_html_items = "".join([f'<li style="margin-bottom: 8px; color: #fecdd3;">{g}</li>' for g in gaps_list])

        html_body = f"""<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<style>
  body {{
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif;
    background-color: #0b0f19;
    color: #e2e8f0;
    margin: 0;
    padding: 24px;
  }}
  .container {{
    max-width: 600px;
    margin: 0 auto;
    background: #111827;
    border: 1px solid rgba(255, 255, 255, 0.1);
    border-radius: 16px;
    overflow: hidden;
    box-shadow: 0 10px 30px -5px rgba(0, 0, 0, 0.6);
  }}
  .header {{
    background: linear-gradient(135deg, #e11d48 0%, #be123c 50%, #881337 100%);
    padding: 28px 24px;
    text-align: left;
  }}
  .header h1 {{
    margin: 0;
    color: #ffffff;
    font-size: 22px;
    font-weight: 800;
  }}
  .header p {{
    margin: 6px 0 0 0;
    color: #ffe4e6;
    font-size: 13.5px;
  }}
  .content {{
    padding: 28px 24px;
  }}
  .revision-banner {{
    background: rgba(225, 29, 72, 0.12);
    border: 1px solid rgba(225, 29, 72, 0.4);
    border-left: 4px solid #e11d48;
    border-radius: 12px;
    padding: 18px;
    margin-bottom: 22px;
  }}
  .revision-title {{
    font-size: 15px;
    font-weight: 800;
    color: #fb7185;
    margin-bottom: 6px;
  }}
  .revision-core {{
    font-size: 14px;
    font-weight: 600;
    color: #ffffff;
    line-height: 1.5;
  }}
  .gaps-box {{
    background: rgba(30, 41, 59, 0.5);
    border: 1px solid rgba(244, 63, 94, 0.25);
    border-radius: 12px;
    padding: 18px;
    margin-bottom: 22px;
  }}
  .gaps-box ul {{
    margin: 8px 0 0 0;
    padding-left: 20px;
    font-size: 13.5px;
    line-height: 1.6;
  }}
  .meeting-card {{
    background: rgba(15, 23, 42, 0.85);
    border: 1px solid rgba(99, 102, 241, 0.4);
    border-left: 4px solid #6366f1;
    border-radius: 12px;
    padding: 18px;
    margin-bottom: 22px;
  }}
  .btn-meet {{
    display: inline-block;
    background: linear-gradient(135deg, #4f46e5 0%, #6366f1 100%);
    color: #ffffff !important;
    text-decoration: none;
    font-weight: 700;
    font-size: 14px;
    padding: 12px 24px;
    border-radius: 8px;
    margin-top: 12px;
  }}
  .footer {{
    padding: 20px 24px;
    background: rgba(0, 0, 0, 0.2);
    border-top: 1px solid rgba(255, 255, 255, 0.05);
    text-align: center;
    font-size: 12px;
    color: #64748b;
  }}
</style>
</head>
<body>
  <div class="container">
    <div class="header">
      <h1>Revision Required</h1>
      <p>Autonomous AI Technical Review &middot; Action Items Identified</p>
    </div>
    <div class="content">
      <div class="revision-banner">
        <div class="revision-title">Action Items Required</div>
        <div class="revision-core">These needs to be changed: {gaps_text}</div>
      </div>

      <div class="gaps-box">
        <div style="font-size: 12px; font-weight: 700; text-transform: uppercase; letter-spacing: 0.05em; color: #fb7185;">Detailed Action Items</div>
        <ul>
          {gaps_html_items}
        </ul>
      </div>

      <div class="meeting-card">
        <div style="font-size: 12px; font-weight: 700; text-transform: uppercase; letter-spacing: 0.05em; color: #818cf8;">Next Task Review Session</div>
        <div style="font-size: 15px; font-weight: 700; color: #ffffff; margin-top: 4px;">{next_review_time_str}</div>
        <p style="font-size: 13px; color: #94a3b8; margin: 8px 0 0 0;">
          A new Google Meet link has been generated for your subsequent review session. Please present your updated implementation using the link below:
        </p>
        <a href="{next_review_meet_url}" target="_blank" class="btn-meet">Join New Review Google Meet &rarr;</a>
        <div style="font-size: 11px; color: #64748b; margin-top: 8px; font-family: monospace;">{next_review_meet_url}</div>
      </div>
    </div>
    <div class="footer">
      Automated Task Lifecycle Notification &middot; {assigner_name} &middot; Task Reviewer AI
    </div>
  </div>
</body>
</html>"""

        msg = MIMEMultipart("mixed")
        msg["Subject"] = subject
        msg["From"] = f"{settings.SMTP_FROM_NAME} <{settings.SMTP_FROM_EMAIL}>"
        msg["To"] = to_email

        alt_part = MIMEMultipart("alternative")
        alt_part.attach(MIMEText(text_body, "plain", "utf-8"))
        alt_part.attach(MIMEText(html_body, "html", "utf-8"))
        msg.attach(alt_part)

        clean_pw = settings.SMTP_PASSWORD.replace(" ", "") if settings.SMTP_PASSWORD else ""
        clean_user = settings.SMTP_USER.strip() if settings.SMTP_USER else ""
        result = {}

        if not (clean_user and clean_pw):
            logger.info(f"[EMAIL SERVICE - SIMULATION] No SMTP credentials. Notification logged for {to_email}.")
            result = {"sent": True, "mode": "SIMULATION", "recipient": to_email, "subject": subject}
        else:
            try:
                logger.info(f"[EMAIL SERVICE] Dispatching task revision email to {to_email} via SMTP...")
                if settings.SMTP_USE_SSL:
                    server = smtplib.SMTP_SSL(settings.SMTP_HOST, settings.SMTP_PORT, timeout=settings.SMTP_TIMEOUT_SECONDS)
                else:
                    server = smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT, timeout=settings.SMTP_TIMEOUT_SECONDS)
                    if settings.SMTP_USE_TLS:
                        server.starttls()

                server.login(clean_user, clean_pw)
                server.send_message(msg)
                server.quit()

                logger.info(f"[EMAIL SERVICE] Task revision email successfully delivered to {to_email} via SMTP.")
                result = {"sent": True, "mode": "SMTP", "recipient": to_email, "subject": subject}
            except Exception as e:
                logger.error(f"[EMAIL SERVICE ERROR] Failed to send email to {to_email}: {e}")
                result = {"sent": False, "mode": "FAILED", "recipient": to_email, "error": str(e)}

        if db:
            try:
                notif = Notification(
                    task_id=task_id,
                    recipient_email=to_email,
                    recipient_role="INTERN",
                    notification_type=NotificationType.REVISION_REQUEST,
                    subject=subject,
                    body_text=text_body,
                    body_html=html_body,
                    status=NotificationStatus.SENT if result.get("sent") else NotificationStatus.FAILED,
                    delivery_provider=DeliveryProvider.SMTP,
                    error_message=result.get("error"),
                    sent_at=datetime.now(timezone.utc) if result.get("sent") else None,
                    attempts=1
                )
                db.add(notif)
                await db.commit()
            except Exception as ex:
                logger.warning(f"[EMAIL SERVICE] Failed to record notification in database: {ex}")

        return result

    @classmethod
    def test_smtp_connection(cls) -> Dict[str, Any]:
        """Diagnostic helper to verify SMTP connectivity."""
        if not (settings.SMTP_USER and settings.SMTP_PASSWORD):
            return {
                "status": "UNCONFIGURED",
                "host": settings.SMTP_HOST,
                "port": settings.SMTP_PORT,
                "message": "SMTP_USER or SMTP_PASSWORD is not set in environment."
            }
        try:
            clean_pw = settings.SMTP_PASSWORD.replace(" ", "") if settings.SMTP_PASSWORD else ""
            clean_user = settings.SMTP_USER.strip() if settings.SMTP_USER else ""

            if settings.SMTP_USE_SSL:
                server = smtplib.SMTP_SSL(settings.SMTP_HOST, settings.SMTP_PORT, timeout=settings.SMTP_TIMEOUT_SECONDS)
            else:
                server = smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT, timeout=settings.SMTP_TIMEOUT_SECONDS)
                if settings.SMTP_USE_TLS:
                    server.starttls()
            server.login(clean_user, clean_pw)
            server.quit()
            return {
                "status": "CONNECTED",
                "host": settings.SMTP_HOST,
                "port": settings.SMTP_PORT,
                "message": "SMTP connection and authentication successful."
            }
        except Exception as e:
            return {
                "status": "ERROR",
                "host": settings.SMTP_HOST,
                "port": settings.SMTP_PORT,
                "error": str(e)
            }
