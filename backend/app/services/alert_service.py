from __future__ import annotations

import smtplib
import uuid
from dataclasses import dataclass
from datetime import date, datetime, timezone
from email.message import EmailMessage

from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models.audit_log import AuditAction, AuditLog
from app.models.directive import Directive
from app.models.user import User
from app.services.audit_service import append_audit_log


@dataclass(frozen=True)
class AlertMilestone:
    days_before: int  # 30,14,7,3,0


MILESTONES: list[AlertMilestone] = [
    AlertMilestone(30),
    AlertMilestone(14),
    AlertMilestone(7),
    AlertMilestone(3),
    AlertMilestone(0),
]


def _build_email(*, recipient: str, subject: str, body: str) -> EmailMessage:
    msg = EmailMessage()
    msg["To"] = recipient
    msg["From"] = settings.nic_smtp_user or "alerts@karnataka.gov.in"
    msg["Subject"] = subject
    msg.set_content(body)
    return msg


async def _already_sent(db: AsyncSession, directive_id: uuid.UUID, days_before: int) -> bool:
    # Deduplicate by audit_logs entry of action=alert_sent and milestone in new_value
    q = (
        select(AuditLog.id)
        .where(
            and_(
                AuditLog.table_name == "directives",
                AuditLog.record_id == directive_id,
                AuditLog.action == AuditAction.ALERT_SENT,
            )
        )
        .limit(200)
    )
    rows = (await db.execute(q)).scalars().all()
    if not rows:
        return False
    # Need to actually inspect JSONB values; simplest is re-select full rows
    q2 = (
        select(AuditLog)
        .where(
            and_(
                AuditLog.table_name == "directives",
                AuditLog.record_id == directive_id,
                AuditLog.action == AuditAction.ALERT_SENT,
            )
        )
        .order_by(AuditLog.timestamp.desc())
        .limit(200)
    )
    logs = (await db.execute(q2)).scalars().all()
    for l in logs:
        nv = l.new_value or {}
        if nv.get("milestone_days_before") == days_before:
            return True
    return False


async def _lookup_recipient(db: AsyncSession, directive: Directive) -> User | None:
    # Map designation → active user email. If multiple, pick first.
    q = select(User).where(and_(User.designation == directive.owner_designation, User.is_active == True)).limit(1)  # noqa: E712
    return (await db.execute(q)).scalars().first()


async def send_deadline_alerts_for_directive(
    *,
    db: AsyncSession,
    directive: Directive,
    case_number: str,
    court_name: str,
    dashboard_case_url: str,
    today: date,
    system_officer_id: uuid.UUID,
    system_officer_name: str,
) -> int:
    if directive.deadline is None:
        return 0

    recipient_user = await _lookup_recipient(db, directive)
    if recipient_user is None:
        # Still audit that we attempted but had no recipient mapping
        await append_audit_log(
            db,
            table_name="directives",
            record_id=directive.id,
            action=AuditAction.ALERT_SENT,
            officer_id=system_officer_id,
            officer_name=system_officer_name,
            new_value={
                "event": "alert_skipped_no_recipient",
                "owner_designation": directive.owner_designation,
            },
        )
        return 0

    days_remaining = (directive.deadline - today).days
    sent = 0

    for m in MILESTONES:
        if days_remaining != m.days_before:
            continue
        if await _already_sent(db, directive.id, m.days_before):
            continue

        subject = f"[AadeshPaalan] {case_number} — Deadline T-{m.days_before}"
        body = (
            f"Case: {case_number} ({court_name})\n"
            f"Directive: {directive.directive_text}\n"
            f"Deadline: {directive.deadline.isoformat()}\n"
            f"Days remaining: {days_remaining}\n"
            f"Risk level: {directive.risk_level}\n"
            f"Link: {dashboard_case_url}\n\n"
            f"Officer: {recipient_user.name} — {recipient_user.designation}\n"
        )

        msg = _build_email(recipient=recipient_user.email, subject=subject, body=body)

        if not (settings.nic_smtp_host and settings.nic_smtp_port and settings.nic_smtp_user and settings.nic_smtp_pass):
            raise RuntimeError("NIC SMTP settings are not configured in environment.")

        with smtplib.SMTP(settings.nic_smtp_host, int(settings.nic_smtp_port)) as smtp:
            smtp.starttls()
            smtp.login(settings.nic_smtp_user, settings.nic_smtp_pass)
            smtp.send_message(msg)

        await append_audit_log(
            db,
            table_name="directives",
            record_id=directive.id,
            action=AuditAction.ALERT_SENT,
            officer_id=system_officer_id,
            officer_name=system_officer_name,
            timestamp=datetime.now(timezone.utc),
            new_value={
                "milestone_days_before": m.days_before,
                "recipient": recipient_user.email,
            },
        )
        sent += 1

    return sent

