import enum
import uuid
from datetime import date, datetime

from sqlalchemy import Boolean, Column, Date, DateTime, Enum, Float, ForeignKey, String, Text, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin


class DirectiveStatus(str, enum.Enum):
    PENDING_REVIEW = "pending_review"
    VERIFIED = "verified"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    OVERDUE = "overdue"
    CONTEMPT_RISK = "contempt_risk"


class RiskLevel(str, enum.Enum):
    OVERDUE = "overdue"
    CRITICAL = "critical"
    DUE_SOON = "due_soon"
    WATCH = "watch"
    COMPLIANT = "compliant"
    ARCHIVED_UNVERIFIED = "archived_unverified"


class Directive(Base, TimestampMixin):
    __tablename__ = "directives"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    case_id: Mapped[str] = mapped_column(String, ForeignKey("cases.id"), nullable=False, index=True)

    directive_text: Mapped[str] = mapped_column(Text, nullable=False)
    source_paragraph: Mapped[str | None] = mapped_column(String(64), nullable=True)
    confidence_score: Mapped[float | None] = mapped_column(Float, nullable=True)

    owner_designation: Mapped[str] = mapped_column(String(255), nullable=False)
    owner_department: Mapped[str | None] = mapped_column(String(255), nullable=True)

    deadline: Mapped[date | None] = mapped_column(Date, nullable=True)
    deadline_basis: Mapped[str | None] = mapped_column(String(512), nullable=True)

    status: Mapped[DirectiveStatus] = mapped_column(Enum(DirectiveStatus, name="directive_status"), nullable=False)
    risk_level: Mapped[RiskLevel | None] = mapped_column(Enum(RiskLevel, name="risk_level"), nullable=True)

    requires_human_review: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("true"))
    verified_by: Mapped[str | None] = mapped_column(String, ForeignKey("users.id"), nullable=True)
    verified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    directive_type: Mapped[str | None] = mapped_column(String(64), nullable=True)
    is_enforceable: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("true"))
    legal_confidence: Mapped[float | None] = mapped_column(Float, nullable=True)
    deadline_convention: Mapped[str | None] = mapped_column(String(128), nullable=True)

    case: Mapped["Case"] = relationship(back_populates="directives")


from app.models.case import Case  # noqa: E402
