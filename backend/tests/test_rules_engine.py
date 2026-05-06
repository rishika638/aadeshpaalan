from datetime import date

from app.services.rules_engine import compute_deadline
from app.utils.holidays import HolidayCalendar


def test_forthwith_adds_3_working_days_and_rolls_holidays() -> None:
    # 2025-05-01 is in our gazetted list; also Thursday.
    # "forthwith" => +3 working days from judgment date
    cal = HolidayCalendar(gazetted={date(2025, 5, 2)})  # make May 2 a holiday for test determinism
    res = compute_deadline("forthwith", date(2025, 5, 1), court="High Court of Karnataka", cal=cal)
    assert res.deadline == date(2025, 5, 6)  # Fri(2 holiday) skip, Sat(3) working, Mon(5) working, Tue(6) working
    assert res.requires_human_review is False


def test_within_days_rolls_sunday() -> None:
    # 2025-05-02 + 2 days = 2025-05-04 (Sunday) => roll to Monday 2025-05-05
    cal = HolidayCalendar(gazetted=set())
    res = compute_deadline("within 2 days", date(2025, 5, 2), court="High Court of Karnataka", cal=cal)
    assert res.deadline == date(2025, 5, 5)


def test_before_next_hearing_requires_human_review() -> None:
    cal = HolidayCalendar(gazetted=set())
    res = compute_deadline("before next date of hearing", date(2025, 5, 1), court="High Court of Karnataka", cal=cal)
    assert res.deadline is None
    assert res.requires_human_review is True

