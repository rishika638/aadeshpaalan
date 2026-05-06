from __future__ import annotations

from dataclasses import dataclass


# ── Mapping table ────────────────────────────────────────────────────────────
#
# Format: (keyword_phrase, designation, priority)
#
# priority 10 = very specific (long, exact phrases) — matched first
# priority  5 = standard department / role names
# priority  1 = broad / generic fallbacks — matched last
#
# The matcher iterates in DESCENDING priority order, so more-specific
# entries always win over shorter or vaguer ones.

_ORG_ENTRIES: list[tuple[str, str, int]] = [

    # ── Specific Karnataka bodies (p=10) ─────────────────────────────────────
    ("karnataka state pollution control board", "Member Secretary, KSPCB", 10),
    ("kspcb", "Member Secretary, KSPCB", 10),
    ("bruhat bengaluru mahanagara palike", "Chief Commissioner, BBMP", 10),
    ("bbmp", "Chief Commissioner, BBMP", 10),
    ("bangalore water supply", "Chairman, BWSSB", 10),
    ("bwssb", "Chairman, BWSSB", 10),
    ("bengaluru development authority", "Commissioner, BDA", 10),
    ("bda", "Commissioner, BDA", 10),
    ("bescom", "Managing Director, BESCOM", 10),
    ("ksrtc", "Managing Director, KSRTC", 10),
    ("kuws&db", "Managing Director, KUWS&DB", 10),
    ("kuwsdb", "Managing Director, KUWS&DB", 10),
    ("karnataka industrial areas development board", "Chief Executive Officer, KIADB", 10),
    ("kiadb", "Chief Executive Officer, KIADB", 10),
    ("karnataka housing board", "Chairman, Karnataka Housing Board", 10),
    ("khb", "Chairman, Karnataka Housing Board", 10),
    ("karnataka road development corporation", "Managing Director, KRDCL", 10),
    ("krdcl", "Managing Director, KRDCL", 10),

    # ── Registry & Police (p=10) ────────────────────────────────────────────
    ("marimallappas", "Principal, Marimallappas PU College, Mysuru", 10),
    ("marimallappas", "Principal, Marimallappas PU College, Mysuru", 10),
    ("karnataka information commission", "State Chief Information Commissioner, Karnataka", 10),
    ("state information commission", "State Chief Information Commissioner, Karnataka", 10),
    ("phonepe", "[PRIVATE PARTY — not a government officer]", 10),
    ("paytm", "[PRIVATE PARTY — not a government officer]", 10),
    ("google pay", "[PRIVATE PARTY — not a government officer]", 10),
    ("sbi", "[PRIVATE PARTY — not a government officer]", 10),
    ("kotak mahindra bank", "[PRIVATE PARTY — not a government officer]", 10),
    ("phonepe", "[PRIVATE PARTY — not a government officer]", 10),
    ("paytm", "[PRIVATE PARTY — not a government officer]", 10),
    ("google pay", "[PRIVATE PARTY — not a government officer]", 10),
    ("regional passport officer", "Regional Passport Officer, Ministry of External Affairs", 10),
    ("passport officer", "Regional Passport Officer, Ministry of External Affairs", 10),
    ("passport seva kendra", "Regional Passport Officer, Ministry of External Affairs", 10),
    ("assistant commissioner of commercial taxes", "Assistant Commissioner of Commercial Taxes, Karnataka", 10),
    ("joint commissioner of commercial taxes", "Joint Commissioner of Commercial Taxes, Karnataka", 10),
    ("deputy commissioner of commercial taxes", "Deputy Commissioner of Commercial Taxes, Karnataka", 10),
    ("commercial tax department", "Commissioner of Commercial Taxes, Karnataka", 10),
    ("central government counsel", "[PRIVATE PARTY — not a government action owner]", 10),
    ("cgc", "[PRIVATE PARTY — not a government action owner]", 10),
    ("registry of this court", "Registrar, Karnataka High Court", 10),
    ("registry of the court", "Registrar, Karnataka High Court", 10),
    ("registry is directed", "Registrar, Karnataka High Court", 10),
    ("registry", "Registrar, Karnataka High Court", 10),
    ("registrar of the high court", "Registrar, Karnataka High Court", 10),
    ("registrar, karnataka high court", "Registrar, Karnataka High Court", 10),
    ("registrar of this court", "Registrar, Karnataka High Court", 10),
    ("north cen police", "Commissioner of Police, Bengaluru", 10),
    ("jurisdictional police", "Commissioner of Police (Jurisdictional)", 10),
    ("investigating officer", "Station House Officer (Concerned Police Station)", 10),
    ("io ", "Station House Officer (Concerned Police Station)", 10),
    # ── Courts & Tribunals (p=10) ─────────────────────────────────────────────
    ("principal judge, family court", "Principal Judge, Family Court", 10),
    ("family court", "Principal Judge, Family Court", 10),
    ("national green tribunal", "Registrar, NGT", 10),
    ("ngt", "Registrar, NGT", 10),
    ("state environment impact assessment authority", "Member Secretary, SEIAA", 10),
    ("seiaa", "Member Secretary, SEIAA", 10),
    ("national highways authority", "Chief Engineer, NHAI", 10),
    ("nhai", "Chief Engineer, NHAI", 10),
    ("jaipur development authority", "Commissioner, Jaipur Development Authority", 10),
    ("jda", "Commissioner, Jaipur Development Authority", 10),
    ("delhi development authority", "Vice Chairman, DDA", 10),
    ("dda", "Vice Chairman, DDA", 10),

    # ── Specific Principal Secretary portfolios (p=9) ─────────────────────────
    ("principal secretary (mines)", "Principal Secretary (Mines)", 9),
    ("principal secretary (forest)", "Principal Secretary (Forest)", 9),
    ("principal secretary (environment)", "Principal Secretary (Environment)", 9),
    ("principal secretary (law)", "Principal Secretary (Law)", 9),
    ("principal secretary (home)", "Principal Secretary (Home)", 9),
    ("principal secretary (revenue)", "Principal Secretary (Revenue)", 9),
    ("principal secretary (urban development)", "Principal Secretary (Urban Development)", 9),
    ("principal secretary (water resources)", "Principal Secretary (Water Resources)", 9),
    ("principal secretary (irrigation)", "Principal Secretary (Irrigation)", 9),
    ("principal secretary (health)", "Principal Secretary (Health)", 9),
    ("principal secretary (education)", "Principal Secretary (Education)", 9),
    ("principal secretary (social welfare)", "Principal Secretary (Social Welfare)", 9),
    ("principal secretary (labour)", "Principal Secretary (Labour)", 9),
    ("principal secretary (finance)", "Principal Secretary (Finance)", 9),

    # ── Specific department / directorate (p=8) ───────────────────────────────
    ("information commissioner", "State Information Commissioner, Karnataka", 8),
    ("pre university education", "Director, Department of Pre-University Education", 8),
    ("department of pre university", "Director, Department of Pre-University Education", 8),
    ("joint director, pre university", "Joint Director, Department of Pre-University Education", 8),
    ("deputy director for pre university", "Deputy Director, Pre-University Education, Mysuru District", 8),
    ("deputy director, pre university", "Deputy Director, Pre-University Education", 8),
    ("principal, government pu college", "Principal, Government PU College (concerned)", 8),
    ("principal, government college", "Principal, Government College (concerned)", 8),
    ("director of mines and geology", "Director of Mines & Geology", 8),
    ("director, mines and geology", "Director of Mines & Geology", 8),
    ("mines and geology", "Director of Mines & Geology", 8),
    ("director, ground water", "Director, Ground Water Department", 8),
    ("ground water department", "Director, Ground Water Department", 8),
    ("groundwater department", "Director, Ground Water Department", 8),
    ("principal chief conservator of forests", "Principal Chief Conservator of Forests", 8),
    ("pccf", "Principal Chief Conservator of Forests", 8),
    ("director general of police", "Director General of Police", 8),
    ("dgp", "Director General of Police", 8),
    ("inspector general of police", "Inspector General of Police", 8),
    ("director, land records", "Director, Land Records", 8),
    ("director, survey", "Director, Survey & Settlement", 8),
    ("town planning", "Director, Town Planning", 8),
    ("director, medical", "Director, Medical & Health Services", 8),
    ("chief engineer, pwd", "Chief Engineer, PWD", 8),
    ("chief engineer, roads", "Chief Engineer, Roads & Buildings", 8),
    ("advocate general", "Advocate General", 8),
    ("government pleader", "Government Pleader", 8),
    ("solicitor general", "Solicitor General of India", 8),
    ("attorney general", "Attorney General of India", 8),
    ("registrar general, high court", "Registrar General, High Court", 8),

    # ── Named roles without portfolio qualifier (p=7) ─────────────────────────
    ("chief secretary", "Chief Secretary", 7),
    ("additional chief secretary", "Additional Chief Secretary", 7),
    ("divisional commissioner", "Divisional Commissioner", 7),
    ("district collector", "District Collector", 7),
    ("deputy commissioner", "Deputy Commissioner", 7),
    ("assistant commissioner", "Assistant Commissioner", 7),
    ("tahsildar", "Tahsildar", 7),
    ("superintendent of police", "Superintendent of Police", 7),
    ("sub-registrar", "Sub-Registrar", 7),
    ("district registrar", "District Registrar", 7),
    ("municipal commissioner", "Municipal Commissioner", 7),
    ("chief officer, municipal council", "Chief Officer, Municipal Council", 7),
    ("executive officer", "Executive Officer, Local Body", 7),

    # ── Generic department keywords (p=5) ─────────────────────────────────────
    ("mines department", "Principal Secretary (Mines)", 5),
    ("mining department", "Principal Secretary (Mines)", 5),
    ("forest department", "Principal Chief Conservator of Forests", 5),
    ("environment department", "Principal Secretary (Environment)", 5),
    ("ecology", "Secretary, Department of Ecology & Environment", 5),
    ("revenue department", "Principal Secretary (Revenue)", 5),
    ("land records", "Director, Land Records", 5),
    ("survey department", "Director, Survey & Settlement", 5),
    ("groundwater", "Director, Ground Water Department", 5),
    ("ground water", "Director, Ground Water Department", 5),
    ("water resources", "Principal Secretary (Water Resources)", 5),
    ("irrigation department", "Principal Secretary (Irrigation)", 5),
    ("public works department", "Chief Engineer, PWD", 5),
    ("public works", "Chief Engineer, PWD", 5),
    ("pwd", "Chief Engineer, PWD", 5),
    ("roads and buildings", "Chief Engineer, Roads & Buildings", 5),
    ("urban development", "Principal Secretary (Urban Development)", 5),
    ("municipal corporation", "Municipal Commissioner", 5),
    ("municipal council", "Chief Officer, Municipal Council", 5),
    ("nagar nigam", "Municipal Commissioner", 5),
    ("nagar palika", "Chief Officer, Nagar Palika", 5),
    ("nagar panchayat", "Chief Officer, Nagar Panchayat", 5),
    ("gram panchayat", "Panchayat Development Officer", 5),
    ("health department", "Principal Secretary (Health)", 5),
    ("medical", "Director, Medical & Health Services", 5),
    ("education department", "Principal Secretary (Education)", 5),
    ("social welfare", "Principal Secretary (Social Welfare)", 5),
    ("labour department", "Principal Secretary (Labour)", 5),
    ("finance department", "Principal Secretary (Finance)", 5),
    ("police department", "Superintendent of Police", 5),
    ("police", "Superintendent of Police", 5),
    ("registrar", "District Registrar", 5),
    ("high court", "Registrar General, High Court", 5),
    ("supreme court", "Registrar, Supreme Court of India", 5),
    ("tribunal", "Registrar, Tribunal", 5),
    ("encroachment", "Municipal Commissioner", 5),
    ("slp monitoring", "Principal Secretary (Law)", 5),
    # NOTE: "compliance report" intentionally removed — it is too generic and
    # would shadow higher-priority domain entries like "groundwater compliance report".

    # ── Skip flags — judicial officers & private parties (p=10) ──────────────
    ("learned magistrate", "[JUDICIAL OFFICER — not a government action item]", 10),
    ("concerned magistrate", "[JUDICIAL OFFICER — not a government action item]", 10),
    ("judicial magistrate", "[JUDICIAL OFFICER — not a government action item]", 10),
    ("hdfc bank", "[PRIVATE PARTY — not a government officer]", 10),
    ("yes bank", "[PRIVATE PARTY — not a government officer]", 10),
    ("icici bank", "[PRIVATE PARTY — not a government officer]", 10),
    ("axis bank", "[PRIVATE PARTY — not a government officer]", 10),
    ("state bank of india", "[PRIVATE PARTY — not a government officer]", 10),

    # ── Ultra-generic fallbacks (p=1) ─────────────────────────────────────────
    ("principal secretary", "Principal Secretary", 1),
    ("secretary to government", "Principal Secretary", 1),  # in Karnataka usage, "secretary to government" = Principal Secretary
    ("state government", "Chief Secretary", 1),
    ("state of ", "Chief Secretary", 1),
    ("union of india", "Secretary, Ministry of Law & Justice", 1),
    ("central government", "Secretary, Ministry of Law & Justice", 1),
    ("respondent", "Needs Manual Assignment", 1),
    ("concerned authority", "Needs Manual Assignment", 1),
    ("nodal officer", "Needs Manual Assignment", 1),
    ("competent authority", "Needs Manual Assignment", 1),
]

# Sort once at import time: highest priority first, then longest key (most specific) first
_ORG_ENTRIES_SORTED: list[tuple[str, str, int]] = sorted(
    _ORG_ENTRIES,
    key=lambda e: (e[2], len(e[0])),
    reverse=True,
)

# Expose a plain dict for code that needs ORG_MAP directly
ORG_MAP: dict[str, str] = {phrase: designation for phrase, designation, _ in _ORG_ENTRIES_SORTED}


# ── Result type ──────────────────────────────────────────────────────────────

@dataclass(frozen=True)
class OrgMappingResult:
    designation: str
    requires_human_review: bool
    matched_key: str | None
    priority: int  # 0 = no match


# ── Public API ───────────────────────────────────────────────────────────────

def map_responsibility_to_designation(responsible_party_description: str) -> OrgMappingResult:
    """
    Case-insensitive substring match against ORG_MAP keys.

    Matching rules:
    - Iterate in descending (priority, key-length) order so that more-specific
      entries always beat shorter / vaguer ones.
    - First match wins.
    - If nothing matches: designation = "Concerned Authority" and
      requires_human_review = True.

    The `requires_human_review` flag is True when:
    - No match is found, OR
    - The match resolves to "Concerned Authority" (catch-all phrases like
      "respondent", "competent authority", "nodal officer").
    """
    text = (responsible_party_description or "").strip().lower()
    if not text:
        return OrgMappingResult(
            designation="Concerned Authority",
            requires_human_review=True,
            matched_key=None,
            priority=0,
        )

    for phrase, designation, priority in _ORG_ENTRIES_SORTED:
        if phrase in text:
            is_catch_all = designation in ("Concerned Authority", "Needs Manual Assignment") or designation.startswith("[")
            return OrgMappingResult(
                designation=designation,
                requires_human_review=is_catch_all,
                matched_key=phrase,
                priority=priority,
            )

    return OrgMappingResult(
        designation="Needs Manual Assignment",
        requires_human_review=True,
        matched_key=None,
        priority=0,
    )
