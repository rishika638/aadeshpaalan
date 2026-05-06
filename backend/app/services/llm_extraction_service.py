from __future__ import annotations

import asyncio
import json
import re
from dataclasses import dataclass, field
from difflib import SequenceMatcher

from groq import Groq
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.audit_log import AuditAction
from app.services.audit_service import append_audit_log
from app.utils.org_mapping import map_responsibility_to_designation


MODEL = "llama-3.3-70b-versatile"
_PASS1_CHARS = 3000
_PASS2_CHARS = 12000

_SKIP = {"Concerned Authority", "Needs Manual Assignment", ""}
_PRIVATE_PFX = "[PRIVATE PARTY"
_JUDICIAL_PFX = "[JUDICIAL OFFICER"


class LLMExtractionError(RuntimeError):
    pass


@dataclass
class CaseMetadata:
    case_number: str | None
    court_name: str | None
    order_date: str | None
    parties: dict = field(default_factory=dict)
    subject_matter: str | None = None


def _parse_json_strict(s: str) -> dict | list:
    cleaned = s.strip()
    if cleaned.startswith("```"):
        lines = [l for l in cleaned.split("\n") if not l.strip().startswith("```")]
        cleaned = "\n".join(lines).strip()
    try:
        return json.loads(cleaned)
    except Exception as e:
        raise LLMExtractionError(f"LLM did not return valid JSON: {e}. Raw: {s[:200]!r}") from e


# BUG 2: enforce short source_paragraph format — 50 char threshold
def _normalize_source_paragraph(raw: str | None) -> str | None:
    if not raw:
        return raw
    raw = raw.strip()
    # Already correct: starts with Page/Para and short enough
    if re.match(r"^Page\s+\d+", raw, re.IGNORECASE) and len(raw) <= 50:
        return raw
    if re.match(r"^Para\s+\d+", raw, re.IGNORECASE) and len(raw) <= 20:
        return raw
    # LLM put text content here — extract page/para numbers
    page_m = re.search(r"[Pp]age\s*(\d+)", raw)
    para_m = re.search(r"[Pp]ara(?:graph)?\s*(\d+)", raw)
    if page_m and para_m:
        return f"Page {page_m.group(1)}, Para {para_m.group(1)}"
    if page_m:
        return f"Page {page_m.group(1)}"
    if para_m:
        return f"Para {para_m.group(1)}"
    if len(raw) > 50:
        return "Location unresolved"
    return raw


# BUG 3: fuzzy deduplication
def _word_set(text: str) -> set[str]:
    return set(re.findall(r"\w+", text.lower()))


def _similarity(a: str, b: str) -> float:
    return SequenceMatcher(None, a.lower(), b.lower()).ratio()


def deduplicate_directives(directives: list[dict]) -> list[dict]:
    kept: list[dict] = []
    for candidate in directives:
        text_c = (candidate.get("directive_text") or "").strip()
        is_dup = False
        for i, existing in enumerate(kept):
            text_e = (existing.get("directive_text") or "").strip()
            if _similarity(text_c, text_e) >= 0.85:
                # Keep higher confidence; tie-break by later page
                conf_c = float(candidate.get("confidence") or 0)
                conf_e = float(existing.get("confidence") or 0)
                page_c = int(candidate.get("source_page") or 0)
                page_e = int(existing.get("source_page") or 0)
                if conf_c > conf_e or (conf_c == conf_e and page_c > page_e):
                    kept[i] = candidate
                is_dup = True
                break
        if not is_dup:
            kept.append(candidate)
    return kept


async def _call_groq_json(
    *,
    groq_api_key: str,
    system_prompt: str,
    user_prompt: str,
    db: AsyncSession,
    case_id: str,
    officer_id: str,
    officer_name: str,
    pass_name: str,
) -> dict | list:
    last_err: Exception | None = None
    for attempt in range(3):
        try:
            client = Groq(api_key=groq_api_key)
            response = client.chat.completions.create(
                model=MODEL,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                temperature=0.1,
                response_format={"type": "json_object"},
            )
            parsed = _parse_json_strict(response.choices[0].message.content)
            await append_audit_log(
                db, table_name="cases", record_id=case_id,
                action=AuditAction.UPDATED, officer_id=officer_id,
                officer_name=officer_name, old_value=None,
                new_value={"event": "groq_call", "model": MODEL, "pass": pass_name},
            )
            return parsed
        except LLMExtractionError:
            raise
        except Exception as e:
            last_err = e
            if attempt < 2:
                await asyncio.sleep(2 ** attempt)
    raise LLMExtractionError(f"Groq call failed after retries: {last_err}")


# ── PASS 1: Metadata + full party mapping ─────────────────────────────────────

async def extract_case_metadata(
    *,
    llm_api_key: str,
    judgment_text: str,
    db: AsyncSession,
    case_id: str,
    officer_id: str,
    officer_name: str,
) -> CaseMetadata:
    from app.config import settings
    groq_key = settings.groq_api_key or llm_api_key

    system = (
        "Extract metadata from an Indian court judgment header. "
        "Return JSON with keys: "
        "case_number (string), "
        "court_name (string), "
        "order_date (string YYYY-MM-DD — from header like 'DATED THIS THE 15TH DAY OF DECEMBER, 2022'), "
        "subject_matter (one sentence), "
        "parties (object — map EVERY respondent reference to their full designation from the cause title: "
        "{'R1': 'State of Karnataka', 'R2': 'Deputy Commissioner', "
        "'1st respondent': 'Regional Passport Officer, Bengaluru', ...}). "
        "Return ONLY valid JSON."
    )
    data = await _call_groq_json(
        groq_api_key=groq_key,
        system_prompt=system,
        user_prompt=f"Extract metadata:\n\n{judgment_text[:_PASS1_CHARS]}",
        db=db, case_id=case_id, officer_id=officer_id, officer_name=officer_name,
        pass_name="pass1_metadata",
    )
    if not isinstance(data, dict):
        data = {}
    return CaseMetadata(
        case_number=data.get("case_number"),
        court_name=data.get("court_name"),
        order_date=data.get("order_date"),
        parties=data.get("parties") or {},
        subject_matter=data.get("subject_matter"),
    )


# ── PASS 2: Operative directive extraction ────────────────────────────────────

async def extract_directives(
    *,
    llm_api_key: str,
    judgment_text: str,
    operative_text: str | None = None,
    is_fallback: bool = False,
    db: AsyncSession,
    case_id: str,
    officer_id: str,
    officer_name: str,
    page_chunks: list[dict] | None = None,
    parties: dict | None = None,
) -> list[dict]:
    from app.config import settings
    groq_key = settings.groq_api_key or llm_api_key

    # Use pre-detected operative section if provided, else fall back to tail pages
    if operative_text:
        text_for_llm = operative_text[:_PASS2_CHARS]
    elif page_chunks:
        tail = page_chunks[-8:] if len(page_chunks) > 8 else page_chunks
        text_for_llm = "\n\n".join(
            f"[PAGE {c['page']}]\n{c['text']}" for c in tail if c.get("text")
        )[:_PASS2_CHARS]
    else:
        text_for_llm = judgment_text[-_PASS2_CHARS:]

    parties_ctx = ""
    if parties:
        parties_ctx = "PARTY LIST:\n" + "\n".join(f"  {k} = {v}" for k, v in parties.items()) + "\n\n"

    fallback_note = (
        "NOTE: No explicit ORDER section header was found. "
        "This is the concluding section of the judgment. "
        "Extract any operative directives found here.\n\n"
    ) if is_fallback else ""

    system = (
        "You extract operative government directives from Indian High Court judgments.\n"
        "ONLY extract from the final ORDER/DIRECTIONS section.\n"
        "IGNORE: facts, submissions, analysis, observations, case law.\n"
        "VALID patterns: 'is directed', 'shall', 'is hereby directed', 'mandamus issues', 'Registry is directed'.\n\n"
        "EMBEDDED DIRECTIVES:\n"
        "Some judgments embed directives in final paragraph "
        "without numbered ORDER. These are valid.\n"
        "Look for: 'X is directed to furnish Y within Z weeks', "
        "'X shall pay cost', 'mandamus issues to X', "
        "'failing which X shall pay Y per day'.\n"
        "Include penalty clause in SAME directive_text.\n\n"
        "PRAYER FILTER — NEVER extract:\n"
        "- Sentences containing 'praying to', 'petitioner seeks', "
        "'it is prayed', 'directing the respondent to' when "
        "appearing BEFORE the ORDER section.\n"
        "- Reliefs listed under 'BETWEEN' or petition prayer.\n\n"
        "PARTY RESOLUTION (MANDATORY):\n"
        "- Resolve R1/R2/'1st respondent'/'2nd respondent' using the PARTY LIST.\n"
        "- NEVER output 'Concerned Authority'. Use 'Needs Manual Assignment' if unresolvable.\n"
        "- Petitioners are NEVER owners. Only respondents/Registry act.\n\n"
        "REFUND/RETURN RULE (CRITICAL):\n"
        "- If directive says 'shall be refunded to petitioner', 'shall be returned to petitioner',\n"
        "  'shall be restored to petitioner' — the petitioner is the BENEFICIARY not the actor.\n"
        "- Identify who holds the money or must perform the action (the respondent/bank).\n"
        "- If actor is a private bank or company: directive_type='private_party', is_enforceable=false.\n"
        "- If actor is a govt dept: directive_type='government_action'.\n\n"
        "SOURCE PARAGRAPH FORMAT (MANDATORY):\n"
        "- source_paragraph must contain ONLY the page number and paragraph number.\n"
        "- Use EXACTLY this format: 'Page X, Para Y' or 'Page X' if no para number.\n"
        "- Maximum 20 characters. Do NOT include any text content in source_paragraph.\n"
        "- The directive text belongs ONLY in directive_text field.\n\n"
        "DIRECTIVE TYPES: government_action | administrative | judicial_direction | "
        "private_party | ongoing_injunction | judicial_outcome | financial\n\n"
        "CONFIDENCE: cap at 0.85 if owner unresolved or time expression approximated. Never 1.0.\n\n"
        "Return JSON: {\"directives\": [{"
        "directive_text, "
        "source_paragraph (ONLY 'Page X, Para Y' format, max 20 chars), "
        "source_page (int), "
        "raw_responsible_entity, "
        "responsible_party_description, "
        "time_expression, "
        "assumption_flag (bool), "
        "directive_type, is_enforceable (bool), confidence, requires_human_review"
        "}]}"
    )

    data = await _call_groq_json(
        groq_api_key=groq_key,
        system_prompt=system,
        user_prompt=f"{parties_ctx}{fallback_note}Extract operative directives:\n\n{text_for_llm}",
        db=db, case_id=case_id, officer_id=officer_id, officer_name=officer_name,
        pass_name="pass2_directives",
    )

    if isinstance(data, dict):
        data = data.get("directives") or data.get("items") or (list(data.values())[0] if data else [])
    if not isinstance(data, list):
        raise LLMExtractionError("Pass 2 expected a JSON array.")

    # BUG 2: normalize source_paragraph to short format
    for d in data:
        d["source_paragraph"] = _normalize_source_paragraph(d.get("source_paragraph"))

    # BUG 3: deduplicate before returning
    data = deduplicate_directives(data)

    # Change 1d: filter out prayer clauses that slipped through
    _PRAYER_SIGNALS = [
        "praying to", "petitioner seeks", "it is prayed",
        "prayers sought", "reliefs sought",
        "petition is filed seeking", "seeking issuance of",
    ]

    def _is_prayer(text: str) -> bool:
        t = text.lower()
        return any(p in t for p in _PRAYER_SIGNALS)

    data = [d for d in data if not _is_prayer(d.get("directive_text") or "")]

    return data


# ── PASS 3: Normalization — owner resolution + confidence capping ─────────────

async def map_responsibilities(
    *,
    directives: list[dict],
    db: AsyncSession,
    case_id: str,
    officer_id: str,
    officer_name: str,
) -> list[dict]:
    mapped: list[dict] = []

    for d in directives:
        out = dict(d)
        dtype = (out.get("directive_type") or "").strip()
        resp = (out.get("responsible_party_description") or "").strip()
        assumption = bool(out.get("assumption_flag", False))

        if dtype in ("judicial_outcome", "private_party"):
            out["owner_designation"] = "Needs Manual Assignment"
            out["is_enforceable"] = False
            out["requires_human_review"] = True
            out["confidence"] = min(float(out.get("confidence") or 0.5), 0.85)
            mapped.append(out)
            continue

        if dtype == "administrative":
            resp_admin = (out.get("responsible_party_description") or "").strip().lower()
            if "registry" in resp_admin or "registrar" in resp_admin or not resp_admin:
                out["owner_designation"] = "Registrar, Karnataka High Court"
                out["is_enforceable"] = True
                out["requires_human_review"] = False
            else:
                m = map_responsibility_to_designation(resp_admin)
                designation = m.designation
                if designation.startswith(_PRIVATE_PFX) or designation.startswith(_JUDICIAL_PFX):
                    out["owner_designation"] = "Needs Manual Assignment"
                    out["is_enforceable"] = False
                    out["requires_human_review"] = True
                elif designation not in _SKIP:
                    out["owner_designation"] = designation
                    out["requires_human_review"] = m.requires_human_review
                else:
                    out["owner_designation"] = "Needs Manual Assignment"
                    out["requires_human_review"] = True
                out["is_enforceable"] = True
            mapped.append(out)
            continue

        if resp and resp not in _SKIP:
            m = map_responsibility_to_designation(resp)
            designation = m.designation
            if designation.startswith(_PRIVATE_PFX) or designation.startswith(_JUDICIAL_PFX):
                out["owner_designation"] = "Needs Manual Assignment"
                out["is_enforceable"] = False
                out["requires_human_review"] = True
            elif designation not in _SKIP:
                out["owner_designation"] = designation
                out["requires_human_review"] = bool(out.get("requires_human_review")) or m.requires_human_review
            else:
                out["owner_designation"] = "Needs Manual Assignment"
                out["requires_human_review"] = True
        else:
            out["owner_designation"] = "Needs Manual Assignment"
            out["requires_human_review"] = True

        raw_conf = float(out.get("confidence") or 0.5)
        if assumption or out["owner_designation"] == "Needs Manual Assignment":
            raw_conf = min(raw_conf, 0.85)
        out["confidence"] = min(raw_conf, 0.95)

        mapped.append(out)

    await append_audit_log(
        db, table_name="cases", record_id=case_id,
        action=AuditAction.UPDATED, officer_id=officer_id,
        officer_name=officer_name, old_value=None,
        new_value={"event": "pass3_normalization", "directives": len(mapped)},
    )
    return mapped
