import uuid
from datetime import datetime, timezone
from pathlib import Path

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.database import get_db
from app.models.audit_log import AuditAction
from app.models.case import Case, CaseStatus
from app.models.user import UserRole
from app.schemas.case import UploadResponse
from app.security import require_roles
from app.services.audit_service import append_audit_log
from app.services.processing_pipeline import launch_processing_task


router = APIRouter(prefix="/api", tags=["upload"])


MAX_BYTES = 50 * 1024 * 1024


@router.post("/upload", response_model=UploadResponse)
async def upload_judgment(
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    user=Depends(require_roles(UserRole.UPLOADER, UserRole.ADMIN)),
) -> UploadResponse:
    if file.content_type != "application/pdf":
        raise HTTPException(status_code=400, detail="Only PDF allowed")

    body = await file.read()
    if len(body) > MAX_BYTES:
        raise HTTPException(status_code=400, detail="File too large (max 50MB)")

    storage = Path(settings.storage_path)
    storage.mkdir(parents=True, exist_ok=True)
    name = f"{uuid.uuid4()}.pdf"
    path = storage / name
    path.write_bytes(body)

    case = Case(
        case_number="TBD",
        court_name="TBD",
        judgment_date=None,
        uploaded_by=user.id,
        upload_timestamp=datetime.now(timezone.utc),
        status=CaseStatus.PROCESSING,
        pdf_path=str(path),
        raw_text=None,
        ocr_confidence=None,
    )
    db.add(case)
    await db.flush()

    await append_audit_log(
        db,
        table_name="cases",
        record_id=case.id,
        action=AuditAction.CREATED,
        officer_id=user.id,
        officer_name=user.name,
        new_value={"event": "pdf_uploaded", "pdf_path": case.pdf_path, "size_bytes": len(body)},
    )
    await db.commit()

    launch_processing_task(case.id)
    return UploadResponse(case_id=case.id, status=case.status, estimated_seconds=60)

