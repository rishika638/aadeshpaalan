from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.audit_log import AuditAction, AuditLog
from app.models.case import Case, CaseStatus
from app.models.directive import Directive, DirectiveStatus
from app.models.user import UserRole
from app.schemas.case import CaseDetailResponse, CaseOut, CaseStatusResponse, ReviewResponse, VerifyRequest
from app.schemas.directive import DirectiveOut
from app.security import get_current_user, require_roles
from app.services.audit_service import append_audit_log
from app.services.risk_calculator import compute_risk


router = APIRouter(prefix="/api/cases", tags=["cases"])


def _progress_from_status(case_status: CaseStatus) -> tuple[int, str]:
    if case_status == CaseStatus.PROCESSING:
        return 50, "Processing (OCR/AI/rules engine)"
    if case_status == CaseStatus.PENDING_REVIEW:
        return 100, "Ready for review"
    if case_status == CaseStatus.VERIFIED:
        return 100, "Verified"
    if case_status == CaseStatus.ACTIVE:
        return 100, "Active"
    if case_status == CaseStatus.CLOSED:
        return 100, "Closed"
    return 0, "Unknown"


@router.get("/{case_id}/pdf")
async def serve_pdf(case_id: str, db: AsyncSession = Depends(get_db), user=Depends(get_current_user)) -> FileResponse:
    case = (await db.execute(select(Case).where(Case.id == case_id))).scalars().first()
    if case is None:
        raise HTTPException(status_code=404, detail="Case not found")
    from pathlib import Path
    path = Path(case.pdf_path)
    if not path.exists():
        raise HTTPException(status_code=404, detail="PDF file not found on disk")
    return FileResponse(
        path,
        media_type="application/pdf",
        headers={"Content-Disposition": f"inline; filename={path.name}"},
    )


@router.get("/{case_id}/status", response_model=CaseStatusResponse)
async def case_status(case_id: str, db: AsyncSession = Depends(get_db), user=Depends(get_current_user)) -> CaseStatusResponse:
    case = (await db.execute(select(Case).where(Case.id == case_id))).scalars().first()
    if case is None:
        raise HTTPException(status_code=404, detail="Case not found")
    pct, msg = _progress_from_status(case.status)
    return CaseStatusResponse(status=case.status, progress_percent=pct, message=msg)


@router.get("/{case_id}/review", response_model=ReviewResponse)
async def review(case_id: str, db: AsyncSession = Depends(get_db), user=Depends(require_roles(UserRole.REVIEWER, UserRole.ADMIN))) -> ReviewResponse:
    case = (await db.execute(select(Case).where(Case.id == case_id))).scalars().first()
    if case is None:
        raise HTTPException(status_code=404, detail="Case not found")
    directives = (await db.execute(select(Directive).where(Directive.case_id == case.id))).scalars().all()
    return ReviewResponse(
        case=CaseOut.model_validate(case, from_attributes=True),
        directives=[DirectiveOut.model_validate(d, from_attributes=True) for d in directives],
    )


@router.post("/{case_id}/verify")
async def verify(case_id: str, payload: VerifyRequest, db: AsyncSession = Depends(get_db), user=Depends(require_roles(UserRole.REVIEWER, UserRole.ADMIN))) -> dict:
    case = (await db.execute(select(Case).where(Case.id == case_id))).scalars().first()
    if case is None:
        raise HTTPException(status_code=404, detail="Case not found")

    directives = (await db.execute(select(Directive).where(Directive.case_id == case.id))).scalars().all()
    by_id = {d.id: d for d in directives}

    now = datetime.now(timezone.utc)
    today = now.date()

    for incoming in payload.directives:
        d = by_id.get(incoming.id)
        if d is None:
            continue
        old = {
            "directive_text": d.directive_text,
            "owner_designation": d.owner_designation,
            "deadline": d.deadline.isoformat() if d.deadline else None,
            "requires_human_review": d.requires_human_review,
        }

        d.directive_text = incoming.directive_text
        d.source_paragraph = incoming.source_paragraph
        d.confidence_score = incoming.confidence_score
        d.owner_designation = incoming.owner_designation
        d.owner_department = incoming.owner_department
        d.deadline = incoming.deadline
        d.deadline_basis = incoming.deadline_basis
        d.requires_human_review = incoming.requires_human_review
        d.notes = incoming.notes

        d.status = DirectiveStatus.VERIFIED
        d.verified_by = user.id
        d.verified_at = now
        d.risk_level = compute_risk(d, today)

        new = {
            "directive_text": d.directive_text,
            "owner_designation": d.owner_designation,
            "deadline": d.deadline.isoformat() if d.deadline else None,
            "requires_human_review": d.requires_human_review,
            "status": d.status.value,
            "risk_level": d.risk_level.value if d.risk_level else None,
        }
        await append_audit_log(
            db,
            table_name="directives",
            record_id=d.id,
            action=AuditAction.VERIFIED,
            officer_id=user.id,
            officer_name=user.name,
            old_value=old,
            new_value=new,
        )

    case.status = CaseStatus.VERIFIED
    await append_audit_log(
        db,
        table_name="cases",
        record_id=case.id,
        action=AuditAction.VERIFIED,
        officer_id=user.id,
        officer_name=user.name,
        new_value={"event": "case_verified"},
    )

    await db.commit()
    return {"ok": True}


@router.get("/{case_id}", response_model=CaseDetailResponse)
async def case_detail(case_id: str, db: AsyncSession = Depends(get_db), user=Depends(get_current_user)) -> CaseDetailResponse:
    case = (await db.execute(select(Case).where(Case.id == case_id))).scalars().first()
    if case is None:
        raise HTTPException(status_code=404, detail="Case not found")
    directives = (await db.execute(select(Directive).where(Directive.case_id == case.id))).scalars().all()
    logs = (
        await db.execute(
            select(AuditLog).where(AuditLog.record_id.in_([case.id] + [d.id for d in directives])).order_by(AuditLog.timestamp.desc()).limit(2000)
        )
    ).scalars().all()

    return CaseDetailResponse(
        id=case.id,
        case_number=case.case_number,
        court_name=case.court_name,
        judgment_date=case.judgment_date,
        status=case.status,
        directives=[DirectiveOut.model_validate(d, from_attributes=True) for d in directives],
        audit_logs=[
            {
                "id": str(l.id),
                "table_name": l.table_name,
                "record_id": str(l.record_id),
                "action": l.action.value,
                "officer_name": l.officer_name,
                "timestamp": l.timestamp.isoformat(),
                "old_value": l.old_value,
                "new_value": l.new_value,
                "ip_address": l.ip_address,
            }
            for l in logs
        ],
    )
