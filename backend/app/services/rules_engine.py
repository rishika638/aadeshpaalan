from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import date, timedelta

from dateutil.relativedelta import relativedelta
from dateutil.parser import parse as dt_parse, ParserError

from app.utils.holidays import DEFAULT_CALENDAR, HolidayCalendar


@dataclass(frozen=True)
class DeadlineResult:
    deadline: date | None
    basis: str
    confidence: float
    statute_reference: str
    requires_human_review: bool
    assumption_flag: bool = False


# ── Word-to-number map (covers Indian legal writing style) ──────────────────

_WORD_TO_NUM: dict[str, int] = {
    "one": 1, "two": 2, "three": 3, "four": 4, "five": 5,
    "six": 6, "seven": 7, "eight": 8, "nine": 9, "ten": 10,
    "eleven": 11, "twelve": 12, "thirteen": 13, "fourteen": 14,
    "fifteen": 15, "sixteen": 16, "seventeen": 17, "eighteen": 18,
    "nineteen": 19, "twenty": 20, "thirty": 30, "forty": 40,
    "forty-five": 45, "sixty": 60, "ninety": 90,
}

_WORD_NUM_PATTERN = "|".join(re.escape(k) for k in sorted(_WORD_TO_NUM, key=len, reverse=True))
_NUM_PATTERN = rf"(\d+|{_WORD_NUM_PATTERN})"


def _parse_num(s: str) -> int:
    s = s.strip().lower()
    if s.isdigit():
        return int(s)
    return _WORD_TO_NUM[s]


# ── Compiled regexes ─────────────────────────────────────────────────────────

_RE_WITHIN_DAYS = re.compile(
    rf"\bwithin\s+{_NUM_PATTERN}\s+(?:working\s+)?days?\b",
    re.IGNORECASE,
)
_RE_WITHIN_WORKING_DAYS = re.compile(
    rf"\bwithin\s+{_NUM_PATTERN}\s+working\s+days?\b",
    re.IGNORECASE,
)
_RE_WITHIN_WEEKS = re.compile(
    rf"\bwithin\s+{_NUM_PATTERN}\s+weeks?\b",
    re.IGNORECASE,
)
_RE_WITHIN_MONTHS = re.compile(
    rf"\bwithin\s+{_NUM_PATTERN}\s+months?\b",
    re.IGNORECASE,
)
# "by 12 April 2025" / "on or before 12-04-2025" / "before 12/04/2025"
_RE_BY_DATE = re.compile(
    r"\b(?:by|before|on or before|not later than|no later than)\s+"
    r"(\d{1,2}[\-/]\d{1,2}[\-/]\d{2,4}|\d{1,2}\s+\w+\s+\d{4})",
    re.IGNORECASE,
)
# "within a period of X days/weeks/months"
_RE_PERIOD_OF = re.compile(
    rf"\bwithin\s+a\s+period\s+of\s+{_NUM_PATTERN}\s+(days?|weeks?|months?)\b",
    re.IGNORECASE,
)
# "X days from receipt of copy of order" — must be checked BEFORE within-X-days
_RE_FROM_RECEIPT = re.compile(
    rf"{_NUM_PATTERN}\s+(days?|weeks?|months?)\s+from\s+(?:the\s+)?(?:date\s+of\s+)?receipt\s+of\s+(?:a\s+)?copy",
    re.IGNORECASE,
)
# "X days from the date of this order/judgment"
_RE_FROM_DATE = re.compile(
    rf"{_NUM_PATTERN}\s+(days?|weeks?|months?)\s+from\s+(?:the\s+)?(?:date\s+of\s+)?(?:this\s+)?(?:order|judgment|decree|today)",
    re.IGNORECASE,
)


# ── Holiday-aware date arithmetic ────────────────────────────────────────────

def _roll_to_working_day(d: date, cal: HolidayCalendar) -> date:
    return cal.next_working_day(d)


def _add_calendar_days(judgment_date: date, days: int, cal: HolidayCalendar) -> date:
    d = judgment_date + timedelta(days=days)
    return _roll_to_working_day(d, cal)


def _add_working_days(judgment_date: date, working_days: int, cal: HolidayCalendar) -> date:
    d = cal.add_working_days(judgment_date, working_days)
    return _roll_to_working_day(d, cal)


def _add_months(judgment_date: date, months: int, cal: HolidayCalendar) -> date:
    d = judgment_date + relativedelta(months=months)
    return _roll_to_working_day(d, cal)


def _parse_specific_date(expr: str) -> date | None:
    """
    Try to extract a concrete date from the expression.
    Accepts DD-MM-YYYY, DD/MM/YYYY, "12 April 2025", etc.
    Returns None on failure rather than raising.
    """
    expr = expr.strip()
    if not expr:
        return None
    try:
        return dt_parse(expr, dayfirst=True, fuzzy=True).date()
    except (ParserError, ValueError, OverflowError):
        return None


def _statute_for_court(court: str) -> str:
    court_l = (court or "").lower()
    if "supreme" in court_l:
        return "Constitution of India, Article 136"
    if "high court" in court_l:
        return "Code of Civil Procedure, 1908 (Order XLVII)"
    if "ngt" in court_l or "tribunal" in court_l:
        return "National Green Tribunal Act, 2010"
    return ""


# ── Public API ───────────────────────────────────────────────────────────────

def compute_deadline(
    time_expression: str,
    judgment_date: date,
    court: str,
    cal: HolidayCalendar | None = None,
) -> DeadlineResult:
    """
    Pure rules engine — no LLM calls, ever.

    Precedence (first match wins):
      1. Empty / missing expression
      2. Immediate / forthwith (3 working days)
      3. Ongoing / till further orders
      4. No deadline specified
      5. Contingent deadline (after inquiry / report)
      6. Next hearing date (needs human input)
      7. As soon as possible / expeditiously (15 working days)
      8. "within X working days"  → working-day arithmetic
      9. "within X days"          → calendar-day arithmetic
      10. "within X weeks"
      11. "within X months"
      12. "within a period of X days/weeks/months"
      13. "X days/weeks/months from the date of order"
      14. "by/before <specific date>"
      15. Bare specific date (fuzzy parse)
      16. Unrecognised → human review
    """
    cal = cal or DEFAULT_CALENDAR
    expr = (time_expression or "").strip()
    expr_l = expr.lower()

    statute = _statute_for_court(court)
    slp_note = " (SLP — Article 136 appeal window 90 days)" if "article 136" in statute else ""

    def result(
        deadline: date | None,
        basis: str,
        confidence: float,
        requires_human_review: bool,
        assumption_flag: bool = False,
    ) -> DeadlineResult:
        return DeadlineResult(
            deadline=deadline,
            basis=basis + (slp_note if slp_note and deadline else ""),
            confidence=confidence,
            statute_reference=statute,
            requires_human_review=requires_human_review,
            assumption_flag=assumption_flag,
        )

    # ── 1. Empty ──────────────────────────────────────────────────────────────
    if not expr:
        return result(None, "No time expression found — requires human review", 0.2, True)

    # ── 2. Immediate / forthwith ──────────────────────────────────────────────
    _IMMEDIATE = {
        "forthwith", "immediately", "immediate", "at once",
        "forthwith and immediately", "forthwith comply",
    }
    if expr_l in _IMMEDIATE or any(expr_l.startswith(p) for p in _IMMEDIATE):
        d = _add_working_days(judgment_date, 3, cal)
        return result(d, f"Order date + 3 working days ({expr})", 0.9, False)

    # ── 3. Ongoing ────────────────────────────────────────────────────────────
    _ONGOING = [
        "till further orders", "until further orders",
        "until further notice", "till further notice",
        "until further directions", "till further directions",
        "pending further orders",
    ]
    if any(p in expr_l for p in _ONGOING):
        return result(None, "Ongoing — till further orders of the court", 0.9, False)

    # ── 4. No deadline ────────────────────────────────────────────────────────
    _NO_DL = [
        "no specific time", "not specified", "no time", "no deadline",
        "not mentioned", "no specific deadline", "as required",
        "as and when required", "as and when", "as necessary",
        "whenever required", "as per requirement",
    ]
    if any(p in expr_l for p in _NO_DL):
        return result(None, "No fixed deadline specified", 0.5, True)

    # ── 4b. Event-triggered (at time of X) ───────────────────────────────────────
    _AT_TIME_OF = [
        "at the time of", "at time of", "at the time",
        "at the hearing", "at the time of hearing",
        "at the time of filing", "at the time of judgment",
        "at the time of order", "upon filing", "upon pronouncement",
        "upon passing of order", "on passing", "on pronouncement",
    ]
    if any(p in expr_l for p in _AT_TIME_OF):
        return result(None, "Triggered at time of event — no fixed calendar deadline", 0.75, False)

    # ── 5. Contingent ─────────────────────────────────────────────────────────
    _CONTINGENT = [
        "after investigation", "after inquiry", "after full investigation",
        "after completion", "after report", "after filing", "upon receipt",
        "after verification",
    ]
    if any(p in expr_l for p in _CONTINGENT):
        return result(None, "Deadline contingent on completion of prior step — requires human review", 0.6, True)

    # ── 6. Next hearing ───────────────────────────────────────────────────────
    _NEXT_HEARING = [
        "next date", "next hearing", "before next date",
        "on next date", "on the next date", "before the next date",
    ]
    if any(p in expr_l for p in _NEXT_HEARING):
        return result(None, "Before next date of hearing (hearing date required)", 0.35, True)

    # ── 7. ASAP / expeditiously ───────────────────────────────────────────────
    _ASAP = [
        "as early as possible", "as soon as possible", "asap",
        "expeditiously", "without delay", "without further delay",
        "at the earliest", "at the earliest possible",
    ]
    if any(p in expr_l for p in _ASAP):
        d = _add_working_days(judgment_date, 15, cal)
        return result(d, f"Order date + 15 working days ({expr})", 0.7, False)

    # ── 8. From receipt of copy — BEFORE within-X-days (assumption_flag=True) ─────
    m = _RE_FROM_RECEIPT.search(expr)
    if m:
        n = _parse_num(m.group(1))
        unit = m.group(2).lower().rstrip("s")
        if unit == "day":
            d = _add_calendar_days(judgment_date, n, cal)
            basis = f"Order date + {n} days (approximated — actual deadline starts from date of receipt of certified copy)"
        elif unit == "week":
            d = _add_calendar_days(judgment_date, n * 7, cal)
            basis = f"Order date + {n} weeks (approximated — actual deadline starts from date of receipt of certified copy)"
        else:
            d = _add_months(judgment_date, n, cal)
            basis = f"Order date + {n} months (approximated — actual deadline starts from date of receipt of certified copy)"
        return result(d, basis, 0.80, True, assumption_flag=True)

    # ── 9.     # ── 10. Within X *working* days (must check before plain "days") ───────────
    m = _RE_WITHIN_WORKING_DAYS.search(expr)
    if m:
        n = _parse_num(m.group(1))
        d = _add_working_days(judgment_date, n, cal)
        return result(d, f"Order date + {n} working days", 0.92, False)

    # ── 9. Within X days (calendar) ───────────────────────────────────────────
    m = _RE_WITHIN_DAYS.search(expr)
    if m:
        # Skip if the match is actually "working days" (already handled above)
        matched_text = m.group(0).lower()
        if "working" not in matched_text:
            n = _parse_num(m.group(1))
            d = _add_calendar_days(judgment_date, n, cal)
            return result(d, f"Order date + {n} calendar days", 0.92, False)

    # ── 10. Within X weeks ────────────────────────────────────────────────────
    m = _RE_WITHIN_WEEKS.search(expr)
    if m:
        n = _parse_num(m.group(1))
        d = _add_calendar_days(judgment_date, n * 7, cal)
        return result(d, f"Order date + {n} weeks ({n * 7} calendar days)", 0.90, False)

    # ── 11. Within X months ───────────────────────────────────────────────────
    m = _RE_WITHIN_MONTHS.search(expr)
    if m:
        n = _parse_num(m.group(1))
        d = _add_months(judgment_date, n, cal)
        return result(d, f"Order date + {n} months", 0.88, False)

    # ── 12. Within a period of X unit ────────────────────────────────────────
    m = _RE_PERIOD_OF.search(expr)
    if m:
        n = _parse_num(m.group(1))
        unit = m.group(2).lower().rstrip("s")  # normalise to singular
        if unit == "day":
            d = _add_calendar_days(judgment_date, n, cal)
            basis = f"Order date + {n} days (period)"
        elif unit == "week":
            d = _add_calendar_days(judgment_date, n * 7, cal)
            basis = f"Order date + {n} weeks (period)"
        else:  # month
            d = _add_months(judgment_date, n, cal)
            basis = f"Order date + {n} months (period)"
        return result(d, basis, 0.90, False)

    # ── 14. X days/weeks/months from date of order ────────────────────────────
    m = _RE_FROM_DATE.search(expr)
    if m:
        n = _parse_num(m.group(1))
        unit = m.group(2).lower().rstrip("s")
        if unit == "day":
            d = _add_calendar_days(judgment_date, n, cal)
            basis = f"Order date + {n} days (from order)"
        elif unit == "week":
            d = _add_calendar_days(judgment_date, n * 7, cal)
            basis = f"Order date + {n} weeks (from order)"
        else:
            d = _add_months(judgment_date, n, cal)
            basis = f"Order date + {n} months (from order)"
        return result(d, basis, 0.90, False)

    # ── 14. By / before / on or before <specific date> ────────────────────────
    m = _RE_BY_DATE.search(expr)
    if m:
        parsed = _parse_specific_date(m.group(1))
        if parsed:
            return result(
                _roll_to_working_day(parsed, cal),
                f"Specific deadline: {parsed.strftime('%d %b %Y')} (as stated in order)",
                0.88,
                False,
            )

    # ── 15. Bare specific date (last resort fuzzy parse) ──────────────────────
    specific = _parse_specific_date(expr)
    if specific and specific >= judgment_date:
        return result(
            _roll_to_working_day(specific, cal),
            f"Specific date in order: {specific.strftime('%d %b %Y')}",
            0.80,
            False,
        )

    # ── 16. Contextual phrases that are not time expressions ──────────────────
    _CONTEXTUAL = [
        "pursuant to", "as directed", "as per", "in accordance with",
        "continuously", "when developing", "before development",
        "in compliance with", "subject to", "as applicable",
        "as ordered", "as instructed", "as mandated",
    ]
    if any(p in expr_l for p in _CONTEXTUAL):
        return result(None, "No deadline specified — ongoing directive", 0.6, False)

    # ── 17. Only flag unrecognised if it looks like it was meant to be a time expr
    _HAS_TIME_SIGNAL = re.search(
        r"\b(\d+|days?|weeks?|months?|years?|immediately|forthwith|soon|urgent|period|deadline)\b",
        expr_l,
    )
    if not _HAS_TIME_SIGNAL:
        return result(None, "No deadline specified — ongoing directive", 0.6, False)

    # ── 18. Unrecognised time expression ─────────────────────────────────────
    return result(
        None,
        f"Unrecognised time expression: {time_expression!r} — requires human review",
        0.30,
        True,
    )
