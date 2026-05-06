from __future__ import annotations

import asyncio
import logging
import re
from datetime import date, datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models.audit_log import AuditAction
from app.models.case import Case, CaseStatus
from app.models.directive import Directive, DirectiveStatus
from app.models.user import User
from app.services.audit_service import append_audit_log
from app.services.llm_extraction_service import extract_case_metadata, extract_directives, map_responsibilities
from app.services.ocr_service import extract_text_from_pdf
from app.services.rules_engine import DeadlineResult, compute_deadline
from app.services.risk_calculator import compute_risk

log = logging.getLogger(__name__)

SYSTEM_ACTOR_EMAIL = "system@aadeshpaalan"

# Directive types that represent real government execution tasks
_GOVT_TYPES = {"government_action", "administrative", "ongoing_injunction", "financial", "private_party"}

# ORDER section header patterns — checked in priority order
_ORDER_HEADERS = [
    r"\bO\s+R\s+D\s+E\s+R\b",
    r"\bFINAL\s+ORDER\b",
    r"\bOPERATIVE\s+PORTION\b",
    r"\bORDER\b",
    r"In\s+the\s+result[,\.]",
    r"For\s+the\s+aforesaid\s+reasons[,\.]",
    r"For\s+the\s+above\s+reasons[,\.]",
    r"In\s+view\s+of\s+the\s+above[,\.]",
    r"In\s+view\s+of\s+the\s+above[,\s]",
    r"this\s+petition\s+succeeds",
    r"petition\s+is\s+(?:hereby\s+)?allowed",
    r"petition\s+is\s+(?:hereby\s+)?dismissed",
    r"writ\s+petition\s+is\s+(?:hereby\s+)?allowed",
    r"I\s+pass\s+the\s+following",
    r"following\s+order\s+is\s+passed",
    r"directed\s+to\s+furnish",
    r"directed\s+to\s+pay\s+cost",
    r"mandamus\s+issues?\s+to",
    r"a\s+writ\s+of\s+(?:certiorari|mandamus)\s+issues?",
    r"Accordingly[,\.]",
]


def _detect_operative_section(
    full_text: str,
    page_chunks: list[dict] | None,
    max_chars: int,
) -> tuple[str, bool, bool]:
    """
    Returns (text_for_llm, found_header, is_fallback).

    Step 1: scan for explicit ORDER section headers.
    Step 2: fallback to last 20% of document.
    Step 3: fallback to full tail (max_chars from end).
    """
    # Step 1: try explicit headers
    for pattern in _ORDER_HEADERS:
        m = re.search(pattern, full_text, re.IGNORECASE)
        if m:
            section = full_text[m.start():]
            # Annotate with page numbers if chunks available
            if page_chunks:
                # Find which page the match falls on
                char_pos = m.start()
                running = 0
                for chunk in page_chunks:
                    chunk_len = len(chunk.get("text", ""))
                    if running + chunk_len >= char_pos:
                        # Take from this page onwards
                        idx = page_chunks.index(chunk)
                        tail = page_chunks[idx:]
                        section = "\n\n".join(
                            f"[PAGE {c['page']}]\n{c['text']}" for c in tail if c.get("text")
                        )
                        break
                    running += chunk_len + 1
            return section[:max_chars], True, False

    # Step 2: last 20% of document
    log.warning("No ORDER header found — using last 20%% of document as operative section")
    cutoff = max(0, int(len(full_text) * 0.80))
    if page_chunks:
        cutoff_page = max(1, int(len(page_chunks) * 0.80))
        tail_chunks = page_chunks[cutoff_page:]
        if tail_chunks:
            section = "\n\n".join(
                f"[PAGE {c['page']}]\n{c['text']}" for c in tail_chunks if c.get("text")
            )
            return section[:max_chars], False, True
    return full_text[cutoff:][:max_chars], False, True


async def _get_system_actor(db: AsyncSession) -> User:
    u = (await db.execute(select(User).where(User.email == SYSTEM_ACTOR_EMAIL))).scalars().first()
    if u is None:
        u = (await db.execute(select(User).order_by(User.created_at.asc()).limit(1))).scalars().first()
    if u is None:
        raise RuntimeError("No users exist. Run seed.py first.")
    return u


def _deadline_convention_code(time_expr: str, deadline_res: DeadlineResult) -> str | None:
    if not time_expr:
        return "no_deadline"
    basis = (deadline_res.basis or "").lower()
    expr = time_expr.lower().strip()
    if any(p in expr for p in ("forthwith", "immediately", "immediate", "at once")):
        return "KHC_forthwith_3wd"
    if any(p in basis for p in ("till further orders", "ongoing")):
        return "ongoing"
    if "working days" in basis:
        return "working_days_from_order"
    if "weeks" in basis:
        return "weeks_from_order"
    if "months" in basis:
        return "months_from_order"
    if "days" in basis:
        return "days_from_order"
    if "specific" in basis or "stated in order" in basis:
        return "explicit_date"
    if deadline_res.deadline is None:
        return "no_deadline"
    return None


async def process_case_async(db: AsyncSession, case_id: str) -> None:
    system = await _get_system_actor(db)
    case = (await db.execute(select(Case).where(Case.id == case_id))).scalars().first()
    if case is None:
        return

    await append_audit_log(db, table_name="cases", record_id=case.id,
        action=AuditAction.UPDATED, officer_id=system.id, officer_name=system.name,
        new_value={"event": "processing_started"})
    await db.commit()

    # ── OCR ───────────────────────────────────────────────────────────────────
    ocr = extract_text_from_pdf(case.pdf_path)
    case.raw_text = ocr["text"]
    case.ocr_confidence = float(ocr["confidence"])
    await append_audit_log(db, table_name="cases", record_id=case.id,
        action=AuditAction.UPDATED, officer_id=system.id, officer_name=system.name,
        new_value={"event": "ocr_completed", "method": ocr["method"],
                   "confidence": ocr["confidence"], "pages": ocr["pages"]})
    await db.commit()

    if not settings.llm_api_key:
        raise RuntimeError("llm_API_KEY not configured.")

    # ── PASS 1: Metadata + party mapping ─────────────────────────────────────
    metadata = await extract_case_metadata(
        llm_api_key=settings.llm_api_key,
        judgment_text=case.raw_text or "",
        db=db, case_id=case.id,
        officer_id=system.id, officer_name=system.name,
    )

    if metadata.case_number and case.case_number == "TBD":
        case.case_number = metadata.case_number
    if metadata.court_name and case.court_name == "TBD":
        case.court_name = metadata.court_name

    # FIX 3: resolve order_date strictly from metadata — never use today
    order_date: date | None = None
    if metadata.order_date:
        try:
            from dateutil.parser import parse as dt_parse
            order_date = dt_parse(metadata.order_date, dayfirst=True, fuzzy=True).date()
            if case.judgment_date is None:
                case.judgment_date = order_date
        except Exception:
            pass
    if order_date is None:
        order_date = case.judgment_date  # may still be None — handled below

    await db.commit()

    # ── PASS 2: Extract operative directives ──────────────────────────────────
    from app.services.llm_extraction_service import _PASS2_CHARS
    operative_text, found_header, is_fallback = _detect_operative_section(
        full_text=case.raw_text or "",
        page_chunks=ocr.get("chunks"),
        max_chars=_PASS2_CHARS,
    )
    if not found_header:
        log.warning("case %s: no ORDER header — fallback section used", case.id)

    raw_directives = await extract_directives(
        llm_api_key=settings.llm_api_key,
        judgment_text=case.raw_text or "",
        operative_text=operative_text,
        is_fallback=is_fallback,
        db=db, case_id=case.id,
        officer_id=system.id, officer_name=system.name,
        parties=metadata.parties,
    )

    if not raw_directives:
        log.warning("case %s: no operative section detected — results may be incomplete", case.id)

    # ── PASS 3: Normalize — owner resolution + confidence capping ─────────────
    normalized = await map_responsibilities(
        directives=raw_directives,
        db=db, case_id=case.id,
        officer_id=system.id, officer_name=system.name,
    )

    await append_audit_log(db, table_name="cases", record_id=case.id,
        action=AuditAction.UPDATED, officer_id=system.id, officer_name=system.name,
        new_value={"event": "llm_extraction_completed", "total": len(normalized)})
    await db.commit()

    # ── Rules engine + persist (FIX 6: only government_action types) ──────────
    persisted = 0
    for d in normalized:
        dtype = (d.get("directive_type") or "government_action").strip()

        # FIX 6: skip judicial_direction and private_party
        if dtype not in _GOVT_TYPES:
            continue

        time_expr = (d.get("time_expression") or "").strip()
        conf = float(d.get("confidence") or 0.0)
        assumption = bool(d.get("assumption_flag", False))

        # Penalty: directive from early pages is suspicious (likely from prayer/facts)
        source_page = int(d.get("source_page") or 0)
        if source_page > 0 and ocr.get("pages"):
            total_pages = ocr["pages"]
            if source_page < int(total_pages * 0.5):
                conf = min(conf, 0.6)

        # Cap confidence for fallback section (no explicit ORDER header found)
        if is_fallback:
            conf = min(conf, 0.6)

        # FIX 3: never use today — flag missing order_date
        if order_date is None:
            deadline_res = DeadlineResult(
                deadline=None,
                basis="Order date not found — requires human review",
                confidence=0.0,
                statute_reference="",
                requires_human_review=True,
            )
        else:
            deadline_res = compute_deadline(time_expr, order_date, case.court_name or "")

        # FIX 4: cap confidence
        if assumption or deadline_res.requires_human_review:
            conf = min(conf, 0.85)
        conf = min(conf, 0.95)

        requires_review = conf < 0.85 or deadline_res.requires_human_review or is_fallback

        directive = Directive(
            case_id=case.id,
            directive_text=d.get("directive_text") or "",
            source_paragraph=d.get("source_paragraph"),
            confidence_score=conf,
            owner_designation=d.get("owner_designation") or "Needs Manual Assignment",
            owner_department=dtype,
            deadline=deadline_res.deadline,
            deadline_basis=deadline_res.basis,
            status=DirectiveStatus.PENDING_REVIEW,
            risk_level=None,
            requires_human_review=requires_review,
            directive_type=dtype,
            is_enforceable=bool(d.get("is_enforceable", True)),
            legal_confidence=conf,
            deadline_convention=_deadline_convention_code(time_expr, deadline_res),
            verified_by=None,
            verified_at=None,
            notes=None,
        )
        directive.risk_level = compute_risk(directive, date.today())
        db.add(directive)
        persisted += 1

    case.status = CaseStatus.PENDING_REVIEW
    await append_audit_log(db, table_name="cases", record_id=case.id,
        action=AuditAction.UPDATED, officer_id=system.id, officer_name=system.name,
        new_value={"event": "rules_engine_completed", "persisted": persisted})
    await db.commit()


def launch_processing_task(case_id: str) -> None:
    from app.database import AsyncSessionLocal

    async def _run():
        async with AsyncSessionLocal() as db:
            try:
                await process_case_async(db, case_id)
            except Exception as exc:
                import logging
                logging.getLogger(__name__).error(
                    "Processing failed for case %s: %s", case_id, exc, exc_info=True)

    asyncio.create_task(_run())
