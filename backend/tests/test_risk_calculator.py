from datetime import date, timedelta

from app.models.directive import Directive, DirectiveStatus, RiskLevel
from app.services.risk_calculator import compute_risk


def _directive_with_deadline(d: date | None) -> Directive:
    # Minimal stub: SQLAlchemy model can be instantiated without a session for pure logic tests
    return Directive(
        case_id=None,  # type: ignore[arg-type]
        directive_text="x",
        owner_designation="y",
        status=DirectiveStatus.VERIFIED,
        deadline=d,
        requires_human_review=False,
    )


def test_risk_overdue() -> None:
    today = date(2025, 5, 10)
    d = _directive_with_deadline(today - timedelta(days=1))
    assert compute_risk(d, today) == RiskLevel.OVERDUE


def test_risk_critical() -> None:
    today = date(2025, 5, 10)
    d = _directive_with_deadline(today + timedelta(days=3))
    assert compute_risk(d, today) == RiskLevel.CRITICAL


def test_risk_due_soon() -> None:
    today = date(2025, 5, 10)
    d = _directive_with_deadline(today + timedelta(days=14))
    assert compute_risk(d, today) == RiskLevel.DUE_SOON


def test_risk_watch() -> None:
    today = date(2025, 5, 10)
    d = _directive_with_deadline(today + timedelta(days=30))
    assert compute_risk(d, today) == RiskLevel.WATCH


def test_risk_compliant() -> None:
    today = date(2025, 5, 10)
    d = _directive_with_deadline(today + timedelta(days=31))
    assert compute_risk(d, today) == RiskLevel.COMPLIANT

