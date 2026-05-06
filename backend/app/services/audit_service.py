from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.audit_log import AuditAction, AuditLog


async def append_audit_log(
    db: AsyncSession,
    *,
    table_name: str,
    record_id: uuid.UUID,
    action: AuditAction,
    officer_id: uuid.UUID,
    officer_name: str,
    old_value: dict | None = None,
    new_value: dict | None = None,
    ip_address: str | None = None,
    timestamp: datetime | None = None,
) -> AuditLog:
    entry = AuditLog(
        table_name=table_name,
        record_id=record_id,
        action=action,
        officer_id=officer_id,
        officer_name=officer_name,
        timestamp=timestamp or datetime.now(timezone.utc),
        old_value=old_value,
        new_value=new_value,
        ip_address=ip_address,
    )
    db.add(entry)
    await db.flush()
    return entry

