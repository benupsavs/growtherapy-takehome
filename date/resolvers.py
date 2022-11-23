from typing import Iterable, List

import calendar
import datetime

# Resolvers contains utilities to resolve months, weeks, and days to Python dates.


def days_in_week(year: int, week: int) -> Iterable[datetime.date]:
    """
    Gets all days in the specified week.
    :param year: the year, for example, 2022
    :param week: the week in the year, ranging from 1 to 53
    :return: an iterable containing all of the days in the week, from
    lowest to highest
    :raises ValueError: if the week is out of range
    """
    if week < 1 or week > 53:
        raise ValueError("Week must be from 1 to 53, inclusive")
    first_day_of_year = datetime.date(year, 1, 1)
    first_day_of_week = first_day_of_year + datetime.timedelta(weeks=week - 1)
    day_delta = datetime.timedelta(days=1)
    result: List[datetime.date] = []
    for week_day_idx in range(0, 7):
        # only add the dates that occur in the requested year
        week_day = first_day_of_week + day_delta * week_day_idx
        if week_day.year == year:
            result.append(week_day)
        else:
            break

    return result


def days_in_month(year: int, month: int) -> Iterable[datetime.date]:
    """
    Gets all day in the specified month.
    :param year: the year, for example: 2022
    :param month: the month in the year, ranging from 1 to 12
    :return: an iterable containing all of the days in the month, from lowest
    to highest
    """
    if month < 1 or month > 12:
        raise ValueError("Month must be from 1 to 12, inclusive")
    month_start_stop = calendar.monthrange(year, month)
    return [datetime.date(year, month, d) for d in range(month_start_stop[0], month_start_stop[1])]
