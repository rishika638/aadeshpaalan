from __future__ import annotations

from datetime import date, timedelta

from app.models.directive import Directive, DirectiveStatus, RiskLevel

_ARCHIVE_THRESHOLD_DAYS = 365
_RECENT_OVERDUE_DAYS = 90


def compute_risk(directive: Directive, today: date) -> RiskLevel:
    # Archived: deadline set, >1 year ago, never verified
    if (
        directive.deadline is not None
        and directive.deadline < (today - timedelta(days=_ARCHIVE_THRESHOLD_DAYS))
        and directive.status == DirectiveStatus.PENDING_REVIEW
    ):
        return RiskLevel.ARCHIVED_UNVERIFIED

    if directive.deadline is None:
        return RiskLevel.WATCH

    days_remaining = (directive.deadline - today).days

    if days_remaining < 0:
        # Only flag OVERDUE if deadline was within last 90 days
        if days_remaining >= -_RECENT_OVERDUE_DAYS:
            return RiskLevel.OVERDUE
        # Older than 90 days past deadline but not yet 365 — still watch
        return RiskLevel.WATCH
    if days_remaining <= 3:
        return RiskLevel.CRITICAL
    if days_remaining <= 14:
        return RiskLevel.DUE_SOON
    if days_remaining <= 30:
        return RiskLevel.WATCH
    return RiskLevel.COMPLIANT
