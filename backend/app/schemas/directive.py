from datetime import date, datetime

from pydantic import BaseModel

from app.models.directive import DirectiveStatus, RiskLevel


class DirectiveOut(BaseModel):
    id: str
    case_id: str
    directive_text: str
    source_paragraph: str | None = None
    confidence_score: float | None = None
    owner_designation: str
    owner_department: str | None = None
    deadline: date | None = None
    deadline_basis: str | None = None
    status: DirectiveStatus
    risk_level: RiskLevel | None = None
    requires_human_review: bool
    directive_type: str | None = None
    is_enforceable: bool = True
    legal_confidence: float | None = None
    deadline_convention: str | None = None
    verified_by: str | None = None
    verified_at: datetime | None = None
    notes: str | None = None


class DirectiveVerifyIn(BaseModel):
    id: str
    directive_text: str
    source_paragraph: str | None = None
    confidence_score: float | None = None
    owner_designation: str
    owner_department: str | None = None
    deadline: date | None = None
    deadline_basis: str | None = None
    requires_human_review: bool
    directive_type: str | None = None
    is_enforceable: bool = True
    notes: str | None = None


class DirectiveStatusUpdateIn(BaseModel):
    status: DirectiveStatus
