import asyncio
from datetime import date, datetime, timezone

from sqlalchemy import select

from app.database import AsyncSessionLocal, engine
from app.models.audit_log import AuditAction
from app.models.case import Case, CaseStatus
from app.models.directive import Directive, DirectiveStatus, RiskLevel
from app.models.user import User, UserRole
from app.services.audit_service import append_audit_log
from app.models.base import Base

async def run() -> None:
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with AsyncSessionLocal() as db:
        # system actor
        system = (await db.execute(select(User).where(User.email == "system@aadeshpaalan"))).scalars().first()
        if system is None:
            system = User(
                name="AadeshPaalan System",
                email="system@aadeshpaalan",
                designation="System",
                department="System",
                role=UserRole.ADMIN,
                is_active=True,
            )
            db.add(system)
            await db.flush()

        # 3 test users
        users = [
            ("Reviewer User", "reviewer@karnataka.gov.in", "Section Officer (Legal)", "Law", UserRole.REVIEWER),
            ("Officer User", "officer@karnataka.gov.in", "Municipal Commissioner", "Urban Development", UserRole.OFFICER),
            ("Admin User", "admin@karnataka.gov.in", "Principal Secretary (Law)", "Law", UserRole.ADMIN),
        ]
        created_users = []
        for name, email, desig, dept, role in users:
            u = (await db.execute(select(User).where(User.email == email))).scalars().first()
            if u is None:
                u = User(
                    name=name,
                    email=email,
                    designation=desig,
                    department=dept,
                    role=role,
                    is_active=True,
                )
                db.add(u)
                await db.flush()
            created_users.append(u)

        uploader = created_users[2]  # admin also can upload

        # 2 sample cases
        case1 = Case(
            case_number="WP 1234/2025",
            court_name="High Court of Karnataka",
            judgment_date=date(2025, 3, 15),
            uploaded_by=uploader.id,
            upload_timestamp=datetime.now(timezone.utc),
            status=CaseStatus.VERIFIED,
            pdf_path="/app/storage/judgments/sample1.pdf",
            raw_text="(seed) sample judgment text",
            ocr_confidence=0.95,
        )
        case2 = Case(
            case_number="WP 5678/2025",
            court_name="High Court of Karnataka",
            judgment_date=date(2025, 4, 1),
            uploaded_by=uploader.id,
            upload_timestamp=datetime.now(timezone.utc),
            status=CaseStatus.VERIFIED,
            pdf_path="/app/storage/judgments/sample2.pdf",
            raw_text="(seed) sample judgment text",
            ocr_confidence=0.95,
        )
        db.add_all([case1, case2])
        await db.flush()

        directives = [
            Directive(
                case_id=case1.id,
                directive_text="Groundwater compliance report",
                source_paragraph="Para 12",
                confidence_score=0.9,
                owner_designation="Deputy Secretary, Revenue",
                owner_department="Revenue",
                deadline=date(2025, 4, 28),
                deadline_basis="Order date + 30 days (seed)",
                status=DirectiveStatus.VERIFIED,
                risk_level=RiskLevel.OVERDUE,
                requires_human_review=False,
                verified_by=created_users[0].id,
                verified_at=datetime.now(timezone.utc),
                notes=None,
            ),
            Directive(
                case_id=case1.id,
                directive_text="Encroachment removal",
                source_paragraph="Para 8",
                confidence_score=0.86,
                owner_designation="Municipal Commissioner",
                owner_department="Urban Development",
                deadline=date(2025, 5, 10),
                deadline_basis="Order date + 6 weeks (seed)",
                status=DirectiveStatus.VERIFIED,
                risk_level=RiskLevel.DUE_SOON,
                requires_human_review=False,
                verified_by=created_users[0].id,
                verified_at=datetime.now(timezone.utc),
                notes=None,
            ),
            Directive(
                case_id=case2.id,
                directive_text="SLP monitoring",
                source_paragraph="Para 3",
                confidence_score=0.8,
                owner_designation="Principal Secretary",
                owner_department="Law",
                deadline=date(2025, 7, 16),
                deadline_basis="Order date + 90 days (seed)",
                status=DirectiveStatus.VERIFIED,
                risk_level=RiskLevel.WATCH,
                requires_human_review=False,
                verified_by=created_users[0].id,
                verified_at=datetime.now(timezone.utc),
                notes=None,
            ),
        ]
        db.add_all(directives)
        await db.flush()

        # Audit logs
        await append_audit_log(
            db,
            table_name="cases",
            record_id=case1.id,
            action=AuditAction.CREATED,
            officer_id=uploader.id,
            officer_name=uploader.name,
            new_value={"event": "seed_case_created"},
        )
        for d in directives:
            await append_audit_log(
                db,
                table_name="directives",
                record_id=d.id,
                action=AuditAction.VERIFIED,
                officer_id=created_users[0].id,
                officer_name=created_users[0].name,
                new_value={"event": "seed_directive_verified"},
            )

        await db.commit()


if __name__ == "__main__":
    asyncio.run(run())

