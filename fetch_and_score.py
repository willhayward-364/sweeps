import json
import os
import re
from datetime import datetime, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

import requests

from rules import RULES
from layout import render_page
from version import read_version, write_api_fetch_timestamp

# Configuration & Flags
USE_MOCK_DATA = False  # 👈 Set to True for testing, False for production

# Dynamic date helpers (spread across the last 6 days) so mock matches stay inside the 7-day weekly window
_now = datetime.now(timezone.utc)
_day1 = (_now - timedelta(days=1)).strftime("%Y-%m-%dT%H:%M:%SZ")
_day2 = (_now - timedelta(days=2)).strftime("%Y-%m-%dT%H:%M:%SZ")
_day3 = (_now - timedelta(days=3)).strftime("%Y-%m-%dT%H:%M:%SZ")
_day4 = (_now - timedelta(days=4)).strftime("%Y-%m-%dT%H:%M:%SZ")
_day5 = (_now - timedelta(days=5)).strftime("%Y-%m-%dT%H:%M:%SZ")
_day6 = (_now - timedelta(days=6)).strftime("%Y-%m-%dT%H:%M:%SZ")

MOCK_MATCHES = [
    # Match 1: Player A (Arsenal) -> Win + Clean Sheet + Goal Feast (Home)
    {
        "competitionCode": "PL",
        "utcDate": _day1,
        "status": "FINISHED",
        "homeTeam": {"name": "Arsenal FC"},        # Player A (Pot 1)
        "awayTeam": {"name": "Newcastle United"},  # Player B (Pot 1)
        "score": {"fullTime": {"home": 3, "away": 0}},
    },
    # Match 2: Player A (Everton) -> Away Giant Kill + Clean Sheet + Goal Feast (Pot 3 vs Pot 1)
    {
        "competitionCode": "PL",
        "utcDate": _day2,
        "status": "FINISHED",
        "homeTeam": {"name": "Manchester City FC"}, # Player B (Pot 1)
        "awayTeam": {"name": "Everton FC"},         # Player A (Pot 3) -> Giant Kill!
        "score": {"fullTime": {"home": 0, "away": 3}},
    },
    # Match 3: Player C (Man Utd) vs Player E (Liverpool) -> 0-0 Draw (Draw + Clean Sheet for both)
    {
        "competitionCode": "PL",
        "utcDate": _day3,
        "status": "FINISHED",
        "homeTeam": {"name": "Ipswich Town"}, # Player C
        "awayTeam": {"name": "Liverpool FC"},          # Player E
        "score": {"fullTime": {"home": 0, "away": 0}},
    },
    # Match 4: Player D (Aston Villa) vs Player F (Bournemouth) -> High-scoring loss (Goal Feast for loser)
    {
        "competitionCode": "PL",
        "utcDate": _day4,
        "status": "FINISHED",
        "homeTeam": {"name": "Aston Villa FC"},       # Player D (Pot 1)
        "awayTeam": {"name": "AFC Bournemouth"},      # Player F (Pot 1)
        "score": {"fullTime": {"home": 4, "away": 3}},
    },
    # Match 5: Player D (Hull City) -> Home Giant Kill (Pot 4 vs Pot 1)
    {
        "competitionCode": "ELC",
        "utcDate": _day5,
        "status": "FINISHED",
        "homeTeam": {"name": "Hull City AFC"},        # Player D (Pot 4) -> Giant Kill!
        "awayTeam": {"name": "Tottenham Hotspur"},    # Player E (Pot 1)
        "score": {"fullTime": {"home": 1, "away": 0}},
    },
    # Match 6: Player F (Coventry) vs Player B (Burnley) -> Regular Win
    {
        "competitionCode": "ELC",
        "utcDate": _day6,
        "status": "FINISHED",
        "homeTeam": {"name": "Coventry City"},        # Player F (Pot 3)
        "awayTeam": {"name": "Burnley FC"},           # Player B (Pot 4)
        "score": {"fullTime": {"home": 2, "away": 1}},
    },
]

def load_upcoming_matches() -> list[dict]:
    if USE_MOCK_DATA:
        _next1 = (_now + timedelta(days=2)).strftime("%Y-%m-%dT15:00:00Z")
        _next2 = (_now + timedelta(days=3)).strftime("%Y-%m-%dT17:30:00Z")
        return [
            {
                "competitionCode": "PL",
                "utcDate": _next1,
                "status": "TIMED",
                "homeTeam": {"name": "Ipswich Town"},
                "awayTeam": {"name": "Liverpool FC"},
            },
            {
                "competitionCode": "PL",
                "utcDate": _next2,
                "status": "TIMED",
                "homeTeam": {"name": "Manchester City FC"},
                "awayTeam": {"name": "Everton FC"},
            },
        ]

    return fetch_upcoming_matches("PL")


def fetch_upcoming_matches(comp_code: str) -> list[dict]:
    # Fetch fixtures scheduled for the next 7 days
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    next_week = (datetime.now(timezone.utc) + timedelta(days=7)).strftime("%Y-%m-%d")
    
    url = f"https://api.football-data.org/v4/competitions/{comp_code}/matches?dateFrom={today}&dateTo={next_week}"
    try:
        response = requests.get(url, headers=HEADERS, timeout=10)
        response.raise_for_status()
        matches = response.json().get("matches", [])
        for match in matches:
            match["competitionCode"] = comp_code
        return matches
    except Exception as exc:
        print(f"⚠️ Could not fetch upcoming fixtures for {comp_code}: {exc}")
        return []

def load_matches() -> list[dict]:
    if USE_MOCK_DATA:
        print("🧪 RUNNING IN MOCK DATA MODE - Skipping Football-Data API calls...")
        return MOCK_MATCHES

    return (
    fetch_matches("PL")
    )
API_KEY = os.getenv("FOOTBALL_DATA_API_KEY", "").strip()
HEADERS = {"X-Auth-Token": API_KEY} if API_KEY else {}

PLAYERS = {
"Player A": ["Liverpool", "AFC Bournemouth", "Leeds United", "Ipswich Town"],
"Player B": ["Manchester City", "Aston Villa", "Sunderland", "Ipswich Town"],
"Player C": ["Manchester United", "Newcastle United", "Crystal Palace", "Hull City"],
"Player D": ["Tottenham Hotspur", "Brentford", "Coventry City", "Ipswich Town"],
"Player E": ["Arsenal", "Fulham", "Nottingham Forest", "Hull City"],
"Player F": ["Chelsea", "Brighton & Hove Albion", "Everton", "Hull City"],
}

POTS = {
    "pot1": ["Arsenal", "Manchester City", "Manchester United", "Tottenham Hotspur", "Liverpool", "Chelsea"],
    "pot2": ["AFC Bournemouth", "Newcastle United", "Brighton & Hove Albion", "Fulham", "Brentford", "Aston Villa"],  
    "pot3": ["Everton", "Leeds United", "Crystal Palace", "Nottingham Forest", "Sunderland", "Coventry"],
    "pot4": ["Hull City", "Ipswich Town"],
}

PLAYER_NICKNAMES = {
    "Player A": "364",
    "Player B": "Keano",
    "Player C": "Dookie",
    "Player D": "Rich",
    "Player E": "Robin",
    "Player F": "Davey",
}

PLAYER_AVATARS = {
    "Player A": "images/player_avatars/364_avatar.jpg",
    "Player B": "images/player_avatars/keano_avatar.jpg",
    "Player C": "images/player_avatars/dookie_avatar.jpg",
    "Player D": "images/player_avatars/Rich_avatar.jpg",
    "Player E": "images/player_avatars/Robin_avatar.jpg",
    "Player F": "images/player_avatars/Daveylad_avatar.jpg",
}


def get_player_display_name(player_id: str) -> str:
    return PLAYER_NICKNAMES.get(player_id, player_id)


UK_TIMEZONE = ZoneInfo("Europe/London")


def format_kickoff_time(utc_date: str, fallback: str) -> str:
    """Converts an API UTC kick-off time to UK time, e.g. '2026-10-25 16:30 GMT' / '... BST'."""
    if not utc_date:
        return fallback
    try:
        kickoff = datetime.fromisoformat(utc_date.replace("Z", "+00:00"))
    except ValueError:
        return fallback
    return kickoff.astimezone(UK_TIMEZONE).strftime("%Y-%m-%d %H:%M %Z")

# ==========================================
# Team Crest Lookup & Normalization Logic
# ==========================================

COMMON_ALIASES = {
    "man-city": "manchester-city",
    "man-utd": "manchester-united",
    "man-united": "manchester-united",
    "west-ham": "west-ham-united",
    "brighton": "brighton-hove-albion",
    "brighton-and-hove-albion": "brighton-hove-albion",
    "brighton-hove": "brighton-hove-albion",
    "wolves": "wolverhampton-wanderers",
    "wolverhampton": "wolverhampton-wanderers",
    "spurs": "tottenham-hotspur",
    "tottenham": "tottenham-hotspur",
    "newcastle": "newcastle-united",
    "newcastle-united-fc": "newcastle",
    "nottingham": "nottingham-forest",
    "leeds": "leeds-united",
    "ipswich": "ipswich-town",
    "coventry": "coventry-city",
    "hull": "hull-city",
}

TEAM_CREST_LOOKUP = {
    "arsenal": "england_arsenal.football-logos.cc.png",
    "aston-villa": "england_aston-villa.football-logos.cc.png",
    "afc-bournemouth": "england_bournemouth.football-logos.cc.png",
    "bournemouth": "england_bournemouth.football-logos.cc.png",
    "brentford": "england_brentford.football-logos.cc.png",
    "brighton-hove-albion": "england_brighton.football-logos.cc.png",
    "brighton-and-hove-albion": "england_brighton.football-logos.cc.png",
    "burnley": "england_burnley.football-logos.cc.png",
    "chelsea": "england_chelsea.football-logos.cc.png",
    "coventry": "england_coventry-city.football-logos.cc.png",
    "coventry-city": "england_coventry-city.football-logos.cc.png",
    "crystal-palace": "england_crystal-palace.football-logos.cc.png",
    "everton": "england_everton.football-logos.cc.png",
    "fulham": "england_fulham.football-logos.cc.png",
    "hull-city": "england_hull-city.football-logos.cc.png",
    "ipswich-town": "england_ipswich.football-logos.cc.png",
    "leeds-united": "england_leeds-united.football-logos.cc.png",
    "liverpool": "england_liverpool.football-logos.cc.png",
    "manchester-city": "england_manchester-city.football-logos.cc.png",
    "manchester-united": "england_manchester-united.football-logos.cc.png",
    "millwall": "england_millwall.football-logos.cc.png",
    "newcastle-united": "england_newcastle.football-logos.cc.png",
    "nottingham-forest": "england_nottingham-forest.football-logos.cc.png",
    "sunderland": "england_sunderland.football-logos.cc.png",
    "tottenham-hotspur": "england_tottenham.football-logos.cc.png",
    "west-ham-united": "england_west-ham.football-logos.cc.png",
    "wolverhampton-wanderers": "england_wolves.football-logos.cc.png",
}


def normalize_team_name(team_name: str) -> str:
    """Strips noise words (FC, AFC, Club) and converts short-names to standard slugs."""
    clean = re.sub(r"\b(fc|afc|club)\b", "", team_name, flags=re.IGNORECASE)
    slug = re.sub(r"[^a-z0-9]+", "-", clean.lower()).strip("-")
    return COMMON_ALIASES.get(slug, slug)

def get_player_avatar_path(player_id: str) -> str:
    """Resolves the relative path for a player's avatar image, falling back to placeholder.png if missing."""
    avatar_rel_path = PLAYER_AVATARS.get(player_id)

    if avatar_rel_path:
        full_path = Path(__file__).resolve().parent / avatar_rel_path
        if full_path.exists():
            return avatar_rel_path

    return "images/avatars/placeholder.png"

def get_team_crest_path(team_name: str) -> str | None:
    slug = normalize_team_name(team_name)
    mapped_name = TEAM_CREST_LOOKUP.get(slug)
    if mapped_name:
        crest_path = Path(__file__).with_name("images") / "crests" / mapped_name
        if crest_path.exists():
            return f"images/crests/{mapped_name}"

    fallback_path = Path(__file__).with_name("images") / "crests" / f"{slug}.svg"
    if fallback_path.exists():
        return f"images/crests/{slug}.svg"

    placeholder_path = Path(__file__).with_name("images") / "crests" / "placeholder.svg"
    if placeholder_path.exists():
        return "images/crests/placeholder.svg"

    return None


class MatchFetchError(Exception):
    """Raised when finished matches could not be fetched from the API."""


class StaleDataError(Exception):
    """Raised when the API returns fewer finished matches than already published."""


PUBLISHED_STATE_FILE = Path(__file__).resolve().parent / ".published_matches.json"


def check_matches_not_stale(matches: list[dict], state_file: Path = PUBLISHED_STATE_FILE) -> None:
    """Refuse to publish if the API sent an older copy of the data.

    The number of finished matches in a season only ever goes up, so fewer
    matches than last published (for the same season) means a stale API
    response. A new season resets the count. Delete the state file to force
    a publish.
    """
    season = next((m.get("seasonStartDate") for m in matches if m.get("seasonStartDate")), None)
    if not season or not state_file.exists():
        return
    try:
        previous = json.loads(state_file.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return
    if previous.get("season") == season and len(matches) < previous.get("finished_matches", 0):
        raise StaleDataError(
            f"API returned {len(matches)} finished matches but {previous['finished_matches']} "
            "are already published - looks like stale data."
        )


def record_published_matches(matches: list[dict], state_file: Path = PUBLISHED_STATE_FILE) -> None:
    season = next((m.get("seasonStartDate") for m in matches if m.get("seasonStartDate")), None)
    if season:
        state_file.write_text(
            json.dumps({"season": season, "finished_matches": len(matches)}, indent=2) + "\n",
            encoding="utf-8",
        )


def fetch_matches(comp_code: str):
    competition_url = f"https://api.football-data.org/v4/competitions/{comp_code}"

    try:
        competition_response = requests.get(competition_url, headers=HEADERS, timeout=10)
        competition_response.raise_for_status()
        competition_data = competition_response.json()

        current_season = competition_data.get("currentSeason", {})
        start_date = current_season.get("startDate")
        end_date = current_season.get("endDate")

        if not start_date or not end_date:
            raise ValueError(
                f"Current season dates not available for competition {comp_code}"
            )

        matches_url = (
            f"https://api.football-data.org/v4/competitions/{comp_code}/matches"
            f"?status=FINISHED&dateFrom={start_date}&dateTo={end_date}"
        )
        response = requests.get(matches_url, headers=HEADERS, timeout=10)
        response.raise_for_status()

        matches = response.json().get("matches", [])
        for match in matches:
            match["competitionCode"] = comp_code
            match["seasonStartDate"] = start_date
        return matches
    except (requests.RequestException, ValueError) as exc:
        # Raise rather than returning [] so a failed fetch can't be mistaken for
        # "no matches" and publish a site with everyone on 0 points.
        raise MatchFetchError(f"Error fetching {comp_code}: {exc}") from exc
    


def team_is_in_player_selection(team_name: str, selected_teams: list[str]) -> bool:
    """Checks if an API team matches any team in a player's selection list using normalized slugs."""
    target_slug = normalize_team_name(team_name)
    return any(normalize_team_name(selected) == target_slug for selected in selected_teams)


def calculate_scores(matches: list[dict]):
    player_scores = {
        player: {"points": 0, "wins": 0, "draws": 0, "clean_sheets": 0,"goal_feasts": 0, "giant_kills": 0}
        for player in PLAYERS
    }

    rule_points = {rule["ref"]: rule["points"] for rule in RULES}

    for match in matches:
        home_team = match.get("homeTeam", {}).get("name", "")
        away_team = match.get("awayTeam", {}).get("name", "")

        score = match.get("score", {}).get("fullTime", {})
        home_score = score.get("home")
        away_score = score.get("away")

        if home_score is None or away_score is None:
            continue

        for player, teams in PLAYERS.items():
            home_selected = team_is_in_player_selection(home_team, teams)
            away_selected = team_is_in_player_selection(away_team, teams)

            if home_selected:
                if home_score > away_score:
                    player_scores[player]["points"] += rule_points["R1"]
                    player_scores[player]["wins"] += 1
                elif home_score == away_score:
                    player_scores[player]["points"] += rule_points["R2"]
                    player_scores[player]["draws"] += 1

                if away_score == 0:
                    player_scores[player]["points"] += rule_points["R3"]
                    player_scores[player]["clean_sheets"] += 1

                if home_score >= 3:
                    player_scores[player]["points"] += rule_points["R4"]
                    player_scores[player]["goal_feasts"] += 1
                if (
                    home_score > away_score
                    and team_is_in_player_selection(home_team, POTS["pot3"] + POTS["pot4"])
                    and team_is_in_player_selection(away_team, POTS["pot1"])
                ):
                    player_scores[player]["points"] += rule_points["R5"]
                    player_scores[player]["giant_kills"] += 1

            if away_selected:
                if away_score > home_score:
                    player_scores[player]["points"] += rule_points["R1"]
                    player_scores[player]["wins"] += 1
                elif home_score == away_score:
                    player_scores[player]["points"] += rule_points["R2"]
                    player_scores[player]["draws"] += 1

                if home_score == 0:
                    player_scores[player]["points"] += rule_points["R3"]
                    player_scores[player]["clean_sheets"] += 1

                if away_score >= 3:
                    player_scores[player]["points"] += rule_points["R4"]
                    player_scores[player]["goal_feasts"] += 1
                if (
                    away_score > home_score
                    and team_is_in_player_selection(away_team, POTS["pot3"] + POTS["pot4"])
                    and team_is_in_player_selection(home_team, POTS["pot1"])
                ):
                    player_scores[player]["points"] += rule_points["R5"]
                    player_scores[player]["giant_kills"] += 1

    return player_scores


def _score_team_in_match(team: str, opponent: str, scored: int, conceded: int) -> list[tuple[str, int]]:
    """Returns the (reason, points) items one selected team earned in a match."""
    rule_points = {rule["ref"]: rule["points"] for rule in RULES}
    items: list[tuple[str, int]] = []
    if scored > conceded:
        items.append(("win", rule_points["R1"]))
    elif scored == conceded:
        items.append(("draw", rule_points["R2"]))
    if conceded == 0:
        items.append(("clean sheet", rule_points["R3"]))
    if scored >= 3:
        items.append(("goal feast", rule_points["R4"]))
    if (
        scored > conceded
        and team_is_in_player_selection(team, POTS["pot3"] + POTS["pot4"])
        and team_is_in_player_selection(opponent, POTS["pot1"])
    ):
        items.append(("giant kill", rule_points["R5"]))
    return items


def _selected_team_name(api_team: str, selected_teams: list[str]) -> str:
    """Returns the player's own name for a team (e.g. 'Liverpool' for 'Liverpool FC')."""
    slug = normalize_team_name(api_team)
    return next((t for t in selected_teams if normalize_team_name(t) == slug), api_team)


def calculate_match_breakdown(match: dict) -> list[dict]:
    """Per-player points for one match, split by each of the player's teams involved.

    Every player with a team in the match is included (zero-point players too),
    sorted with the highest scorers first.
    """
    home_team = match.get("homeTeam", {}).get("name", "")
    away_team = match.get("awayTeam", {}).get("name", "")

    score = match.get("score", {}).get("fullTime", {})
    home_score = score.get("home")
    away_score = score.get("away")

    if home_score is None or away_score is None:
        return []

    sides = [
        (home_team, away_team, home_score, away_score),
        (away_team, home_team, away_score, home_score),
    ]

    breakdown = []
    for player, teams in PLAYERS.items():
        team_entries = []
        for team, opponent, scored, conceded in sides:
            if not team_is_in_player_selection(team, teams):
                continue
            items = _score_team_in_match(team, opponent, scored, conceded)
            team_entries.append(
                {
                    "team": _selected_team_name(team, teams),
                    "points": sum(pts for _, pts in items),
                    "items": items,
                }
            )

        if not team_entries:
            continue

        breakdown.append(
            {
                "player": player,
                "display_name": get_player_display_name(player),
                "points": sum(entry["points"] for entry in team_entries),
                "teams": team_entries,
                "reasons": [reason for entry in team_entries for reason, _ in entry["items"]] or ["loss"],
            }
        )

    breakdown.sort(key=lambda item: item["points"], reverse=True)
    return breakdown



# ==========================================
# Shared building blocks
# ==========================================
REASON_LABELS = {
    "win": "Win",
    "draw": "Draw",
    "clean sheet": "Clean sheet",
    "goal feast": "Goal feast",
    "giant kill": "Giant kill",
}


# Crests that are too dark to see on the dark background get a light circle behind them
DARK_CRESTS = {"tottenham-hotspur"}


def crest_img(team_name: str, css_class: str = "crest") -> str:
    path = get_team_crest_path(team_name)
    if not path:
        return ""
    if normalize_team_name(team_name) in DARK_CRESTS:
        css_class += " crest-on-light"
    return f'<img class="{css_class}" src="{path}" alt="{team_name}" title="{team_name}" loading="lazy">'


def avatar_img(player_id: str, css_class: str = "avatar") -> str:
    return f'<img class="{css_class}" src="{get_player_avatar_path(player_id)}" alt="" loading="lazy">'


def uk_kickoff(utc_date: str) -> datetime | None:
    try:
        return datetime.fromisoformat(utc_date.replace("Z", "+00:00")).astimezone(UK_TIMEZONE)
    except (AttributeError, ValueError):
        return None


def match_team_names(match: dict) -> tuple[str, str]:
    home = match.get("homeTeam", {})
    away = match.get("awayTeam", {})
    return (
        home.get("shortName") or home.get("name", "Unknown"),
        away.get("shortName") or away.get("name", "Unknown"),
    )


def render_match_line(home_team: str, away_team: str, badge: str, time_label: str) -> str:
    return f"""
    <div class="match-line">
      <span class="match-team home"><span class="team-name">{home_team}</span>{crest_img(home_team, "crest crest-lg")}</span>
      <span class="match-mid"><span class="match-badge">{badge}</span><span class="match-time">{time_label}</span></span>
      <span class="match-team away">{crest_img(away_team, "crest crest-lg")}<span class="team-name">{away_team}</span></span>
    </div>"""


def render_day_grouped(cards: list[tuple[datetime | None, str]]) -> str:
    """Puts a UK-date heading above each run of cards from the same day."""
    html, current_day = "", None
    for kickoff, card_html in cards:
        day_label = kickoff.strftime("%A %-d %B") if kickoff else "Date to be confirmed"
        if day_label != current_day:
            html += f'\n  <h2 class="section-heading">{day_label}</h2>'
            current_day = day_label
        html += card_html
    return html


# ==========================================
# Standings & Form: points tables
# ==========================================
TABLE_KEY = '<div class="table-key">W wins · D draws · CS clean sheets · GF goal feasts · GK giant kills</div>'


def render_points_table(scores: dict, show_teams: bool = True) -> str:
    """Compact table: rank (shared on equal points), player, optional team crests, stats, points."""
    sorted_scores = sorted(scores.items(), key=lambda item: item[1]["points"], reverse=True)

    rows = []
    for player, data in sorted_scores:
        rank = 1 + sum(1 for other in scores.values() if other["points"] > data["points"])
        teams_cell = (
            f'\n        <td class="col-teams">{"".join(crest_img(t) for t in PLAYERS[player])}</td>'
            if show_teams else ""
        )
        rows.append(
            f"""
      <tr data-player="{player}">
        <td class="col-rank">{rank}</td>
        <td class="col-player"><span class="player-name">{avatar_img(player)}{get_player_display_name(player)}</span></td>{teams_cell}
        <td class="col-stat">{data['wins']}</td>
        <td class="col-stat">{data['draws']}</td>
        <td class="col-stat">{data['clean_sheets']}</td>
        <td class="col-stat">{data['goal_feasts']}</td>
        <td class="col-stat">{data['giant_kills']}</td>
        <td class="col-pts">{data['points']}</td>
      </tr>"""
        )

    teams_head = '\n          <th class="col-teams">Teams</th>' if show_teams else ""
    return f"""
  <div class="card table-card">
    <table class="data-table">
      <thead>
        <tr>
          <th class="col-rank">#</th>
          <th class="col-player">Player</th>{teams_head}
          <th class="col-stat" title="Wins">W</th>
          <th class="col-stat" title="Draws">D</th>
          <th class="col-stat" title="Clean sheets">CS</th>
          <th class="col-stat" title="Goal feasts">GF</th>
          <th class="col-stat" title="Giant kills">GK</th>
          <th class="col-pts">Pts</th>
        </tr>
      </thead>
      <tbody>{''.join(rows)}
      </tbody>
    </table>
    {TABLE_KEY}
  </div>"""


def render_html(scores: dict, matches: list[dict] | None = None, version: str | None = None, output_path: str | None = None):
    """Standings page (index.html): the full league table."""
    render_page(
        page="index.html",
        title="Standings · LSB Sweepstake",
        heading="🏆 Standings 2026/27",
        body=render_points_table(scores, show_teams=True),
        output_path=output_path or Path(__file__).with_name("index.html"),
        version=version,
    )


def calculate_weekly_scores(matches: list[dict]) -> dict:
    """Filters matches completed in the last 7 days and calculates weekly points."""
    now = datetime.now(timezone.utc)
    seven_days_ago = now - timedelta(days=7)

    recent_matches = []
    for match in matches:
        utc_date_str = match.get("utcDate")
        if utc_date_str and match.get("status") == "FINISHED":
            match_time = datetime.fromisoformat(utc_date_str.replace("Z", "+00:00"))
            if match_time >= seven_days_ago:
                recent_matches.append(match)

    return calculate_scores(recent_matches)


def render_form_page(matches: list[dict], version: str | None = None, output_path: str | None = None):
    """Form page (form.html): points scored in the last 7 days."""
    body = '  <h2 class="section-heading">Last 7 days</h2>' + render_points_table(
        calculate_weekly_scores(matches), show_teams=False
    )
    render_page(
        page="form.html",
        title="Form · LSB Sweepstake",
        heading="⚡ Form",
        body=body,
        output_path=output_path or Path(__file__).with_name("form.html"),
        version=version,
    )


# ==========================================
# Players page
# ==========================================
def get_team_pot(team_name: str) -> str:
    for pot_key, teams in POTS.items():
        if team_is_in_player_selection(team_name, teams):
            return pot_key.replace("pot", "Pot ")
    return ""


def render_players_page(version: str | None = None, output_path: str | None = None):
    cards = []
    for player, teams in PLAYERS.items():
        team_rows = "".join(
            f"""
        <div class="team-row">{crest_img(team)}<span class="team-row-name">{team}</span><span class="muted">{get_team_pot(team)}</span></div>"""
            for team in teams
        )
        cards.append(
            f"""
  <div class="card player-card">
    <div class="player-card-head">{avatar_img(player, "avatar avatar-lg")}<span class="player-name">{get_player_display_name(player)}</span></div>
    <div class="team-list">{team_rows}
    </div>
  </div>"""
        )
    render_page(
        page="players.html",
        title="Players · LSB Sweepstake",
        heading="👥 Players",
        body="".join(cards),
        output_path=output_path or Path(__file__).with_name("players.html"),
        version=version,
    )


# ==========================================
# Latest results page
# ==========================================
def render_match_breakdown(breakdown: list[dict]) -> str:
    """Each involved player: name and total on one line, then a line per team with its point tags."""
    if not breakdown:
        return '\n      <div class="empty-note">No sweepstake players involved</div>'

    rows = []
    for item in breakdown:
        total = item["points"]
        team_parts = []
        for entry in item["teams"]:
            if entry["items"]:
                tags = "".join(
                    f'<span class="tag">{REASON_LABELS[reason]} +{pts}</span>'
                    for reason, pts in entry["items"]
                )
            else:
                tags = '<span class="tag tag-muted">Loss</span>'
            team_parts.append(f"""
        <div class="team-line">{crest_img(entry["team"])}<span class="team-tags">{tags}</span></div>""")

        rows.append(
            f"""
      <div class="player-block">
        <div class="player-block-head">
          <span class="player-name">{avatar_img(item['player'])}{item['display_name']}</span>
          <span class="row-total">{f"+{total}" if total else "0"}</span>
        </div>{''.join(team_parts)}
      </div>"""
        )
    return "".join(rows)


def render_latest_results_page(matches: list[dict], version: str | None = None, output_path: str | None = None):
    sorted_matches = sorted(matches, key=lambda match: match.get("utcDate", ""), reverse=True)[:380]

    cards = []
    for match in sorted_matches:
        kickoff = uk_kickoff(match.get("utcDate", ""))
        home_team, away_team = match_team_names(match)
        score = match.get("score", {}).get("fullTime", {})
        home_score, away_score = score.get("home"), score.get("away")
        badge = f"{home_score}-{away_score}" if home_score is not None and away_score is not None else "TBD"
        time_label = kickoff.strftime("%H:%M %Z") if kickoff else ""

        cards.append((kickoff, f"""
  <div class="card match-card">{render_match_line(home_team, away_team, badge, time_label)}
    <div class="match-rows">{render_match_breakdown(calculate_match_breakdown(match))}
    </div>
  </div>"""))

    body = render_day_grouped(cards) or '  <div class="card empty-note">No results yet.</div>'
    render_page(
        page="latest_results.html",
        title="Results · LSB Sweepstake",
        heading="⚽ Latest Results",
        body=body,
        output_path=output_path or Path(__file__).with_name("latest_results.html"),
        version=version,
    )


# ==========================================
# Upcoming fixtures page
# ==========================================
def render_team_owners(team_name: str) -> str:
    """Small avatar + name for every player who owns the team."""
    return "".join(
        f'<span class="owner">{avatar_img(player, "avatar avatar-sm")}{get_player_display_name(player)}</span>'
        for player, teams in PLAYERS.items()
        if team_is_in_player_selection(team_name, teams)
    )


def render_fixture_owners(home_team: str, away_team: str) -> str:
    """Owners listed under each side of the fixture, lined up with the teams above."""
    return f"""
    <div class="owners-line">
      <span class="owners home">{render_team_owners(home_team)}</span>
      <span></span>
      <span class="owners away">{render_team_owners(away_team)}</span>
    </div>"""


def render_upcoming_fixtures_page(version: str | None = None, output_path: str | None = None):
    # The API returns all of today's matches, so leave out ones already played
    finished_statuses = {"FINISHED", "AWARDED", "CANCELLED"}
    upcoming = [m for m in load_upcoming_matches() if m.get("status") not in finished_statuses]
    matches = sorted(upcoming, key=lambda match: match.get("utcDate", ""))[:25]

    cards = []
    for match in matches:
        kickoff = uk_kickoff(match.get("utcDate", ""))
        home_team, away_team = match_team_names(match)
        badge = kickoff.strftime("%H:%M") if kickoff else "TBC"
        time_label = kickoff.strftime("%Z") if kickoff else ""
        cards.append((kickoff, f"""
  <div class="card match-card">{render_match_line(home_team, away_team, badge, time_label)}{render_fixture_owners(home_team, away_team)}
  </div>"""))

    body = render_day_grouped(cards) or '  <div class="card empty-note">No fixtures in the next 7 days.</div>'
    render_page(
        page="upcoming_fixtures.html",
        title="Fixtures · LSB Sweepstake",
        heading="📅 Upcoming Fixtures",
        body=body,
        output_path=output_path or Path(__file__).with_name("upcoming_fixtures.html"),
        version=version,
    )


# ==========================================
# Rules page: pots grid
# ==========================================
POT_LABELS = {
    "pot1": "Pot 1 · Top tier",
    "pot2": "Pot 2 · Upper tier",
    "pot3": "Pot 3 · Mid tier",
    "pot4": "Pot 4 · Challengers",
}


def render_pots_quadrant() -> str:
    cards = []
    for pot_key, label in POT_LABELS.items():
        team_rows = "".join(
            f'\n        <div class="team-row">{crest_img(team)}<span class="team-row-name">{team}</span></div>'
            for team in POTS.get(pot_key, [])
        )
        cards.append(
            f"""
    <div class="card pot-card">
      <div class="card-heading">{label}</div>
      <div class="team-list">{team_rows}
      </div>
    </div>"""
        )
    return '  <div class="pots-grid">' + "".join(cards) + "\n  </div>"


if __name__ == "__main__":
    import sys

    from rules import render_rules_page

    # 1. Fetch results first. If the API fails, stop before writing anything so
    #    the published site keeps its last good results.
    try:
        matches = load_matches()
        check_matches_not_stale(matches)
    except (MatchFetchError, StaleDataError) as exc:
        print(f"❌ {exc}")
        print("Aborting without updating any pages.")
        sys.exit(1)

    # 2. Record when the API was successfully fetched
    timestamp = os.getenv("DEPLOYMENT_TIMESTAMP") or datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    write_api_fetch_timestamp(timestamp)

    # 3. Site version (set by hand in version.py)
    next_version = read_version()

    # 4. Scoring and page generation
    scores = calculate_scores(matches)
    render_html(scores, matches, version=next_version)
    render_form_page(matches, version=next_version)
    render_players_page(version=next_version)
    render_latest_results_page(matches, version=next_version)
    render_upcoming_fixtures_page(version=next_version)
    render_rules_page(pots_html=render_pots_quadrant(), version=next_version)
    record_published_matches(matches)