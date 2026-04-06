# Feature Leakage Audit Report

## Summary

- **Total features analyzed**: 560
- **Safe**: 548
- **Suspicious**: 12
- **Leakers**: 0

## Suspicious Features

These features triggered at least one detection strategy but did not meet the full leaker criteria. Manual review recommended.

| Feature | Importance Ratio | Correlation | Name Class | Reasons |
|---------|-----------------|-------------|------------|---------|
| diff_elo | 182.7x | 0.339 | safe | importance_ratio=182.7x; correlation=0.339 |
| elo_delta | 0.0x | 0.339 | safe | correlation=0.339 |
| diff_cumul_gd | 18.6x | 0.298 | safe | importance_ratio=18.6x |
| home_league_wins | 21.6x | 0.272 | safe | importance_ratio=21.6x |
| diff_xg_for_roll10 | 14.6x | 0.271 | safe | importance_ratio=14.6x |
| home_league_points | 12.5x | 0.268 | safe | importance_ratio=12.5x |
| away_league_wins | 11.8x | 0.261 | safe | importance_ratio=11.8x |
| away_league_points | 10.3x | 0.259 | safe | importance_ratio=10.3x |
| away_league_losses | 24.0x | 0.252 | safe | importance_ratio=24.0x |
| home_league_losses | 25.1x | 0.250 | safe | importance_ratio=25.1x |
| home_league_draws | 27.5x | 0.149 | safe | importance_ratio=27.5x |
| away_league_draws | 21.8x | 0.134 | safe | importance_ratio=21.8x |

## Recommended Additions to _RAW_MATCH_STATS

```python
# Add these to _RAW_MATCH_STATS in backtesting/data.py
    "away_league_draws",
    "away_league_losses",
    "away_league_points",
    "away_league_wins",
    "diff_cumul_gd",
    "diff_elo",
    "diff_xg_for_roll10",
    "elo_delta",
    "home_league_draws",
    "home_league_losses",
    "home_league_points",
    "home_league_wins",
```

