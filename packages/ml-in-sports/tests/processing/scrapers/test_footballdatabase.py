"""Tests for the footballdatabase.eu scraper PoC parser."""

from ml_in_sports.processing.scrapers.footballdatabase import (
    parse_competition_fixtures,
)


def test_parse_competition_fixtures_from_static_html() -> None:
    """Fixture rows from the competition page shape are parsed."""
    html = """
    <div id='results' class='module gamelist spy'>
      <h3><span class='dday'>32. Kolejka</span></h3>
      <table class='list'>
        <tr class='date line all'><td colspan='7'>10 kwiecień 2026</td></tr>
        <tr class='line all'>
          <td class='hour'>
            <script type="text/javascript">
              var datedematch=moment.tz("2026-04-10 20:00:00","Europe/London");
            </script>
          </td>
          <td class='club left'><a href='/pl/klub/druzyna/132-west_ham/2025-2026'>West Ham</a></td>
          <td class='clublogo left'></td>
          <td class='score'><a href='/pl/match/podsumowanie/3221719-west_ham-wolverhampton'><span class='preview'>NA ZYWO</span></a></td>
          <td class='clublogo right'></td>
          <td class='club right'><a href='/pl/klub/druzyna/158-wolverhampton/2025-2026'>Wolverhampton</a></td>
          <td class='stats'></td>
        </tr>
        <tr class='line all'>
          <td class='hour'></td>
          <td class='club left'><a href='/pl/klub/druzyna/38-chelsea/2025-2026'>Chelsea</a></td>
          <td class='clublogo left'></td>
          <td class='score'><a href='/pl/match/podsumowanie/3221715-chelsea-manchester_city'>2-1</a></td>
          <td class='clublogo right'></td>
          <td class='club right'><a href='/pl/klub/druzyna/110-manchester_city/2025-2026'>Manchester City</a></td>
          <td class='stats'></td>
        </tr>
      </table>
    </div>
    """

    fixtures = parse_competition_fixtures(
        html,
        "https://www.footballdatabase.eu/pl/rozgrywki/ogolne/22323-premier_league/2025-2026",
    )

    assert len(fixtures) == 2
    assert fixtures[0].match_id == "3221719"
    assert fixtures[0].home_team == "West Ham"
    assert fixtures[0].away_team == "Wolverhampton"
    assert fixtures[0].status == "upcoming"
    assert fixtures[0].kickoff is not None
    assert fixtures[0].timezone == "Europe/London"
    assert fixtures[1].status == "played"
    assert fixtures[1].home_goals == 2
    assert fixtures[1].away_goals == 1


def test_parse_competition_fixtures_missing_results_returns_empty() -> None:
    """Parser fails closed when the expected section is absent."""
    assert parse_competition_fixtures("<html></html>", "https://example.test") == []
