"""initial

Revision ID: 0001_initial
Revises: 
Create Date: 2026-05-01

"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
from sqlalchemy.dialects.postgresql import ENUM


revision = "0001_initial"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # UUID generation
    op.execute('CREATE EXTENSION IF NOT EXISTS "pgcrypto";')

    # Enums
    case_status = ENUM(
        "processing",
        "pending_review",
        "verified",
        "active",
        "closed",
        name="case_status",
        create_type=False,
    )
    
    directive_status = ENUM(
        "pending_review",
        "verified",
        "in_progress",
        "completed",
        "overdue",
        "contempt_risk",
        name="directive_status",
        create_type=False,
    )
    
    risk_level = ENUM(
        "overdue",
        "critical",
        "due_soon",
        "watch",
        "compliant",
        name="risk_level",
        create_type=False,
    )
    
    user_role = ENUM(
        "uploader",
        "reviewer",
        "officer",
        "admin",
        name="user_role",
        create_type=False,
    )
    
    audit_action = ENUM(
        "created",
        "updated",
        "verified",
        "status_changed",
        "alert_sent",
        name="audit_action",
        create_type=False,
    )

    case_status.create(op.get_bind(), checkfirst=True)
    directive_status.create(op.get_bind(), checkfirst=True)
    risk_level.create(op.get_bind(), checkfirst=True)
    user_role.create(op.get_bind(), checkfirst=True)
    audit_action.create(op.get_bind(), checkfirst=True)

    # Tables
    op.create_table(
        "users",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("email", sa.String(length=320), nullable=False, unique=True),
        sa.Column("designation", sa.String(length=255), nullable=False),
        sa.Column("department", sa.String(length=255), nullable=False),
        sa.Column("role", user_role, nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )
    op.create_index("ix_users_email", "users", ["email"], unique=True)

    op.create_table(
        "cases",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("case_number", sa.String(length=255), nullable=False),
        sa.Column("court_name", sa.String(length=255), nullable=False),
        sa.Column("judgment_date", sa.Date(), nullable=True),
        sa.Column("uploaded_by", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("upload_timestamp", sa.DateTime(timezone=True), nullable=False),
        sa.Column("status", case_status, nullable=False),
        sa.Column("pdf_path", sa.String(length=1024), nullable=False),
        sa.Column("raw_text", sa.Text(), nullable=True),
        sa.Column("ocr_confidence", sa.Float(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )
    op.create_index("ix_cases_case_number", "cases", ["case_number"], unique=False)

    op.create_table(
        "directives",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("case_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("cases.id"), nullable=False),
        sa.Column("directive_text", sa.Text(), nullable=False),
        sa.Column("source_paragraph", sa.String(length=64), nullable=True),
        sa.Column("confidence_score", sa.Float(), nullable=True),
        sa.Column("owner_designation", sa.String(length=255), nullable=False),
        sa.Column("owner_department", sa.String(length=255), nullable=True),
        sa.Column("deadline", sa.Date(), nullable=True),
        sa.Column("deadline_basis", sa.String(length=512), nullable=True),
        sa.Column("status", directive_status, nullable=False),
        sa.Column("risk_level", risk_level, nullable=True),
        sa.Column("requires_human_review", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("verified_by", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("verified_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )
    op.create_index("ix_directives_case_id", "directives", ["case_id"], unique=False)

    op.create_table(
        "audit_logs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("table_name", sa.String(length=64), nullable=False),
        sa.Column("record_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("action", audit_action, nullable=False),
        sa.Column("officer_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("officer_name", sa.String(length=255), nullable=False),
        sa.Column("timestamp", sa.DateTime(timezone=True), nullable=False),
        sa.Column("old_value", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("new_value", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("ip_address", sa.String(length=64), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )
    op.create_index("ix_audit_logs_record_id", "audit_logs", ["record_id"], unique=False)

    # updated_at triggers for mutable tables (audit_logs is append-only)
    op.execute(
        """
        CREATE OR REPLACE FUNCTION set_updated_at()
        RETURNS TRIGGER AS $$
        BEGIN
            NEW.updated_at = now();
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql;
        """
    )
    for table in ("users", "cases", "directives"):
        op.execute(
            f"""
            DROP TRIGGER IF EXISTS trg_set_updated_at_{table} ON {table};
            CREATE TRIGGER trg_set_updated_at_{table}
            BEFORE UPDATE ON {table}
            FOR EACH ROW
            EXECUTE FUNCTION set_updated_at();
            """
        )

    # APPEND ONLY audit_logs: prevent UPDATE and DELETE
    op.execute(
        """
        CREATE OR REPLACE FUNCTION audit_logs_immutable()
        RETURNS TRIGGER AS $$
        BEGIN
            RAISE EXCEPTION 'audit_logs is append-only';
        END;
        $$ LANGUAGE plpgsql;
        """
    )
    op.execute("DROP TRIGGER IF EXISTS trg_audit_logs_no_update ON audit_logs;")
    op.execute(
        """
        CREATE TRIGGER trg_audit_logs_no_update
        BEFORE UPDATE ON audit_logs
        FOR EACH ROW
        EXECUTE FUNCTION audit_logs_immutable();
        """
    )
    op.execute("DROP TRIGGER IF EXISTS trg_audit_logs_no_delete ON audit_logs;")
    op.execute(
        """
        CREATE TRIGGER trg_audit_logs_no_delete
        BEFORE DELETE ON audit_logs
        FOR EACH ROW
        EXECUTE FUNCTION audit_logs_immutable();
        """
    )


def downgrade() -> None:
    op.execute("DROP TRIGGER IF EXISTS trg_audit_logs_no_update ON audit_logs;")
    op.execute("DROP TRIGGER IF EXISTS trg_audit_logs_no_delete ON audit_logs;")
    op.execute("DROP FUNCTION IF EXISTS audit_logs_immutable();")

    for table in ("users", "cases", "directives"):
        op.execute(f"DROP TRIGGER IF EXISTS trg_set_updated_at_{table} ON {table};")
    op.execute("DROP FUNCTION IF EXISTS set_updated_at();")

    op.drop_index("ix_audit_logs_record_id", table_name="audit_logs")
    op.drop_table("audit_logs")

    op.drop_index("ix_directives_case_id", table_name="directives")
    op.drop_table("directives")

    op.drop_index("ix_cases_case_number", table_name="cases")
    op.drop_table("cases")

    op.drop_index("ix_users_email", table_name="users")
    op.drop_table("users")

    op.execute('DROP EXTENSION IF EXISTS "pgcrypto";')

    sa.Enum(name="audit_action").drop(op.get_bind(), checkfirst=True)
    sa.Enum(name="user_role").drop(op.get_bind(), checkfirst=True)
    sa.Enum(name="risk_level").drop(op.get_bind(), checkfirst=True)
    sa.Enum(name="directive_status").drop(op.get_bind(), checkfirst=True)
    sa.Enum(name="case_status").drop(op.get_bind(), checkfirst=True)

