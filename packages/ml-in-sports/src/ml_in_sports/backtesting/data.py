"""Data loading and preparation for backtesting.

Reads materialized features parquet, selects feature columns,
computes targets, and prepares train/test splits per fold.

Pinnacle closing odds integration (SPO-60):
When Pinnacle CSVs are available in the configured odds directory,
the loader prefers Pinnacle closing odds over market-average odds
for CLV computation. Falls back to avg_home/avg_draw/avg_away when
Pinnacle data is unavailable or team names cannot be matched.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
import structlog

from ml_in_sports.utils.team_names import normalize_team_name

logger = structlog.get_logger(__name__)

# Columns that are metadata, not features
_META_COLS: frozenset[str] = frozenset({
    "id",
    "league",
    "season",
    "game",
    "date",
    "home_team",
    "away_team",
    "home_goals",
    "away_goals",
    "result_1x2",
    "source_updated_at",
})

# Odds columns (used for CLV computation, not as features)
_ODDS_COLS: frozenset[str] = frozenset({
    "b365_home",
    "b365_draw",
    "b365_away",
    "avg_home",
    "avg_draw",
    "avg_away",
    "b365_over_25",
    "b365_under_25",
    "avg_over_25",
    "avg_under_25",
    # Pinnacle closing odds (merged from football-data.co.uk CSVs)
    "pinnacle_home",
    "pinnacle_draw",
    "pinnacle_away",
})

# Non-numeric target/market columns stored as strings
_MARKET_COLS: frozenset[str] = frozenset({
    "over_2_5",
    "btts",
    "over_1_5",
    "over_3_5",
    "home_goals_over_1_5",
    "away_goals_over_0_5",
    "home_or_draw",
    "home_or_away",
    "draw_or_away",
})

# Formation columns (categorical, not numeric features)
_FORMATION_COLS: frozenset[str] = frozenset({
    "home_formation",
    "away_formation",
    "home_formation_group",
    "away_formation_group",
})

# Raw post-match statistics -- these describe what happened DURING the match
# and are NOT available at prediction time. Including them causes label leakage.
_RAW_MATCH_STATS: frozenset[str] = frozenset({
    "home_xg",
    "away_xg",
    "home_np_xg",
    "away_np_xg",
    "home_expected_points",
    "away_expected_points",
    "home_ppda",
    "away_ppda",
    "home_deep_completions",
    "away_deep_completions",
    "home_possession",
    "away_possession",
    "home_total_shots",
    "away_total_shots",
    "home_shots",
    "away_shots",
    "home_shots_on_target",
    "away_shots_on_target",
    "home_effective_tackles",
    "away_effective_tackles",
    "home_total_tackles",
    "away_total_tackles",
    "home_accurate_passes",
    "away_accurate_passes",
    "home_blocked_shots",
    "away_blocked_shots",
    "home_fouls",
    "away_fouls",
    "home_interceptions",
    "away_interceptions",
    "home_effective_clearance",
    "away_effective_clearance",
    "home_accurate_crosses",
    "away_accurate_crosses",
    "home_accurate_long_balls",
    "away_accurate_long_balls",
    "home_penalty_kick_goals",
    "away_penalty_kick_goals",
    "home_penalty_kick_shots",
    "away_penalty_kick_shots",
    "home_attendance",
    "away_attendance",
    "home_total_passes",
    "away_total_passes",
    "home_saves",
    "away_saves",
    "home_yellow_cards",
    "away_yellow_cards",
    "home_red_cards",
    "away_red_cards",
    "home_offsides",
    "away_offsides",
    "home_total_crosses",
    "away_total_crosses",
    "home_total_clearance",
    "away_total_clearance",
    # Derived post-match columns
    "margin",
    "total_goals",
    # Detected by automated leakage check (SPO-56): raw match stats
    # that were missing from the original exclusion list.
    "home_total_long_balls",
    "away_total_long_balls",
    "home_corners",
    "away_corners",
    "home_won_corners",
    "away_won_corners",
})

# Odds-derived columns — NOT post-match leakage, but circular when used
# as model features alongside the same odds used for CLV computation.
# Detected by automated leakage check (SPO-56).
_ODDS_DERIVED_COLS: frozenset[str] = frozenset({
    "implied_prob_home",
    "implied_prob_draw",
    "implied_prob_away",
    "implied_prob_over_25",
    "implied_prob_under_25",
    "fair_prob_home",
    "fair_prob_draw",
    "fair_prob_away",
    "fair_prob_over_25",
    "fair_prob_under_25",
    "consensus_home",
    "consensus_draw",
    "consensus_away",
    "overround_1x2",
    "overround_ou",
})

# All non-feature columns combined
_EXCLUDED_COLS: frozenset[str] = (
    _META_COLS
    | _ODDS_COLS
    | _MARKET_COLS
    | _FORMATION_COLS
    | _RAW_MATCH_STATS
    | _ODDS_DERIVED_COLS
)

# Target encoding: result_1x2 string -> integer
_TARGET_ENCODING: dict[str, int] = {"H": 0, "D": 1, "A": 2}

# Maximum fraction of NaN in a column before it is dropped
_MAX_NAN_FRACTION: float = 0.50


class BacktestDataLoader:
    """Loads and prepares data for walk-forward backtesting.

    Reads a materialized features parquet file, filters by league and
    season, encodes the target, selects numeric feature columns, drops
    high-NaN columns, and fills remaining NaNs with column medians.

    When ``pinnacle_odds_dir`` points to a directory with Pinnacle CSVs
    from football-data.co.uk, the loader merges Pinnacle closing odds
    and prefers them over market-average odds for CLV computation.

    The loader is stateless after ``__init__`` -- calling ``load()``
    multiple times with different filters produces independent results.

    Args:
        parquet_path: Path to the all_features.parquet file.
        target_col: Name of the raw target column in the parquet.
        pinnacle_odds_dir: Directory containing football-data.co.uk CSVs
            with Pinnacle closing odds. ``None`` disables Pinnacle merge
            and uses market-average odds only.
    """

    def __init__(
        self,
        parquet_path: Path = Path("data/features/all_features.parquet"),
        target_col: str = "result_1x2",
        pinnacle_odds_dir: Path | None = None,
    ) -> None:
        self._parquet_path = parquet_path
        self._target_col = target_col
        self._pinnacle_odds_dir = pinnacle_odds_dir
        self._feature_columns: list[str] | None = None
        self._pinnacle_odds: pd.DataFrame | None = None

    def load(
        self,
        leagues: list[str] | None = None,
        seasons: list[str] | None = None,
    ) -> pd.DataFrame:
        """Load, filter, and prepare data from the parquet file.

        Applies the following transformations in order:
          1. Filter by leagues and/or seasons (if specified).
          2. Drop rows where the target column is NaN (future matches).
          3. Encode the target column (H=0, D=1, A=2) as ``target``.
          4. Select numeric feature columns (excluding meta/odds/market).
          5. Drop columns with >50% NaN.
          6. Fill remaining NaN with column median.
          7. Sort by date within each season.

        Args:
            leagues: League names to include. None means all leagues.
            seasons: Season codes to include. None means all seasons.

        Returns:
            DataFrame with meta columns, ``target`` (int), and clean
            numeric feature columns.

        Raises:
            FileNotFoundError: If the parquet file does not exist.
        """
        if not self._parquet_path.exists():
            raise FileNotFoundError(
                f"Features parquet not found: {self._parquet_path}"
            )

        df = pd.read_parquet(self._parquet_path)
        logger.info(
            "parquet_loaded",
            path=str(self._parquet_path),
            rows=len(df),
            columns=df.shape[1],
        )

        # Filter by leagues
        if leagues is not None:
            df = df[df["league"].isin(leagues)].copy()
            logger.info("filtered_by_leagues", leagues=leagues, rows=len(df))

        # Filter by seasons
        if seasons is not None:
            df = df[df["season"].isin(seasons)].copy()
            logger.info("filtered_by_seasons", seasons=seasons, rows=len(df))

        # Drop rows where target is NaN (upcoming/future matches)
        before_drop = len(df)
        df = df.dropna(subset=[self._target_col]).copy()
        dropped = before_drop - len(df)
        if dropped > 0:
            logger.info("dropped_nan_target_rows", count=dropped)

        # Encode target: H=0, D=1, A=2
        df["target"] = df[self._target_col].map(_TARGET_ENCODING)
        unmapped = df["target"].isna().sum()
        if unmapped > 0:
            logger.warning(
                "unmapped_target_values",
                count=int(unmapped),
                unique_values=list(df[self._target_col].unique()),
            )
            df = df.dropna(subset=["target"]).copy()
        df["target"] = df["target"].astype(int)

        # Select feature columns: all numeric columns minus exclusions
        numeric_cols = set(df.select_dtypes(include="number").columns)
        feature_cols = sorted(numeric_cols - _EXCLUDED_COLS - {"target"})

        # Drop columns with >50% NaN
        nan_fractions = df[feature_cols].isna().mean()
        high_nan_cols = nan_fractions[nan_fractions > _MAX_NAN_FRACTION].index.tolist()
        if high_nan_cols:
            logger.info(
                "dropped_high_nan_columns",
                count=len(high_nan_cols),
                threshold=_MAX_NAN_FRACTION,
            )
            feature_cols = [c for c in feature_cols if c not in high_nan_cols]

        # Fill remaining NaN with column median
        medians = df[feature_cols].median()
        df[feature_cols] = df[feature_cols].fillna(medians)

        # Store feature columns for later retrieval
        self._feature_columns = feature_cols

        # Sort by date within each season for proper temporal ordering
        df = df.sort_values(["season", "date"]).reset_index(drop=True)

        logger.info(
            "data_prepared",
            rows=len(df),
            feature_columns=len(feature_cols),
            leagues=sorted(df["league"].unique().tolist()),
            seasons=sorted(df["season"].unique().tolist()),
        )

        return df

    def get_feature_columns(self) -> list[str]:
        """Return the list of feature column names.

        Must be called after ``load()`` -- the feature list is computed
        during loading based on NaN analysis and column type filtering.

        Returns:
            Sorted list of feature column names.

        Raises:
            RuntimeError: If called before ``load()``.
        """
        if self._feature_columns is None:
            raise RuntimeError(
                "Feature columns not available. Call load() first."
            )
        return list(self._feature_columns)

    def _load_pinnacle_odds(
        self,
        leagues: list[str] | None,
        seasons: list[str] | None,
    ) -> pd.DataFrame | None:
        """Load Pinnacle closing odds from football-data.co.uk CSVs.

        Returns ``None`` if the configured directory does not exist, has
        no CSV files, or ``pinnacle_odds_dir`` was not set.

        Team names from football-data.co.uk are normalized through the
        same ``normalize_team_name`` mapping used in the main pipeline,
        so that names like "Nott'm Forest" match the canonical
        "Nottingham Forest" in the features parquet.

        Args:
            leagues: SportsLab league names to filter (or ``None``).
            seasons: Season codes to filter (or ``None``).

        Returns:
            DataFrame with Pinnacle odds keyed by (league, season,
            home_team, away_team), or ``None`` if unavailable.
        """
        if self._pinnacle_odds_dir is None:
            return None

        if not self._pinnacle_odds_dir.is_dir():
            logger.info(
                "pinnacle_odds_dir_not_found",
                path=str(self._pinnacle_odds_dir),
            )
            return None

        from ml_in_sports.processing.odds.pinnacle import load_pinnacle_odds

        odds_df = load_pinnacle_odds(
            data_dir=self._pinnacle_odds_dir,
            leagues=leagues,
            seasons=seasons,
        )

        if odds_df.empty:
            logger.info("no_pinnacle_odds_loaded")
            return None

        # Normalize team names so they match the features parquet.
        odds_df["home_team"] = odds_df["home_team"].map(normalize_team_name)
        odds_df["away_team"] = odds_df["away_team"].map(normalize_team_name)

        # Keep only the columns needed for the merge.
        keep_cols = [
            "league",
            "season",
            "home_team",
            "away_team",
            "pinnacle_home",
            "pinnacle_draw",
            "pinnacle_away",
        ]
        odds_df = odds_df[[c for c in keep_cols if c in odds_df.columns]]

        # Drop rows where all three Pinnacle odds are NaN (no value).
        pinnacle_cols = ["pinnacle_home", "pinnacle_draw", "pinnacle_away"]
        present_cols = [c for c in pinnacle_cols if c in odds_df.columns]
        if present_cols:
            odds_df = odds_df.dropna(subset=present_cols, how="all")

        if odds_df.empty:
            logger.info("pinnacle_odds_all_nan_after_filter")
            return None

        logger.info(
            "pinnacle_odds_ready_for_merge",
            rows=len(odds_df),
            leagues=sorted(odds_df["league"].unique().tolist()),
        )
        return odds_df

    @staticmethod
    def _merge_pinnacle_into_test(
        test_df: pd.DataFrame,
        pinnacle_df: pd.DataFrame,
    ) -> np.ndarray | None:
        """Merge Pinnacle closing odds onto test data by team names.

        Performs a left join on (league, season, home_team, away_team).
        Rows that match get Pinnacle odds; unmatched rows fall back to
        the market-average odds already in test_df.

        Args:
            test_df: Test fold DataFrame with meta and odds columns.
            pinnacle_df: Pinnacle odds DataFrame from
                ``_load_pinnacle_odds``.

        Returns:
            Array of shape (n_test, 3) with closing odds per match,
            preferring Pinnacle where available, or ``None`` if
            neither source provides usable odds.
        """
        join_cols = ["league", "season", "home_team", "away_team"]
        missing_join = [c for c in join_cols if c not in test_df.columns]
        if missing_join:
            logger.warning(
                "pinnacle_merge_missing_join_cols",
                missing=missing_join,
            )
            return None

        # Reset index to ensure positional alignment after merge.
        test_reset = test_df.reset_index(drop=True)
        merged = test_reset[join_cols].merge(
            pinnacle_df,
            on=join_cols,
            how="left",
        )

        pinnacle_cols = ["pinnacle_home", "pinnacle_draw", "pinnacle_away"]
        has_pinnacle = all(c in merged.columns for c in pinnacle_cols)

        if not has_pinnacle:
            return None

        pinnacle_matched = merged[pinnacle_cols].notna().all(axis=1).sum()
        total = len(merged)
        match_pct = pinnacle_matched / total * 100 if total > 0 else 0.0

        logger.info(
            "pinnacle_merge_result",
            matched=int(pinnacle_matched),
            total=total,
            match_pct=round(match_pct, 1),
        )

        # Build the output: Pinnacle where available, avg_* as fallback.
        avg_cols = ["avg_home", "avg_draw", "avg_away"]
        has_avg = all(c in test_reset.columns for c in avg_cols)

        result = merged[pinnacle_cols].copy().reset_index(drop=True)
        result.columns = pd.Index(["closing_home", "closing_draw", "closing_away"])

        if has_avg:
            avg_values = test_reset[avg_cols].copy().reset_index(drop=True)
            avg_values.columns = pd.Index(
                ["closing_home", "closing_draw", "closing_away"]
            )
            # Fill NaN Pinnacle rows with market average.
            for col in result.columns:
                result[col] = result[col].fillna(avg_values[col])

        if result.notna().all(axis=None):
            return result.values

        # Some rows still NaN even after fallback -- fill with median.
        non_nan_count = result.notna().all(axis=1).sum()
        if non_nan_count > 0:
            filled = result.fillna(result.median())
            logger.warning(
                "closing_odds_had_nan_after_merge",
                nan_rows=int(total - non_nan_count),
                total_rows=total,
            )
            return filled.values

        return None

    def get_fold_data(
        self,
        df: pd.DataFrame,
        train_seasons: list[str],
        test_seasons: list[str],
    ) -> tuple[pd.DataFrame, np.ndarray, pd.DataFrame, np.ndarray, np.ndarray | None]:
        """Split data into train and test sets by season.

        Closing odds priority (SPO-60):
          1. Pinnacle closing (PSH/PSD/PSA from football-data.co.uk)
          2. Market average (avg_home/avg_draw/avg_away from parquet)

        When Pinnacle data is available, matched rows use Pinnacle odds
        and unmatched rows fall back to market average. This gives CLV
        computed against the sharpest closing line available.

        Args:
            df: Prepared DataFrame from ``load()``.
            train_seasons: Season codes for training data.
            test_seasons: Season codes for test data.

        Returns:
            Tuple of:
                - X_train: Feature DataFrame for training.
                - y_train: Target array for training, shape (n_train,).
                - X_test: Feature DataFrame for testing.
                - y_test: Target array for testing, shape (n_test,).
                - test_closing_odds: Closing odds array, shape (n_test, 3)
                  using Pinnacle closing where available, falling back to
                  avg_home/avg_draw/avg_away. ``None`` if no odds source
                  is available.

        Raises:
            RuntimeError: If called before ``load()``.
            ValueError: If train or test split is empty.
        """
        feature_cols = self.get_feature_columns()

        train_mask = df["season"].isin(train_seasons)
        test_mask = df["season"].isin(test_seasons)

        train_df = df[train_mask]
        test_df = df[test_mask]

        if len(train_df) == 0:
            raise ValueError(
                f"No training data for seasons {train_seasons}"
            )
        if len(test_df) == 0:
            raise ValueError(
                f"No test data for seasons {test_seasons}"
            )

        x_train = train_df[feature_cols].copy()
        y_train = np.asarray(train_df["target"].values)

        x_test = test_df[feature_cols].copy()
        y_test = np.asarray(test_df["target"].values)

        # --- Closing odds: prefer Pinnacle, fall back to avg_* ---
        test_closing_odds: np.ndarray | None = None
        odds_source = "none"

        # Try Pinnacle first (lazy-load once per loader instance).
        if self._pinnacle_odds is None and self._pinnacle_odds_dir is not None:
            leagues_in_data = df["league"].unique().tolist()
            seasons_in_data = df["season"].unique().tolist()
            self._pinnacle_odds = self._load_pinnacle_odds(
                leagues=leagues_in_data,
                seasons=seasons_in_data,
            )

        if self._pinnacle_odds is not None:
            pinnacle_result = self._merge_pinnacle_into_test(
                test_df, self._pinnacle_odds
            )
            if pinnacle_result is not None:
                test_closing_odds = pinnacle_result
                odds_source = "pinnacle"

        # Fall back to market-average odds from the parquet.
        if test_closing_odds is None:
            avg_cols = ["avg_home", "avg_draw", "avg_away"]
            if all(c in test_df.columns for c in avg_cols):
                odds_df = test_df[avg_cols]
                if odds_df.notna().all(axis=None):
                    test_closing_odds = odds_df.values
                    odds_source = "market_average"
                else:
                    non_nan_count = odds_df.notna().all(axis=1).sum()
                    if non_nan_count > 0:
                        odds_filled = odds_df.fillna(odds_df.median())
                        test_closing_odds = odds_filled.values
                        odds_source = "market_average"
                        logger.warning(
                            "test_odds_had_nan",
                            nan_rows=int(len(odds_df) - non_nan_count),
                            total_rows=len(odds_df),
                        )

        logger.info(
            "fold_data_split",
            train_seasons=train_seasons,
            test_seasons=test_seasons,
            train_rows=len(x_train),
            test_rows=len(x_test),
            has_odds=test_closing_odds is not None,
            odds_source=odds_source,
        )

        return x_train, y_train, x_test, y_test, test_closing_odds
