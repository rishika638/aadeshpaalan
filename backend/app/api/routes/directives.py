from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.audit_log import AuditAction
from app.models.directive import Directive, DirectiveStatus
from app.models.user import UserRole
from app.schemas.directive import DirectiveStatusUpdateIn
from app.security import require_roles
from app.services.audit_service import append_audit_log


router = APIRouter(prefix="/api/directives", tags=["directives"])


@router.post("/{directive_id}/update-status")
async def update_status(
    directive_id: str,
    payload: DirectiveStatusUpdateIn,
    db: AsyncSession = Depends(get_db),
    user=Depends(require_roles(UserRole.OFFICER, UserRole.ADMIN)),
) -> dict:
    if payload.status not in (DirectiveStatus.IN_PROGRESS, DirectiveStatus.COMPLETED):
        raise HTTPException(status_code=400, detail="Officers may only set in_progress or completed")

    d = (await db.execute(select(Directive).where(Directive.id == directive_id))).scalars().first()
    if d is None:
        raise HTTPException(status_code=404, detail="Directive not found")

    old = {"status": d.status.value}
    d.status = payload.status
    await append_audit_log(
        db,
        table_name="directives",
        record_id=d.id,
        action=AuditAction.STATUS_CHANGED,
        officer_id=user.id,
        officer_name=user.name,
        timestamp=datetime.now(timezone.utc),
        old_value=old,
        new_value={"status": d.status.value},
    )
    await db.commit()
    return {"ok": True}

