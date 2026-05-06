from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.audit_log import AuditLog
from app.security import get_current_user


router = APIRouter(prefix="/api/audit", tags=["audit"])


@router.get("/{record_id}")
async def audit_trail(record_id: str, db: AsyncSession = Depends(get_db), user=Depends(get_current_user)) -> dict:
    logs = (
        await db.execute(select(AuditLog).where(AuditLog.record_id == record_id).order_by(AuditLog.timestamp.desc()).limit(2000))
    ).scalars().all()
    return {
        "record_id": str(record_id),
        "items": [
            {
                "id": str(l.id),
                "table_name": l.table_name,
                "record_id": str(l.record_id),
                "action": l.action.value,
                "officer_id": str(l.officer_id),
                "officer_name": l.officer_name,
                "timestamp": l.timestamp.isoformat(),
                "old_value": l.old_value,
                "new_value": l.new_value,
                "ip_address": l.ip_address,
            }
            for l in logs
        ],
    }

