"""Domain model dataclasses documenting the unified dataset schemas.

These define the output shape of the pipeline. Not used for storage
(pipeline works with DataFrames), but serve as documentation and
validation reference.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class MatchRecord:
    """One row in the unified matches table.

    Combines Understat (xG, PPDA), ESPN (possession, tackles, passes),
    Sofascore (round info), and ClubElo (team strength).
    """

    league: str
    season: str
    game: str
    date: str
    home_team: str
    away_team: str
    home_goals: int | None = None
    away_goals: int | None = None
    home_xg: float | None = None
    away_xg: float | None = None
    home_np_xg: float | None = None
    away_np_xg: float | None = None
    home_expected_points: float | None = None
    away_expected_points: float | None = None
    home_ppda: float | None = None
    away_ppda: float | None = None
    home_deep_completions: int | None = None
    away_deep_completions: int | None = None
    home_possession: float | None = None
    away_possession: float | None = None
    home_total_shots: int | None = None
    away_total_shots: int | None = None
    home_shots_on_target: int | None = None
    away_shots_on_target: int | None = None
    home_effective_tackles: int | None = None
    away_effective_tackles: int | None = None
    home_total_tackles: int | None = None
    away_total_tackles: int | None = None
    home_accurate_passes: int | None = None
    away_accurate_passes: int | None = None
    home_total_passes: int | None = None
    away_total_passes: int | None = None
    home_accurate_crosses: int | None = None
    away_accurate_crosses: int | None = None
    home_effective_clearance: int | None = None
    away_effective_clearance: int | None = None
    home_interceptions: int | None = None
    away_interceptions: int | None = None
    home_saves: int | None = None
    away_saves: int | None = None
    home_fouls: int | None = None
    away_fouls: int | None = None
    home_yellow_cards: int | None = None
    away_yellow_cards: int | None = None
    home_red_cards: int | None = None
    away_red_cards: int | None = None
    home_won_corners: int | None = None
    away_won_corners: int | None = None
    round: int | None = None
    week: int | None = None
    home_elo: float | None = None
    away_elo: float | None = None


@dataclass(frozen=True)
class PlayerMatchRecord:
    """One row in the unified player_matches table.

    Combines Understat (xG, xA) with ESPN (fouls, saves, subs).
    """

    league: str
    season: str
    game: str
    team: str
    player: str
    position: str | None = None
    minutes: int | None = None
    goals: int | None = None
    shots: int | None = None
    xg: float | None = None
    xa: float | None = None
    key_passes: int | None = None
    xg_chain: float | None = None
    xg_buildup: float | None = None
    own_goals: int | None = None
    assists: int | None = None
    fouls_committed: int | None = None
    fouls_suffered: int | None = None
    saves: int | None = None
    offsides: int | None = None
    total_shots_espn: int | None = None
    shots_on_target_espn: int | None = None
    sub_in: int | None = None
    sub_out: int | None = None
    yellow_cards: int | None = None
    red_cards: int | None = None


@dataclass(frozen=True)
class ShotRecord:
    """One row in the shots table.

    Individual shot events from Understat with xG and coordinates.
    """

    league: str
    season: str
    game: str
    team: str
    player: str
    shot_id: int
    date: str | None = None
    xg: float | None = None
    location_x: float | None = None
    location_y: float | None = None
    minute: int | None = None
    body_part: str | None = None
    situation: str | None = None
    result: str | None = None
    assist_player: str | None = None
    player_id: int | None = None
    assist_player_id: int | None = None
