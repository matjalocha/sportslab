"""Automated data leakage detection for feature sets.

Provides four complementary strategies to identify post-match data
that has leaked into pre-match feature columns:

1. Feature importance spike detection (LightGBM-based)
2. High correlation with target detection
3. Name-based heuristic classification
4. Combined report with final verdicts

Usage::

    from ml_in_sports.backtesting.leakage import run_leakage_check, generate_leakage_report

    results = run_leakage_check(X, y)
    generate_leakage_report(results, Path("docs/feature_leakage_audit.md"))
"""

from __future__ import annotations

import re
from pathlib import Path

import lightgbm as lgb
import numpy as np
import pandas as pd
import structlog

logger = structlog.get_logger(__name__)

# ---------------------------------------------------------------------------
# Name-based heuristic patterns
# ---------------------------------------------------------------------------

# Features matching these patterns are considered safe (pre-match computable).
# Order matters: first match wins.
_SAFE_PATTERNS: list[tuple[str, str]] = [
    (r"_rolling_", "rolling_window"),
    (r"_roll\d+", "rolling_window"),
    (r"_lag\d+", "lagged_value"),
    (r"_last\d+", "recent_form"),
    (r"_streak", "streak_counter"),
    (r"_form_\d+", "form_window"),
    (r"_elo", "elo_rating"),
    (r"_h2h_", "head_to_head"),
    (r"h2h_", "head_to_head"),
    (r"_fifa_", "fifa_attribute"),
    (r"_avg_.*_xi", "squad_attribute"),
    (r"_max_.*_xi", "squad_attribute"),
    (r"_min_.*_xi", "squad_attribute"),
    (r"_total_value_eur_xi", "squad_value"),
    (r"_total_wage_eur_xi", "squad_wage"),
    (r"_overall_std_xi", "squad_attribute"),
    (r"_bench_avg_overall", "squad_attribute"),
    (r"_starting_gk_overall", "squad_attribute"),
    (r"_num_defenders", "squad_composition"),
    (r"_num_forwards", "squad_composition"),
    (r"_num_midfielders", "squad_composition"),
    (r"_league_points", "league_table"),
    (r"_league_wins", "league_table"),
    (r"_league_losses", "league_table"),
    (r"_league_draws", "league_table"),
    (r"_league_goals_for", "league_table"),
    (r"_league_goals_against", "league_table"),
    (r"_league_goal_difference", "league_table"),
    (r"_table_pos", "league_table"),
    (r"table_pos_diff", "league_table"),
    (r"_cumul_gd", "cumulative_stat"),
    (r"_cumul_pts", "cumulative_stat"),
    (r"_cumul_mp", "cumulative_stat"),
    (r"_pts_gap", "points_gap"),
    (r"_stability_\d+", "formation_stability"),
    (r"_win_rate_", "win_rate"),
    (r"_venue_", "venue_stat"),
    (r"_days_since_last", "schedule"),
    (r"_matches_last_\d+d", "schedule"),
    (r"_pctile_", "percentile_stat"),
    (r"_sp_", "set_piece_stat"),
    (r"_momentum_", "momentum_stat"),
    (r"_team_xi_", "player_form"),
    (r"_top_scorer_", "player_form"),
    (r"_top_creator_", "player_form"),
    (r"^diff_", "differential"),
    (r"^elo_", "elo_derived"),
    (r"^implied_prob_", "odds_derived"),
    (r"^fair_prob_", "odds_derived"),
    (r"^overround_", "odds_derived"),
    (r"^consensus_", "consensus_prob"),
    (r"^midfield_dominance$", "squad_derived"),
    (r"^defender_mismatch$", "squad_derived"),
    (r"^is_weekend$", "calendar"),
    (r"^is_holiday_period$", "calendar"),
    (r"^day_of_week$", "calendar"),
    (r"^month$", "calendar"),
    (r"^week$", "calendar"),
    (r"^season_phase$", "calendar"),
    (r"^round$", "calendar"),
    (r"^round_number$", "calendar"),
    (r"^n_teams$", "league_meta"),
    (r"_scored_last\d+", "recent_form"),
    (r"_cs_last\d+", "recent_form"),
    (r"_drew_last\d+", "recent_form"),
    (r"_lost_last\d+", "recent_form"),
    (r"_won_last\d+", "recent_form"),
    (r"_unbeaten_streak", "streak_counter"),
    (r"_losing_streak", "streak_counter"),
    (r"_scoring_streak", "streak_counter"),
    (r"_clean_sheet_streak", "streak_counter"),
    (r"_draw_streak", "streak_counter"),
    (r"_win_streak", "streak_counter"),
    (r"_corners_won_rolling_", "rolling_window"),
    (r"_opponent_corners_rolling_", "rolling_window"),
    (r"_fouls_rolling_", "rolling_window"),
    (r"_red_cards_rolling_", "rolling_window"),
    (r"_yellow_cards_rolling_", "rolling_window"),
    (r"_goals_first_15min_rolling_", "rolling_window"),
    (r"_goals_last_15min_rolling_", "rolling_window"),
    (r"_goals_conceded_lag\d+", "lagged_value"),
    (r"_goals_scored_lag\d+", "lagged_value"),
    (r"_goals_scored_vs_\dback_std", "formation_matchup"),
    (r"_points_lag\d+", "lagged_value"),
    (r"_xg_for_lag\d+", "lagged_value"),
    (r"_xg_against_lag\d+", "lagged_value"),
    (r"_xg_buildup_rolling_", "rolling_window"),
    (r"_xg_chain_rolling_", "rolling_window"),
    (r"xg_x_conversion_", "derived_interaction"),
    (r"elo_x_form_", "derived_interaction"),
    (r"elo_x_xg_", "derived_interaction"),
    (r"diff_elo_x_form", "derived_interaction"),
    (r"elo_delta", "elo_derived"),
    (r"_form_goals_conceded_\d+", "form_window"),
    (r"_form_goals_scored_\d+", "form_window"),
    (r"_fifa_match_rate_xi", "squad_attribute"),
]

# Features matching these patterns are suspicious (possibly post-match).
_SUSPICIOUS_PATTERNS: list[tuple[str, str]] = [
    (r"^(?:home|away)_xg$", "raw_match_xg"),
    (r"^(?:home|away)_np_xg$", "raw_match_np_xg"),
    (r"^(?:home|away)_goals$", "raw_match_goals"),
    (r"^(?:home|away)_possession$", "raw_match_possession"),
    (r"^(?:home|away)_ppda$", "raw_match_ppda"),
    (r"^(?:home|away)_expected_points$", "raw_match_expected_pts"),
    (r"^(?:home|away)_total_shots$", "raw_match_shots"),
    (r"^(?:home|away)_shots_on_target$", "raw_match_sot"),
    (r"^(?:home|away)_total_passes$", "raw_match_passes"),
    (r"^(?:home|away)_accurate_passes$", "raw_match_passes"),
    (r"^(?:home|away)_saves$", "raw_match_saves"),
    (r"^(?:home|away)_fouls$", "raw_match_fouls"),
    (r"^(?:home|away)_offsides$", "raw_match_offsides"),
    (r"^(?:home|away)_interceptions$", "raw_match_interceptions"),
    (r"^(?:home|away)_blocked_shots$", "raw_match_blocked_shots"),
    (r"^(?:home|away)_deep_completions$", "raw_match_deep_comp"),
    (r"^(?:home|away)_effective_tackles$", "raw_match_tackles"),
    (r"^(?:home|away)_total_tackles$", "raw_match_tackles"),
    (r"^(?:home|away)_effective_clearance$", "raw_match_clearance"),
    (r"^(?:home|away)_total_clearance$", "raw_match_clearance"),
    (r"^(?:home|away)_accurate_crosses$", "raw_match_crosses"),
    (r"^(?:home|away)_total_crosses$", "raw_match_crosses"),
    (r"^(?:home|away)_accurate_long_balls$", "raw_match_long_balls"),
    (r"^(?:home|away)_total_long_balls$", "raw_match_long_balls"),
    (r"^(?:home|away)_penalty_kick_goals$", "raw_match_penalty"),
    (r"^(?:home|away)_penalty_kick_shots$", "raw_match_penalty"),
    (r"^(?:home|away)_yellow_cards$", "raw_match_cards"),
    (r"^(?:home|away)_red_cards$", "raw_match_cards"),
    (r"^(?:home|away)_attendance$", "raw_match_attendance"),
    (r"^(?:home|away)_won_corners$", "raw_match_corners"),
    (r"^margin$", "post_match_derived"),
    (r"^total_goals$", "post_match_derived"),
]


def detect_importance_spikes(
    x: pd.DataFrame,
    y: np.ndarray,
    threshold_multiplier: float = 10.0,
) -> pd.DataFrame:
    """Train quick LightGBM and flag features with importance > threshold * mean.

    Uses a shallow, fast LightGBM classifier (50 estimators, max_depth=4)
    to measure split-based feature importance. Features whose importance
    exceeds ``threshold_multiplier`` times the mean importance are flagged
    as suspicious -- they carry disproportionate predictive signal, which
    for a multiclass match result target typically indicates post-match
    data leaking into the feature.

    Args:
        x: Feature DataFrame, shape (n_samples, n_features). Must contain
            only numeric columns with no NaN.
        y: Integer-encoded target array, shape (n_samples,). Values in {0,1,2}.
        threshold_multiplier: A feature is suspicious when its importance
            exceeds this multiple of the mean importance. Default 10.0.

    Returns:
        DataFrame with columns: feature, importance, mean_importance, ratio,
        is_suspicious. Sorted by importance descending.
    """
    if x.shape[1] == 0:
        return pd.DataFrame(
            columns=["feature", "importance", "mean_importance", "ratio", "is_suspicious"],
        )

    model = lgb.LGBMClassifier(
        n_estimators=50,
        max_depth=4,
        random_state=42,
        verbosity=-1,
        n_jobs=1,
        importance_type="gain",
    )
    model.fit(x, y)

    importances = model.feature_importances_.astype(float)
    feature_names = list(x.columns)

    mean_imp = float(np.mean(importances)) if len(importances) > 0 else 0.0
    # Avoid division by zero when mean is zero
    safe_mean = mean_imp if mean_imp > 0 else 1.0

    ratios = importances / safe_mean

    result = pd.DataFrame({
        "feature": feature_names,
        "importance": importances,
        "mean_importance": mean_imp,
        "ratio": ratios,
        "is_suspicious": ratios > threshold_multiplier,
    })

    result = result.sort_values("importance", ascending=False).reset_index(drop=True)

    suspicious_count = int(result["is_suspicious"].sum())
    logger.info(
        "importance_spike_detection_complete",
        total_features=len(feature_names),
        suspicious_count=suspicious_count,
        threshold_multiplier=threshold_multiplier,
        mean_importance=round(mean_imp, 4),
    )

    return result


def detect_high_correlations(
    x: pd.DataFrame,
    y: np.ndarray,
    threshold: float = 0.3,
) -> pd.DataFrame:
    """Compute absolute correlation of each feature with the target.

    For a multiclass target encoded as integers (0, 1, 2), this function
    creates binary indicator columns for each class and computes the
    Pearson correlation of every feature with each indicator. The maximum
    absolute correlation across all class indicators is reported.

    Pre-match features typically correlate 0.01--0.15 with match results.
    Correlation above 0.3 is suspicious; above 0.5 is almost certainly
    post-match leakage.

    Args:
        x: Feature DataFrame, shape (n_samples, n_features).
        y: Integer-encoded target array, shape (n_samples,).
        threshold: Absolute correlation above which a feature is suspicious.

    Returns:
        DataFrame with columns: feature, correlation, is_suspicious,
        severity (low/medium/high). Sorted by correlation descending.
    """
    if x.shape[1] == 0:
        return pd.DataFrame(
            columns=["feature", "correlation", "is_suspicious", "severity"],
        )

    unique_classes = np.unique(y)
    max_correlations: list[float] = []

    for col in x.columns:
        col_values = np.asarray(x[col].values, dtype=float)
        class_corrs: list[float] = []
        for cls in unique_classes:
            indicator = (y == cls).astype(float)
            # Handle constant columns (std=0)
            if np.std(col_values) == 0.0 or np.std(indicator) == 0.0:
                class_corrs.append(0.0)
            else:
                corr = float(np.abs(np.corrcoef(col_values, indicator)[0, 1]))
                class_corrs.append(corr if np.isfinite(corr) else 0.0)
        max_correlations.append(max(class_corrs))

    correlations = np.array(max_correlations)

    def _severity(corr: float) -> str:
        if corr >= 0.5:
            return "high"
        if corr >= threshold:
            return "medium"
        return "low"

    result = pd.DataFrame({
        "feature": list(x.columns),
        "correlation": correlations,
        "is_suspicious": correlations > threshold,
        "severity": [_severity(c) for c in correlations],
    })

    result = result.sort_values("correlation", ascending=False).reset_index(drop=True)

    suspicious_count = int(result["is_suspicious"].sum())
    high_count = int((result["severity"] == "high").sum())
    logger.info(
        "correlation_detection_complete",
        total_features=x.shape[1],
        suspicious_count=suspicious_count,
        high_severity_count=high_count,
        threshold=threshold,
    )

    return result


def detect_name_patterns(
    feature_names: list[str],
) -> pd.DataFrame:
    """Classify features by name patterns as safe, suspicious, or unknown.

    Uses a whitelist of safe patterns (rolling windows, lags, Elo, form,
    squad attributes, etc.) and a blacklist of suspicious patterns (raw
    match stats without temporal qualifiers). Features matching neither
    list are classified as ``unknown``.

    Args:
        feature_names: List of feature column names to classify.

    Returns:
        DataFrame with columns: feature, classification (safe/suspicious/unknown),
        matched_pattern. Sorted by classification then feature name.
    """
    classifications: list[str] = []
    matched_patterns: list[str] = []

    for name in feature_names:
        found = False

        # Check suspicious patterns first (they are more specific --
        # e.g. "home_xg" is suspicious, "home_xg_for_roll3" is safe)
        for pattern, label in _SUSPICIOUS_PATTERNS:
            if re.search(pattern, name):
                classifications.append("suspicious")
                matched_patterns.append(label)
                found = True
                break

        if found:
            continue

        for pattern, label in _SAFE_PATTERNS:
            if re.search(pattern, name):
                classifications.append("safe")
                matched_patterns.append(label)
                found = True
                break

        if not found:
            classifications.append("unknown")
            matched_patterns.append("")

    result = pd.DataFrame({
        "feature": feature_names,
        "classification": classifications,
        "matched_pattern": matched_patterns,
    })

    result = result.sort_values(
        ["classification", "feature"],
    ).reset_index(drop=True)

    safe_count = int((result["classification"] == "safe").sum())
    suspicious_count = int((result["classification"] == "suspicious").sum())
    unknown_count = int((result["classification"] == "unknown").sum())
    logger.info(
        "name_pattern_detection_complete",
        total_features=len(feature_names),
        safe=safe_count,
        suspicious=suspicious_count,
        unknown=unknown_count,
    )

    return result


def run_leakage_check(
    x: pd.DataFrame,
    y: np.ndarray,
    importance_threshold: float = 10.0,
    correlation_threshold: float = 0.3,
) -> pd.DataFrame:
    """Run all leakage detection strategies and combine into a single report.

    Combines results from importance spike detection, correlation analysis,
    and name-based heuristics into a unified verdict per feature.

    Verdict logic:
      - **leaker**: importance ratio > threshold AND correlation > 0.5
      - **suspicious**: importance ratio > threshold OR correlation > threshold
        OR name classification is ``suspicious``
      - **safe**: none of the above

    Args:
        x: Feature DataFrame, shape (n_samples, n_features).
        y: Integer-encoded target array, shape (n_samples,).
        importance_threshold: Multiplier for importance spike detection.
        correlation_threshold: Absolute correlation threshold.

    Returns:
        DataFrame with columns: feature, importance_ratio, correlation,
        name_class, final_verdict (safe/suspicious/leaker), reasons.
        Sorted by final_verdict severity then correlation descending.
    """
    feature_names = list(x.columns)

    if len(feature_names) == 0:
        return pd.DataFrame(
            columns=[
                "feature",
                "importance_ratio",
                "correlation",
                "name_class",
                "final_verdict",
                "reasons",
            ],
        )

    logger.info(
        "leakage_check_started",
        n_features=len(feature_names),
        n_samples=len(y),
    )

    # Strategy 1: Importance spikes
    importance_df = detect_importance_spikes(x, y, importance_threshold)
    importance_map = dict(
        zip(importance_df["feature"], importance_df["ratio"], strict=True),
    )
    importance_suspicious = set(
        importance_df.loc[importance_df["is_suspicious"], "feature"],
    )

    # Strategy 2: Correlation
    correlation_df = detect_high_correlations(x, y, correlation_threshold)
    correlation_map = dict(
        zip(correlation_df["feature"], correlation_df["correlation"], strict=True),
    )
    correlation_suspicious = set(
        correlation_df.loc[correlation_df["is_suspicious"], "feature"],
    )
    high_correlation = set(
        correlation_df.loc[correlation_df["severity"] == "high", "feature"],
    )

    # Strategy 3: Name patterns
    name_df = detect_name_patterns(feature_names)
    name_class_map = dict(
        zip(name_df["feature"], name_df["classification"], strict=True),
    )
    name_suspicious = set(
        name_df.loc[name_df["classification"] == "suspicious", "feature"],
    )

    # Combine verdicts
    verdicts: list[str] = []
    reasons_list: list[str] = []

    for feat in feature_names:
        feat_reasons: list[str] = []

        is_importance_spike = feat in importance_suspicious
        is_corr_suspicious = feat in correlation_suspicious
        is_high_corr = feat in high_correlation
        is_name_suspicious = feat in name_suspicious

        if is_importance_spike:
            feat_reasons.append(
                f"importance_ratio={importance_map[feat]:.1f}x",
            )
        if is_corr_suspicious:
            feat_reasons.append(
                f"correlation={correlation_map[feat]:.3f}",
            )
        if is_name_suspicious:
            feat_reasons.append("name_pattern=suspicious")

        # Verdict logic
        if is_importance_spike and is_high_corr:
            verdict = "leaker"
        elif is_importance_spike or is_corr_suspicious or is_name_suspicious:
            verdict = "suspicious"
        else:
            verdict = "safe"

        verdicts.append(verdict)
        reasons_list.append("; ".join(feat_reasons) if feat_reasons else "")

    result = pd.DataFrame({
        "feature": feature_names,
        "importance_ratio": [importance_map.get(f, 0.0) for f in feature_names],
        "correlation": [correlation_map.get(f, 0.0) for f in feature_names],
        "name_class": [name_class_map.get(f, "unknown") for f in feature_names],
        "final_verdict": verdicts,
        "reasons": reasons_list,
    })

    # Sort: leakers first, then suspicious, then safe; within each group by
    # correlation descending.
    verdict_order = {"leaker": 0, "suspicious": 1, "safe": 2}
    result["_sort_key"] = result["final_verdict"].map(verdict_order)
    result = result.sort_values(
        ["_sort_key", "correlation"],
        ascending=[True, False],
    ).reset_index(drop=True)
    result = result.drop(columns=["_sort_key"])

    leaker_count = int((result["final_verdict"] == "leaker").sum())
    suspicious_count = int((result["final_verdict"] == "suspicious").sum())
    safe_count = int((result["final_verdict"] == "safe").sum())

    logger.info(
        "leakage_check_complete",
        leakers=leaker_count,
        suspicious=suspicious_count,
        safe=safe_count,
    )

    return result


def generate_leakage_report(
    results: pd.DataFrame,
    output_path: Path,
) -> Path:
    """Generate a markdown report from leakage check results.

    The report includes:
      - Summary counts: safe / suspicious / leakers
      - Table of confirmed leakers sorted by correlation descending
      - Table of suspicious features
      - Recommended additions to ``_RAW_MATCH_STATS``

    Args:
        results: DataFrame from ``run_leakage_check``.
        output_path: Path where the markdown file will be written.

    Returns:
        The resolved output path.
    """
    output_path = output_path.resolve()
    output_path.parent.mkdir(parents=True, exist_ok=True)

    leakers = results[results["final_verdict"] == "leaker"]
    suspicious = results[results["final_verdict"] == "suspicious"]
    safe = results[results["final_verdict"] == "safe"]

    lines: list[str] = [
        "# Feature Leakage Audit Report",
        "",
        "## Summary",
        "",
        f"- **Total features analyzed**: {len(results)}",
        f"- **Safe**: {len(safe)}",
        f"- **Suspicious**: {len(suspicious)}",
        f"- **Leakers**: {len(leakers)}",
        "",
    ]

    if len(leakers) > 0:
        lines.extend([
            "## Confirmed Leakers",
            "",
            "These features have both high importance (>10x mean) and high "
            "correlation (>0.5) with the target. They almost certainly contain "
            "post-match information.",
            "",
            "| Feature | Importance Ratio | Correlation | Name Class | Reasons |",
            "|---------|-----------------|-------------|------------|---------|",
        ])
        for _, row in leakers.iterrows():
            lines.append(
                f"| {row['feature']} | {row['importance_ratio']:.1f}x "
                f"| {row['correlation']:.3f} | {row['name_class']} "
                f"| {row['reasons']} |",
            )
        lines.append("")

    if len(suspicious) > 0:
        lines.extend([
            "## Suspicious Features",
            "",
            "These features triggered at least one detection strategy but "
            "did not meet the full leaker criteria. Manual review recommended.",
            "",
            "| Feature | Importance Ratio | Correlation | Name Class | Reasons |",
            "|---------|-----------------|-------------|------------|---------|",
        ])
        for _, row in suspicious.iterrows():
            lines.append(
                f"| {row['feature']} | {row['importance_ratio']:.1f}x "
                f"| {row['correlation']:.3f} | {row['name_class']} "
                f"| {row['reasons']} |",
            )
        lines.append("")

    # Recommended exclusions
    exclude_features = sorted(
        set(leakers["feature"].tolist()) | set(suspicious["feature"].tolist()),
    )
    if exclude_features:
        lines.extend([
            "## Recommended Additions to _RAW_MATCH_STATS",
            "",
            "```python",
            "# Add these to _RAW_MATCH_STATS in backtesting/data.py",
        ])
        for feat in exclude_features:
            lines.append(f'    "{feat}",')
        lines.extend([
            "```",
            "",
        ])

    content = "\n".join(lines) + "\n"
    output_path.write_text(content, encoding="utf-8")

    logger.info(
        "leakage_report_generated",
        output_path=str(output_path),
        leakers=len(leakers),
        suspicious=len(suspicious),
    )

    return output_path
