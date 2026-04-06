"""Tests for season code computation utilities."""

from unittest.mock import MagicMock, patch

from ml_in_sports.utils.seasons import (
    all_season_codes,
    current_season_code,
    season_start_date,
)


class TestCurrentSeasonCode:
    """Tests for current_season_code."""

    def test_returns_four_digit_string(self) -> None:
        """Result is always a 4-digit string."""
        result = current_season_code()
        assert len(result) == 4
        assert result.isdigit()

    @patch("ml_in_sports.utils.seasons.date")
    def test_march_2026_returns_2526(self, mock_date: MagicMock) -> None:
        """March 2026 falls in the 2025-26 season."""
        from datetime import date as real_date

        mock_date.today.return_value = real_date(2026, 3, 5)
        assert current_season_code() == "2526"

    @patch("ml_in_sports.utils.seasons.date")
    def test_october_2026_returns_2627(self, mock_date: MagicMock) -> None:
        """October 2026 falls in the 2026-27 season."""
        from datetime import date as real_date

        mock_date.today.return_value = real_date(2026, 10, 15)
        assert current_season_code() == "2627"

    @patch("ml_in_sports.utils.seasons.date")
    def test_july_2025_returns_2425(self, mock_date: MagicMock) -> None:
        """July 2025 (before Aug boundary) falls in 2024-25 season."""
        from datetime import date as real_date

        mock_date.today.return_value = real_date(2025, 7, 31)
        assert current_season_code() == "2425"

    @patch("ml_in_sports.utils.seasons.date")
    def test_august_2025_returns_2526(self, mock_date: MagicMock) -> None:
        """August 2025 (at boundary) falls in 2025-26 season."""
        from datetime import date as real_date

        mock_date.today.return_value = real_date(2025, 8, 1)
        assert current_season_code() == "2526"


class TestAllSeasonCodes:
    """Tests for all_season_codes."""

    def test_starts_from_1415_by_default(self) -> None:
        """Default start is '1415'."""
        result = all_season_codes()
        assert result[0] == "1415"

    def test_includes_current_season(self) -> None:
        """List ends with the current season."""
        result = all_season_codes()
        current = current_season_code()
        assert result[-1] == current

    def test_custom_start_returns_subset(self) -> None:
        """Custom start code produces a shorter list."""
        full = all_season_codes()
        subset = all_season_codes("2324")
        assert len(subset) < len(full)
        assert subset[0] == "2324"
        assert subset[-1] == current_season_code()

    def test_consecutive_codes_are_sequential(self) -> None:
        """Each code's end matches the next code's start."""
        result = all_season_codes()
        for i in range(len(result) - 1):
            end_of_current = result[i][2:]
            start_of_next = result[i + 1][:2]
            assert end_of_current == start_of_next

    def test_single_season_when_start_is_current(self) -> None:
        """Returns single element when start equals current season."""
        current = current_season_code()
        result = all_season_codes(current)
        assert result == [current]


class TestSeasonStartDate:
    """Tests for season_start_date."""

    def test_regular_season_2324(self) -> None:
        """Season 2324 starts on 2023-08-01."""
        assert season_start_date("2324") == "2023-08-01"

    def test_covid_season_2021(self) -> None:
        """COVID season 2021 starts on 2020-09-01."""
        assert season_start_date("2021") == "2020-09-01"

    def test_season_1415(self) -> None:
        """Season 1415 starts on 2014-08-01."""
        assert season_start_date("1415") == "2014-08-01"

    def test_season_2526(self) -> None:
        """Season 2526 starts on 2025-08-01."""
        assert season_start_date("2526") == "2025-08-01"

    def test_future_season(self) -> None:
        """Unknown future season still computes correctly."""
        assert season_start_date("2930") == "2029-08-01"

    def test_returns_yyyy_mm_dd_format(self) -> None:
        """Result is always in YYYY-MM-DD format."""
        result = season_start_date("1920")
        parts = result.split("-")
        assert len(parts) == 3
        assert len(parts[0]) == 4
        assert len(parts[1]) == 2
        assert len(parts[2]) == 2
