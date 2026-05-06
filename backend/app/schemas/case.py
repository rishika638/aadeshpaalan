from datetime import date, datetime

from pydantic import BaseModel

from app.models.case import CaseStatus
from app.schemas.directive import DirectiveOut, DirectiveVerifyIn


class CaseOut(BaseModel):
    id: str
    case_number: str
    court_name: str
    judgment_date: date | None = None
    uploaded_by: str
    upload_timestamp: datetime
    status: CaseStatus
    pdf_path: str
    raw_text: str | None = None
    ocr_confidence: float | None = None


class UploadResponse(BaseModel):
    case_id: str
    status: CaseStatus
    estimated_seconds: int = 60


class CaseStatusResponse(BaseModel):
    status: CaseStatus
    progress_percent: int
    message: str


class ReviewResponse(BaseModel):
    case: CaseOut
    directives: list[DirectiveOut]


class VerifyRequest(BaseModel):
    directives: list[DirectiveVerifyIn]


class CaseDetailResponse(BaseModel):
    id: str
    case_number: str
    court_name: str
    judgment_date: date | None = None
    status: CaseStatus
    directives: list[DirectiveOut]
    audit_logs: list[dict]
