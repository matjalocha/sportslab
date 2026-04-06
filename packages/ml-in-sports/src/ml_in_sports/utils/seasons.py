"""Season code computation utilities for football data pipelines.

Football seasons span two calendar years (e.g. 2023-24 -> "2324").
The season boundary is August 1 by default.
"""

from datetime import date

import structlog

logger = structlog.get_logger(__name__)

_SEASON_BOUNDARY_MONTH = 8
_SEASON_BOUNDARY_DAY = 1

_COVID_SEASON_OVERRIDES: dict[str, str] = {
    "2021": "2020-09-01",
}


def current_season_code() -> str:
    """Compute the current football season code from today's date.

    Football seasons start on August 1. Dates before August belong
    to the season that started the previous year.

    Returns:
        Four-digit season code (e.g. "2526" for the 2025-26 season).
    """
    today = date.today()
    start_year = today.year if today.month >= _SEASON_BOUNDARY_MONTH else today.year - 1
    end_year = start_year + 1
    return f"{start_year % 100:02d}{end_year % 100:02d}"


def all_season_codes(start: str = "1415") -> list[str]:
    """Generate all season codes from start to the current season.

    Args:
        start: First season code to include (e.g. "1415").

    Returns:
        List of season codes in chronological order.
    """
    current = current_season_code()
    current_start_yy = int(current[:2])

    start_yy = int(start[:2])

    codes: list[str] = []
    year = start_yy
    while True:
        next_year = (year + 1) % 100
        code = f"{year:02d}{next_year:02d}"
        codes.append(code)
        if year == current_start_yy:
            break
        year = next_year

    return codes


def season_start_date(season: str) -> str:
    """Return the start date for a given season code.

    Default start date is August 1 of the first year in the season.
    The COVID-affected 2020-21 season ("2021") started September 1.

    Args:
        season: Four-digit season code (e.g. "2324").

    Returns:
        Date string in YYYY-MM-DD format.
    """
    if season in _COVID_SEASON_OVERRIDES:
        return _COVID_SEASON_OVERRIDES[season]

    start_yy = int(season[:2])
    full_year = 2000 + start_yy if start_yy < 100 else start_yy
    return f"{full_year:04d}-08-01"
