import enum
import uuid
from datetime import date, datetime

from sqlalchemy import Column, Date, DateTime, Enum, Float, ForeignKey, String, Text, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin


class CaseStatus(str, enum.Enum):
    PROCESSING = "processing"
    PENDING_REVIEW = "pending_review"
    VERIFIED = "verified"
    ACTIVE = "active"
    CLOSED = "closed"


class Case(Base, TimestampMixin):
    __tablename__ = "cases"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    case_number: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    court_name: Mapped[str] = mapped_column(String(255), nullable=False)
    judgment_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    uploaded_by: Mapped[str] = mapped_column(String, ForeignKey("users.id"), nullable=False)
    upload_timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    status: Mapped[CaseStatus] = mapped_column(Enum(CaseStatus, name="case_status"), nullable=False)
    pdf_path: Mapped[str] = mapped_column(String(1024), nullable=False)
    raw_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    ocr_confidence: Mapped[float | None] = mapped_column(Float, nullable=True)

    directives: Mapped[list["Directive"]] = relationship(back_populates="case", cascade="all, delete-orphan")


from app.models.directive import Directive  # noqa: E402
