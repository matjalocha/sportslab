"""SQLAlchemy declarative models matching the 11-table football database schema.

These models mirror the raw SQL in ``ml_in_sports.utils.database._TABLES_SQL``
exactly. They exist so Alembic can autogenerate migrations and so future code
can use the SQLAlchemy ORM instead of hand-written SQL.

The ``database.py`` module still uses raw ``sqlite3`` for reads/writes --
switching it to the ORM is a separate task.
"""

from sqlalchemy import Float, Integer, Text, UniqueConstraint
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    """Shared declarative base for all football database models."""


class Match(Base):
    """Match-level aggregated statistics scraped from Understat/FBref."""

    __tablename__ = "matches"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    league: Mapped[str] = mapped_column(Text, nullable=False)
    season: Mapped[str] = mapped_column(Text, nullable=False)
    game: Mapped[str] = mapped_column(Text, nullable=False)
    date: Mapped[str] = mapped_column(Text, nullable=False)
    home_team: Mapped[str] = mapped_column(Text, nullable=False)
    away_team: Mapped[str] = mapped_column(Text, nullable=False)
    home_goals: Mapped[int | None] = mapped_column(Integer, nullable=True)
    away_goals: Mapped[int | None] = mapped_column(Integer, nullable=True)
    home_xg: Mapped[float | None] = mapped_column(Float, nullable=True)
    away_xg: Mapped[float | None] = mapped_column(Float, nullable=True)
    home_np_xg: Mapped[float | None] = mapped_column(Float, nullable=True)
    away_np_xg: Mapped[float | None] = mapped_column(Float, nullable=True)
    home_expected_points: Mapped[float | None] = mapped_column(Float, nullable=True)
    away_expected_points: Mapped[float | None] = mapped_column(Float, nullable=True)
    home_ppda: Mapped[float | None] = mapped_column(Float, nullable=True)
    away_ppda: Mapped[float | None] = mapped_column(Float, nullable=True)
    home_deep_completions: Mapped[int | None] = mapped_column(Integer, nullable=True)
    away_deep_completions: Mapped[int | None] = mapped_column(Integer, nullable=True)
    home_possession: Mapped[float | None] = mapped_column(Float, nullable=True)
    away_possession: Mapped[float | None] = mapped_column(Float, nullable=True)
    home_total_shots: Mapped[int | None] = mapped_column(Integer, nullable=True)
    away_total_shots: Mapped[int | None] = mapped_column(Integer, nullable=True)
    home_shots_on_target: Mapped[int | None] = mapped_column(Integer, nullable=True)
    away_shots_on_target: Mapped[int | None] = mapped_column(Integer, nullable=True)
    home_effective_tackles: Mapped[int | None] = mapped_column(Integer, nullable=True)
    away_effective_tackles: Mapped[int | None] = mapped_column(Integer, nullable=True)
    home_total_tackles: Mapped[int | None] = mapped_column(Integer, nullable=True)
    away_total_tackles: Mapped[int | None] = mapped_column(Integer, nullable=True)
    home_accurate_passes: Mapped[int | None] = mapped_column(Integer, nullable=True)
    away_accurate_passes: Mapped[int | None] = mapped_column(Integer, nullable=True)
    home_total_passes: Mapped[int | None] = mapped_column(Integer, nullable=True)
    away_total_passes: Mapped[int | None] = mapped_column(Integer, nullable=True)
    home_accurate_crosses: Mapped[int | None] = mapped_column(Integer, nullable=True)
    away_accurate_crosses: Mapped[int | None] = mapped_column(Integer, nullable=True)
    home_effective_clearance: Mapped[int | None] = mapped_column(Integer, nullable=True)
    away_effective_clearance: Mapped[int | None] = mapped_column(Integer, nullable=True)
    home_interceptions: Mapped[int | None] = mapped_column(Integer, nullable=True)
    away_interceptions: Mapped[int | None] = mapped_column(Integer, nullable=True)
    home_saves: Mapped[int | None] = mapped_column(Integer, nullable=True)
    away_saves: Mapped[int | None] = mapped_column(Integer, nullable=True)
    home_fouls: Mapped[int | None] = mapped_column(Integer, nullable=True)
    away_fouls: Mapped[int | None] = mapped_column(Integer, nullable=True)
    home_yellow_cards: Mapped[int | None] = mapped_column(Integer, nullable=True)
    away_yellow_cards: Mapped[int | None] = mapped_column(Integer, nullable=True)
    home_red_cards: Mapped[int | None] = mapped_column(Integer, nullable=True)
    away_red_cards: Mapped[int | None] = mapped_column(Integer, nullable=True)
    home_won_corners: Mapped[int | None] = mapped_column(Integer, nullable=True)
    away_won_corners: Mapped[int | None] = mapped_column(Integer, nullable=True)
    home_offsides: Mapped[int | None] = mapped_column(Integer, nullable=True)
    away_offsides: Mapped[int | None] = mapped_column(Integer, nullable=True)
    home_blocked_shots: Mapped[int | None] = mapped_column(Integer, nullable=True)
    away_blocked_shots: Mapped[int | None] = mapped_column(Integer, nullable=True)
    home_total_crosses: Mapped[int | None] = mapped_column(Integer, nullable=True)
    away_total_crosses: Mapped[int | None] = mapped_column(Integer, nullable=True)
    home_total_long_balls: Mapped[int | None] = mapped_column(Integer, nullable=True)
    away_total_long_balls: Mapped[int | None] = mapped_column(Integer, nullable=True)
    home_accurate_long_balls: Mapped[int | None] = mapped_column(Integer, nullable=True)
    away_accurate_long_balls: Mapped[int | None] = mapped_column(Integer, nullable=True)
    home_total_clearance: Mapped[int | None] = mapped_column(Integer, nullable=True)
    away_total_clearance: Mapped[int | None] = mapped_column(Integer, nullable=True)
    home_penalty_kick_goals: Mapped[int | None] = mapped_column(Integer, nullable=True)
    away_penalty_kick_goals: Mapped[int | None] = mapped_column(Integer, nullable=True)
    home_penalty_kick_shots: Mapped[int | None] = mapped_column(Integer, nullable=True)
    away_penalty_kick_shots: Mapped[int | None] = mapped_column(Integer, nullable=True)
    home_attendance: Mapped[int | None] = mapped_column(Integer, nullable=True)
    away_attendance: Mapped[int | None] = mapped_column(Integer, nullable=True)
    round: Mapped[int | None] = mapped_column(Integer, nullable=True)
    week: Mapped[int | None] = mapped_column(Integer, nullable=True)
    home_elo: Mapped[float | None] = mapped_column(Float, nullable=True)
    away_elo: Mapped[float | None] = mapped_column(Float, nullable=True)
    source_updated_at: Mapped[str | None] = mapped_column(Text, nullable=True)

    __table_args__ = (UniqueConstraint("league", "season", "game"),)


class PlayerMatch(Base):
    """Per-player per-match statistics from Understat."""

    __tablename__ = "player_matches"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    league: Mapped[str] = mapped_column(Text, nullable=False)
    season: Mapped[str] = mapped_column(Text, nullable=False)
    game: Mapped[str] = mapped_column(Text, nullable=False)
    team: Mapped[str] = mapped_column(Text, nullable=False)
    player: Mapped[str] = mapped_column(Text, nullable=False)
    position: Mapped[str | None] = mapped_column(Text, nullable=True)
    minutes: Mapped[int | None] = mapped_column(Integer, nullable=True)
    goals: Mapped[int | None] = mapped_column(Integer, nullable=True)
    shots: Mapped[int | None] = mapped_column(Integer, nullable=True)
    xg: Mapped[float | None] = mapped_column(Float, nullable=True)
    xa: Mapped[float | None] = mapped_column(Float, nullable=True)
    key_passes: Mapped[int | None] = mapped_column(Integer, nullable=True)
    xg_chain: Mapped[float | None] = mapped_column(Float, nullable=True)
    xg_buildup: Mapped[float | None] = mapped_column(Float, nullable=True)
    own_goals: Mapped[int | None] = mapped_column(Integer, nullable=True)
    assists: Mapped[int | None] = mapped_column(Integer, nullable=True)
    fouls_committed: Mapped[int | None] = mapped_column(Integer, nullable=True)
    fouls_suffered: Mapped[int | None] = mapped_column(Integer, nullable=True)
    saves: Mapped[int | None] = mapped_column(Integer, nullable=True)
    offsides: Mapped[int | None] = mapped_column(Integer, nullable=True)
    total_shots_espn: Mapped[int | None] = mapped_column(Integer, nullable=True)
    shots_on_target_espn: Mapped[int | None] = mapped_column(Integer, nullable=True)
    sub_in: Mapped[int | None] = mapped_column(Integer, nullable=True)
    sub_out: Mapped[int | None] = mapped_column(Integer, nullable=True)
    yellow_cards: Mapped[int | None] = mapped_column(Integer, nullable=True)
    red_cards: Mapped[int | None] = mapped_column(Integer, nullable=True)
    source_updated_at: Mapped[str | None] = mapped_column(Text, nullable=True)

    __table_args__ = (
        UniqueConstraint("league", "season", "game", "team", "player"),
    )


class LeagueTable(Base):
    """Season standings snapshot per team."""

    __tablename__ = "league_tables"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    league: Mapped[str] = mapped_column(Text, nullable=False)
    season: Mapped[str] = mapped_column(Text, nullable=False)
    team: Mapped[str] = mapped_column(Text, nullable=False)
    matches_played: Mapped[int | None] = mapped_column(Integer, nullable=True)
    wins: Mapped[int | None] = mapped_column(Integer, nullable=True)
    draws: Mapped[int | None] = mapped_column(Integer, nullable=True)
    losses: Mapped[int | None] = mapped_column(Integer, nullable=True)
    goals_for: Mapped[int | None] = mapped_column(Integer, nullable=True)
    goals_against: Mapped[int | None] = mapped_column(Integer, nullable=True)
    goal_difference: Mapped[int | None] = mapped_column(Integer, nullable=True)
    points: Mapped[int | None] = mapped_column(Integer, nullable=True)

    __table_args__ = (UniqueConstraint("league", "season", "team"),)


class EloRating(Base):
    """Daily Elo rating snapshots from ClubElo."""

    __tablename__ = "elo_ratings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    team: Mapped[str] = mapped_column(Text, nullable=False)
    date: Mapped[str] = mapped_column(Text, nullable=False)
    elo: Mapped[float | None] = mapped_column(Float, nullable=True)
    rank: Mapped[int | None] = mapped_column(Integer, nullable=True)
    country: Mapped[str | None] = mapped_column(Text, nullable=True)
    league: Mapped[str | None] = mapped_column(Text, nullable=True)

    __table_args__ = (UniqueConstraint("team", "date"),)


class FifaRating(Base):
    """FIFA/FC player ratings per version."""

    __tablename__ = "fifa_ratings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    player_name: Mapped[str] = mapped_column(Text, nullable=False)
    long_name: Mapped[str | None] = mapped_column(Text, nullable=True)
    age: Mapped[int | None] = mapped_column(Integer, nullable=True)
    nationality: Mapped[str | None] = mapped_column(Text, nullable=True)
    club_name: Mapped[str | None] = mapped_column(Text, nullable=True)
    league_name: Mapped[str | None] = mapped_column(Text, nullable=True)
    overall: Mapped[int | None] = mapped_column(Integer, nullable=True)
    potential: Mapped[int | None] = mapped_column(Integer, nullable=True)
    value_eur: Mapped[int | None] = mapped_column(Integer, nullable=True)
    wage_eur: Mapped[int | None] = mapped_column(Integer, nullable=True)
    preferred_foot: Mapped[str | None] = mapped_column(Text, nullable=True)
    height_cm: Mapped[int | None] = mapped_column(Integer, nullable=True)
    weight_kg: Mapped[int | None] = mapped_column(Integer, nullable=True)
    positions: Mapped[str | None] = mapped_column(Text, nullable=True)
    pace: Mapped[int | None] = mapped_column(Integer, nullable=True)
    shooting: Mapped[int | None] = mapped_column(Integer, nullable=True)
    passing: Mapped[int | None] = mapped_column(Integer, nullable=True)
    dribbling: Mapped[int | None] = mapped_column(Integer, nullable=True)
    defending: Mapped[int | None] = mapped_column(Integer, nullable=True)
    physic: Mapped[int | None] = mapped_column(Integer, nullable=True)
    skill_moves: Mapped[int | None] = mapped_column(Integer, nullable=True)
    weak_foot: Mapped[int | None] = mapped_column(Integer, nullable=True)
    fifa_version: Mapped[str | None] = mapped_column(Text, nullable=True)
    source_updated_at: Mapped[str | None] = mapped_column(Text, nullable=True)

    __table_args__ = (
        UniqueConstraint("player_name", "club_name", "fifa_version"),
    )


class TmPlayer(Base):
    """Transfermarkt player profile data."""

    __tablename__ = "tm_players"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    player_id: Mapped[int] = mapped_column(Integer, nullable=False)
    name: Mapped[str | None] = mapped_column(Text, nullable=True)
    first_name: Mapped[str | None] = mapped_column(Text, nullable=True)
    last_name: Mapped[str | None] = mapped_column(Text, nullable=True)
    position: Mapped[str | None] = mapped_column(Text, nullable=True)
    sub_position: Mapped[str | None] = mapped_column(Text, nullable=True)
    foot: Mapped[str | None] = mapped_column(Text, nullable=True)
    height_in_cm: Mapped[float | None] = mapped_column(Float, nullable=True)
    date_of_birth: Mapped[str | None] = mapped_column(Text, nullable=True)
    country_of_citizenship: Mapped[str | None] = mapped_column(Text, nullable=True)
    current_club_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    current_club_name: Mapped[str | None] = mapped_column(Text, nullable=True)
    market_value_in_eur: Mapped[int | None] = mapped_column(Integer, nullable=True)
    highest_market_value_in_eur: Mapped[int | None] = mapped_column(Integer, nullable=True)
    contract_expiration_date: Mapped[str | None] = mapped_column(Text, nullable=True)
    source_updated_at: Mapped[str | None] = mapped_column(Text, nullable=True)

    __table_args__ = (UniqueConstraint("player_id"),)


class TmPlayerValuation(Base):
    """Transfermarkt historical player market valuations."""

    __tablename__ = "tm_player_valuations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    player_id: Mapped[int] = mapped_column(Integer, nullable=False)
    date: Mapped[str] = mapped_column(Text, nullable=False)
    market_value_in_eur: Mapped[int | None] = mapped_column(Integer, nullable=True)
    current_club_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    current_club_name: Mapped[str | None] = mapped_column(Text, nullable=True)
    source_updated_at: Mapped[str | None] = mapped_column(Text, nullable=True)

    __table_args__ = (UniqueConstraint("player_id", "date"),)


class TmGame(Base):
    """Transfermarkt match metadata (formations, attendance, referee)."""

    __tablename__ = "tm_games"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    game_id: Mapped[int] = mapped_column(Integer, nullable=False)
    competition_id: Mapped[str | None] = mapped_column(Text, nullable=True)
    season: Mapped[str | None] = mapped_column(Text, nullable=True)
    round: Mapped[str | None] = mapped_column(Text, nullable=True)
    date: Mapped[str | None] = mapped_column(Text, nullable=True)
    home_club_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    away_club_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    home_club_name: Mapped[str | None] = mapped_column(Text, nullable=True)
    away_club_name: Mapped[str | None] = mapped_column(Text, nullable=True)
    home_club_goals: Mapped[int | None] = mapped_column(Integer, nullable=True)
    away_club_goals: Mapped[int | None] = mapped_column(Integer, nullable=True)
    home_club_manager_name: Mapped[str | None] = mapped_column(Text, nullable=True)
    away_club_manager_name: Mapped[str | None] = mapped_column(Text, nullable=True)
    stadium: Mapped[str | None] = mapped_column(Text, nullable=True)
    attendance: Mapped[int | None] = mapped_column(Integer, nullable=True)
    referee: Mapped[str | None] = mapped_column(Text, nullable=True)
    home_club_formation: Mapped[str | None] = mapped_column(Text, nullable=True)
    away_club_formation: Mapped[str | None] = mapped_column(Text, nullable=True)
    source_updated_at: Mapped[str | None] = mapped_column(Text, nullable=True)

    __table_args__ = (UniqueConstraint("game_id"),)


class MatchOdds(Base):
    """Closing and opening odds from Football-Data.co.uk."""

    __tablename__ = "match_odds"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    league: Mapped[str] = mapped_column(Text, nullable=False)
    season: Mapped[str] = mapped_column(Text, nullable=False)
    game: Mapped[str] = mapped_column(Text, nullable=False)
    date: Mapped[str | None] = mapped_column(Text, nullable=True)
    home_team: Mapped[str | None] = mapped_column(Text, nullable=True)
    away_team: Mapped[str | None] = mapped_column(Text, nullable=True)
    ft_home_goals: Mapped[int | None] = mapped_column(Integer, nullable=True)
    ft_away_goals: Mapped[int | None] = mapped_column(Integer, nullable=True)
    ft_result: Mapped[str | None] = mapped_column(Text, nullable=True)
    ht_home_goals: Mapped[int | None] = mapped_column(Integer, nullable=True)
    ht_away_goals: Mapped[int | None] = mapped_column(Integer, nullable=True)
    ht_result: Mapped[str | None] = mapped_column(Text, nullable=True)
    referee: Mapped[str | None] = mapped_column(Text, nullable=True)
    home_shots: Mapped[int | None] = mapped_column(Integer, nullable=True)
    away_shots: Mapped[int | None] = mapped_column(Integer, nullable=True)
    home_shots_on_target: Mapped[int | None] = mapped_column(Integer, nullable=True)
    away_shots_on_target: Mapped[int | None] = mapped_column(Integer, nullable=True)
    home_fouls: Mapped[int | None] = mapped_column(Integer, nullable=True)
    away_fouls: Mapped[int | None] = mapped_column(Integer, nullable=True)
    home_corners: Mapped[int | None] = mapped_column(Integer, nullable=True)
    away_corners: Mapped[int | None] = mapped_column(Integer, nullable=True)
    home_yellow_cards: Mapped[int | None] = mapped_column(Integer, nullable=True)
    away_yellow_cards: Mapped[int | None] = mapped_column(Integer, nullable=True)
    home_red_cards: Mapped[int | None] = mapped_column(Integer, nullable=True)
    away_red_cards: Mapped[int | None] = mapped_column(Integer, nullable=True)
    # Bet365 1X2
    b365_home: Mapped[float | None] = mapped_column(Float, nullable=True)
    b365_draw: Mapped[float | None] = mapped_column(Float, nullable=True)
    b365_away: Mapped[float | None] = mapped_column(Float, nullable=True)
    # Betway 1X2
    bw_home: Mapped[float | None] = mapped_column(Float, nullable=True)
    bw_draw: Mapped[float | None] = mapped_column(Float, nullable=True)
    bw_away: Mapped[float | None] = mapped_column(Float, nullable=True)
    # Interwetten 1X2
    iw_home: Mapped[float | None] = mapped_column(Float, nullable=True)
    iw_draw: Mapped[float | None] = mapped_column(Float, nullable=True)
    iw_away: Mapped[float | None] = mapped_column(Float, nullable=True)
    # Pinnacle 1X2
    ps_home: Mapped[float | None] = mapped_column(Float, nullable=True)
    ps_draw: Mapped[float | None] = mapped_column(Float, nullable=True)
    ps_away: Mapped[float | None] = mapped_column(Float, nullable=True)
    # William Hill 1X2
    wh_home: Mapped[float | None] = mapped_column(Float, nullable=True)
    wh_draw: Mapped[float | None] = mapped_column(Float, nullable=True)
    wh_away: Mapped[float | None] = mapped_column(Float, nullable=True)
    # VC Bet 1X2
    vc_home: Mapped[float | None] = mapped_column(Float, nullable=True)
    vc_draw: Mapped[float | None] = mapped_column(Float, nullable=True)
    vc_away: Mapped[float | None] = mapped_column(Float, nullable=True)
    # Market max/avg 1X2
    max_home: Mapped[float | None] = mapped_column(Float, nullable=True)
    max_draw: Mapped[float | None] = mapped_column(Float, nullable=True)
    max_away: Mapped[float | None] = mapped_column(Float, nullable=True)
    avg_home: Mapped[float | None] = mapped_column(Float, nullable=True)
    avg_draw: Mapped[float | None] = mapped_column(Float, nullable=True)
    avg_away: Mapped[float | None] = mapped_column(Float, nullable=True)
    # Over/Under 2.5
    b365_over_25: Mapped[float | None] = mapped_column(Float, nullable=True)
    b365_under_25: Mapped[float | None] = mapped_column(Float, nullable=True)
    ps_over_25: Mapped[float | None] = mapped_column(Float, nullable=True)
    ps_under_25: Mapped[float | None] = mapped_column(Float, nullable=True)
    max_over_25: Mapped[float | None] = mapped_column(Float, nullable=True)
    max_under_25: Mapped[float | None] = mapped_column(Float, nullable=True)
    avg_over_25: Mapped[float | None] = mapped_column(Float, nullable=True)
    avg_under_25: Mapped[float | None] = mapped_column(Float, nullable=True)
    # Asian handicap
    ah_handicap: Mapped[float | None] = mapped_column(Float, nullable=True)
    b365_ah_home: Mapped[float | None] = mapped_column(Float, nullable=True)
    b365_ah_away: Mapped[float | None] = mapped_column(Float, nullable=True)
    ps_ah_home: Mapped[float | None] = mapped_column(Float, nullable=True)
    ps_ah_away: Mapped[float | None] = mapped_column(Float, nullable=True)
    max_ah_home: Mapped[float | None] = mapped_column(Float, nullable=True)
    max_ah_away: Mapped[float | None] = mapped_column(Float, nullable=True)
    avg_ah_home: Mapped[float | None] = mapped_column(Float, nullable=True)
    avg_ah_away: Mapped[float | None] = mapped_column(Float, nullable=True)
    # Closing 1X2
    b365c_home: Mapped[float | None] = mapped_column(Float, nullable=True)
    b365c_draw: Mapped[float | None] = mapped_column(Float, nullable=True)
    b365c_away: Mapped[float | None] = mapped_column(Float, nullable=True)
    bwc_home: Mapped[float | None] = mapped_column(Float, nullable=True)
    bwc_draw: Mapped[float | None] = mapped_column(Float, nullable=True)
    bwc_away: Mapped[float | None] = mapped_column(Float, nullable=True)
    iwc_home: Mapped[float | None] = mapped_column(Float, nullable=True)
    iwc_draw: Mapped[float | None] = mapped_column(Float, nullable=True)
    iwc_away: Mapped[float | None] = mapped_column(Float, nullable=True)
    psc_home: Mapped[float | None] = mapped_column(Float, nullable=True)
    psc_draw: Mapped[float | None] = mapped_column(Float, nullable=True)
    psc_away: Mapped[float | None] = mapped_column(Float, nullable=True)
    whc_home: Mapped[float | None] = mapped_column(Float, nullable=True)
    whc_draw: Mapped[float | None] = mapped_column(Float, nullable=True)
    whc_away: Mapped[float | None] = mapped_column(Float, nullable=True)
    vcc_home: Mapped[float | None] = mapped_column(Float, nullable=True)
    vcc_draw: Mapped[float | None] = mapped_column(Float, nullable=True)
    vcc_away: Mapped[float | None] = mapped_column(Float, nullable=True)
    maxc_home: Mapped[float | None] = mapped_column(Float, nullable=True)
    maxc_draw: Mapped[float | None] = mapped_column(Float, nullable=True)
    maxc_away: Mapped[float | None] = mapped_column(Float, nullable=True)
    avgc_home: Mapped[float | None] = mapped_column(Float, nullable=True)
    avgc_draw: Mapped[float | None] = mapped_column(Float, nullable=True)
    avgc_away: Mapped[float | None] = mapped_column(Float, nullable=True)
    # Closing Over/Under 2.5
    b365c_over_25: Mapped[float | None] = mapped_column(Float, nullable=True)
    b365c_under_25: Mapped[float | None] = mapped_column(Float, nullable=True)
    psc_over_25: Mapped[float | None] = mapped_column(Float, nullable=True)
    psc_under_25: Mapped[float | None] = mapped_column(Float, nullable=True)
    maxc_over_25: Mapped[float | None] = mapped_column(Float, nullable=True)
    maxc_under_25: Mapped[float | None] = mapped_column(Float, nullable=True)
    avgc_over_25: Mapped[float | None] = mapped_column(Float, nullable=True)
    avgc_under_25: Mapped[float | None] = mapped_column(Float, nullable=True)
    # Closing Asian handicap
    ahc_handicap: Mapped[float | None] = mapped_column(Float, nullable=True)
    b365c_ah_home: Mapped[float | None] = mapped_column(Float, nullable=True)
    b365c_ah_away: Mapped[float | None] = mapped_column(Float, nullable=True)
    psc_ah_home: Mapped[float | None] = mapped_column(Float, nullable=True)
    psc_ah_away: Mapped[float | None] = mapped_column(Float, nullable=True)
    maxc_ah_home: Mapped[float | None] = mapped_column(Float, nullable=True)
    maxc_ah_away: Mapped[float | None] = mapped_column(Float, nullable=True)
    avgc_ah_home: Mapped[float | None] = mapped_column(Float, nullable=True)
    avgc_ah_away: Mapped[float | None] = mapped_column(Float, nullable=True)
    source_updated_at: Mapped[str | None] = mapped_column(Text, nullable=True)

    __table_args__ = (UniqueConstraint("league", "season", "game"),)


class Shot(Base):
    """Individual shot events from Understat."""

    __tablename__ = "shots"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    league: Mapped[str] = mapped_column(Text, nullable=False)
    season: Mapped[str] = mapped_column(Text, nullable=False)
    game: Mapped[str] = mapped_column(Text, nullable=False)
    team: Mapped[str] = mapped_column(Text, nullable=False)
    player: Mapped[str] = mapped_column(Text, nullable=False)
    shot_id: Mapped[int] = mapped_column(Integer, nullable=False)
    date: Mapped[str | None] = mapped_column(Text, nullable=True)
    xg: Mapped[float | None] = mapped_column(Float, nullable=True)
    location_x: Mapped[float | None] = mapped_column(Float, nullable=True)
    location_y: Mapped[float | None] = mapped_column(Float, nullable=True)
    minute: Mapped[int | None] = mapped_column(Integer, nullable=True)
    body_part: Mapped[str | None] = mapped_column(Text, nullable=True)
    situation: Mapped[str | None] = mapped_column(Text, nullable=True)
    result: Mapped[str | None] = mapped_column(Text, nullable=True)
    assist_player: Mapped[str | None] = mapped_column(Text, nullable=True)
    player_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    assist_player_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    source_updated_at: Mapped[str | None] = mapped_column(Text, nullable=True)

    __table_args__ = (UniqueConstraint("shot_id"),)


class ScrapeLog(Base):
    """Tracking log for scraper runs (idempotency / dedup)."""

    __tablename__ = "scrape_log"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    source: Mapped[str] = mapped_column(Text, nullable=False)
    league: Mapped[str | None] = mapped_column(Text, nullable=True)
    season: Mapped[str | None] = mapped_column(Text, nullable=True)
    scraped_at: Mapped[str] = mapped_column(Text, nullable=False)
    row_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    status: Mapped[str] = mapped_column(Text, nullable=False)

    __table_args__ = (UniqueConstraint("source", "league", "season"),)
