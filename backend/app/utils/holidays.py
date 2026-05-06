from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta


@dataclass(frozen=True)
class HolidayCalendar:
    gazetted: set[date]

    def is_gazetted_holiday(self, d: date) -> bool:
        return d in self.gazetted

    def is_working_day(self, d: date) -> bool:
        if d.weekday() == 6:  # Sunday
            return False
        return not self.is_gazetted_holiday(d)

    def next_working_day(self, d: date) -> date:
        cur = d
        while not self.is_working_day(cur):
            cur = cur + timedelta(days=1)
        return cur

    def add_working_days(self, start: date, working_days: int) -> date:
        if working_days < 0:
            raise ValueError("working_days must be >= 0")
        cur = start
        added = 0
        while added < working_days:
            cur = cur + timedelta(days=1)
            if self.is_working_day(cur):
                added += 1
        return cur


# Karnataka + national gazetted holidays (starter set).
# Production: keep this list updated each year from Karnataka Gazette.
GAZETTED_HOLIDAYS: set[date] = {
    # 2025
    date(2025, 1, 1),   # New Year
    date(2025, 1, 26),  # Republic Day
    date(2025, 4, 14),  # Dr. Ambedkar Jayanti
    date(2025, 5, 1),   # May Day
    date(2025, 8, 15),  # Independence Day
    date(2025, 10, 2),  # Gandhi Jayanti
    date(2025, 11, 1),  # Karnataka Rajyotsava
    date(2025, 12, 25), # Christmas
    # 2026 (basic national; extend with Karnataka gazette list)
    date(2026, 1, 1),
    date(2026, 1, 26),
    date(2026, 4, 14),
    date(2026, 5, 1),
    date(2026, 8, 15),
    date(2026, 10, 2),
    date(2026, 11, 1),
    date(2026, 12, 25),
}


DEFAULT_CALENDAR = HolidayCalendar(gazetted=GAZETTED_HOLIDAYS)

