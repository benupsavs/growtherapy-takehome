import datetime
import pytest
from date.resolvers import days_in_week


def test_days_in_week_first_day_of_year() -> None:
    year = 2022
    week = 1
    result = list(days_in_week(year, week))
    assert len(result) == 7

    expected_dates = [datetime.date(year, week, d) for d in range(1, 8)]
    for d in result:
        assert d in expected_dates


def test_days_in_week_invalid_input() -> None:
    year = 2022
    week = -1
    with pytest.raises(ValueError):
        days_in_week(year, week)
    week = 54
    with pytest.raises(ValueError):
        days_in_week(year, week)


def test_days_in_week_last_week_of_year() -> None:
    year = 2022
    week = 53
    result = list(days_in_week(year, week))
    assert len(result) < 7


def test_days_in_week_1_to_52_full_weeks() -> None:
    year = 2022
    for week in range(1, 53):
        result = list(days_in_week(year, week))
        assert len(result) == 7
