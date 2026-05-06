import enum
import uuid
from datetime import datetime

from sqlalchemy import Column, DateTime, Enum, ForeignKey, JSON, String
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin


class AuditAction(str, enum.Enum):
    CREATED = "created"
    UPDATED = "updated"
    VERIFIED = "verified"
    STATUS_CHANGED = "status_changed"
    ALERT_SENT = "alert_sent"


class AuditLog(Base, TimestampMixin):
    __tablename__ = "audit_logs"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    table_name: Mapped[str] = mapped_column(String(64), nullable=False)
    record_id: Mapped[str] = mapped_column(String, nullable=False, index=True)
    action: Mapped[AuditAction] = mapped_column(Enum(AuditAction, name="audit_action"), nullable=False)

    officer_id: Mapped[str] = mapped_column(String, ForeignKey("users.id"), nullable=False)
    officer_name: Mapped[str] = mapped_column(String(255), nullable=False)

    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    old_value: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    new_value: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    ip_address: Mapped[str | None] = mapped_column(String(64), nullable=True)
