"""Shared design tokens for all SportsLab reports.

Single source of truth for brand colors, model colors, and league colors.
All report renderers (HTML, Telegram, terminal) import from here.
"""

# Brand
BRAND_PRIMARY = "#1B2A4A"
BRAND_ACCENT = "#2D7DD2"
BRAND_SURFACE = "#F7F8FA"
BRAND_CARD = "#FFFFFF"
BRAND_BORDER = "#E2E5EA"

# Semantic
COLOR_POSITIVE = "#1A7F37"
COLOR_NEGATIVE = "#CF222E"
COLOR_NEUTRAL = "#9A6700"
COLOR_MUTED = "#656D76"

# Models
MODEL_COLORS: dict[str, str] = {
    "LightGBM": "#2D7DD2",
    "XGBoost": "#E36209",
    "TabPFN": "#8250DF",
    "Hybrid ENS": BRAND_PRIMARY,
    "Baseline": "#AFB8C1",
}

FALLBACK_COLORS: list[str] = ["#2D7DD2", "#E36209", "#8250DF", BRAND_PRIMARY, "#AFB8C1"]

# Leagues
LEAGUE_COLORS: dict[str, str] = {
    "ENG-Premier League": "#3D0B5B",
    "ESP-La Liga": "#CF222E",
    "GER-Bundesliga": "#1A7F37",
    "ITA-Serie A": "#2D7DD2",
    "FRA-Ligue 1": "#1B2A4A",
}

# Semaphore mapping
SEMAPHORE_MAP: dict[str, str] = {
    "green": COLOR_POSITIVE,
    "yellow": COLOR_NEUTRAL,
    "red": COLOR_NEGATIVE,
}
