from __future__ import annotations

from datetime import date

from fastapi import APIRouter, Depends
from sqlalchemy import and_, case, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.case import Case, CaseStatus
from app.models.directive import Directive, DirectiveStatus, RiskLevel
from app.security import get_current_user


router = APIRouter(prefix="/api/dashboard", tags=["dashboard"])


@router.get("/summary")
async def summary(db: AsyncSession = Depends(get_db), user=Depends(get_current_user)) -> dict:
    # Total active cases = those verified/active (excluding closed)
    total_active_cases = (
        await db.execute(select(func.count(Case.id)).where(Case.status.in_([CaseStatus.VERIFIED, CaseStatus.ACTIVE])))
    ).scalar_one()

    def count_risk(level: RiskLevel) -> int:
        return (
            (
                db.execute(
                    select(func.count(Directive.id)).where(
                        and_(Directive.status == DirectiveStatus.VERIFIED, Directive.risk_level == level)
                    )
                )
            )
        )

    overdue = (
        await db.execute(
            select(func.count(Directive.id)).where(
                and_(Directive.status == DirectiveStatus.VERIFIED, Directive.risk_level == RiskLevel.OVERDUE)
            )
        )
    ).scalar_one()
    critical = (
        await db.execute(
            select(func.count(Directive.id)).where(
                and_(Directive.status == DirectiveStatus.VERIFIED, Directive.risk_level == RiskLevel.CRITICAL)
            )
        )
    ).scalar_one()
    due_soon = (
        await db.execute(
            select(func.count(Directive.id)).where(
                and_(Directive.status == DirectiveStatus.VERIFIED, Directive.risk_level == RiskLevel.DUE_SOON)
            )
        )
    ).scalar_one()
    watch = (
        await db.execute(
            select(func.count(Directive.id)).where(
                and_(Directive.status == DirectiveStatus.VERIFIED, Directive.risk_level == RiskLevel.WATCH)
            )
        )
    ).scalar_one()
    compliant = (
        await db.execute(
            select(func.count(Directive.id)).where(
                and_(Directive.status == DirectiveStatus.VERIFIED, Directive.risk_level == RiskLevel.COMPLIANT)
            )
        )
    ).scalar_one()

    return {
        "total_active_cases": int(total_active_cases),
        "overdue_count": int(overdue),
        "critical_count": int(critical),
        "due_soon_count": int(due_soon),
        "watch_count": int(watch),
        "compliant_count": int(compliant),
    }


@router.get("/directives")
async def directives(
    risk_level: RiskLevel | None = None,
    department: str | None = None,
    deadline_from: date | None = None,
    deadline_to: date | None = None,
    page: int = 1,
    limit: int = 50,
    db: AsyncSession = Depends(get_db),
    user=Depends(get_current_user),
) -> dict:
    limit = max(1, min(200, limit))
    page = max(1, page)
    q = select(Directive, Case).join(Case, Case.id == Directive.case_id).where(Directive.status == DirectiveStatus.VERIFIED)
    if risk_level is not None:
        q = q.where(Directive.risk_level == risk_level)
    if department:
        q = q.where(Directive.owner_department == department)
    if deadline_from:
        q = q.where(Directive.deadline >= deadline_from)
    if deadline_to:
        q = q.where(Directive.deadline <= deadline_to)

    # Sort by risk severity then deadline ascending
    q = q.order_by(
        case(
            (Directive.risk_level == RiskLevel.OVERDUE, 0),
            (Directive.risk_level == RiskLevel.CRITICAL, 1),
            (Directive.risk_level == RiskLevel.DUE_SOON, 2),
            (Directive.risk_level == RiskLevel.WATCH, 3),
            (Directive.risk_level == RiskLevel.COMPLIANT, 4),
            (Directive.risk_level == RiskLevel.ARCHIVED_UNVERIFIED, 6),
            else_=5,
        ),
        Directive.deadline.asc().nulls_last(),
    )

    q = q.offset((page - 1) * limit).limit(limit)
    rows = (await db.execute(q)).all()

    items = []
    for d, c in rows:
        items.append(
            {
                "case_id": str(c.id),
                "case_number": c.case_number,
                "court_name": c.court_name,
                "directive": {
                    "id": str(d.id),
                    "case_id": str(d.case_id),
                    "directive_text": d.directive_text,
                    "source_paragraph": d.source_paragraph,
                    "confidence_score": d.confidence_score,
                    "owner_designation": d.owner_designation,
                    "owner_department": d.owner_department,
                    "deadline": d.deadline.isoformat() if d.deadline else None,
                    "deadline_basis": d.deadline_basis,
                    "status": d.status.value,
                    "risk_level": d.risk_level.value if d.risk_level else None,
                    "requires_human_review": d.requires_human_review,
                    "directive_type": d.directive_type,
                    "is_enforceable": d.is_enforceable,
                    "legal_confidence": d.legal_confidence,
                    "deadline_convention": d.deadline_convention,
                    "verified_by": str(d.verified_by) if d.verified_by else None,
                    "verified_at": d.verified_at.isoformat() if d.verified_at else None,
                    "notes": d.notes,
                },
            }
        )

    return {"items": items, "page": page, "limit": limit}

