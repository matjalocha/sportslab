"""Tests for football-data league ingestion."""

from pathlib import Path

import pandas as pd
from ml_in_sports.processing.league_ingestion import ingest_league
from pytest import MonkeyPatch


def test_ingest_league_mock_csv_to_parquet(
    tmp_path: Path,
    monkeypatch: MonkeyPatch,
) -> None:
    """Mock downloader output is parsed, featurized, and written to parquet."""

    def fake_download_season_csv(
        league_code: str,
        season: str,
        output_dir: Path,
    ) -> Path:
        dest = output_dir / league_code / f"{season}.csv"
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text(
            "\n".join(
                [
                    "Date,HomeTeam,AwayTeam,FTHG,FTAG,HST,AST,HC,AC,MaxH,MaxD,MaxA",
                    "01/08/24,Leeds,QPR,2,0,5,2,7,3,1.80,3.40,4.50",
                    "08/08/24,QPR,Leeds,1,1,3,4,4,6,3.10,3.20,2.20",
                    "15/08/24,Leeds,Middlesboro,0,3,2,7,5,8,2.00,3.30,3.70",
                ]
            ),
            encoding="utf-8",
        )
        return dest

    monkeypatch.setattr(
        "ml_in_sports.processing.league_ingestion.download_season_csv",
        fake_download_season_csv,
    )

    output_parquet = tmp_path / "features.parquet"

    added = ingest_league(
        league="ENG-Championship",
        seasons=["2425"],
        odds_dir=tmp_path / "odds",
        output_parquet=output_parquet,
    )

    assert added == 3
    assert output_parquet.exists()

    features = pd.read_parquet(output_parquet)
    assert set(features["league"]) == {"ENG-Championship"}
    assert set(features["season"]) == {"2425"}
    assert features.loc[0, "home_team"] == "Leeds United"
    assert "home_goals_for_roll_3" in features.columns
    assert "result_1x2" in features.columns
