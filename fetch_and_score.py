import os
import re
from datetime import datetime, timezone
from pathlib import Path

import requests

from rules import RULES
from version import (
    bump_version,
    get_version_banner,
    read_version,
    write_api_fetch_timestamp,
    write_version,
)

# Configuration & Flags
USE_MOCK_DATA = false  # 👈 Set to True for testing, False for production

MOCK_MATCHES = [
    # Match 1: Player A (Arsenal) -> Win + Clean Sheet + Goal Feast (Home)
    {
        "competitionCode": "PL",
        "utcDate": "2026-08-15T14:00:00Z",
        "homeTeam": {"name": "Arsenal FC"},        # Player A (Pot 1)
        "awayTeam": {"name": "Newcastle United"},  # Player B (Pot 1)
        "score": {"fullTime": {"home": 3, "away": 0}},
    },
    # Match 2: Player A (Everton) -> Away Giant Kill + Clean Sheet + Goal Feast (Pot 3 vs Pot 1)
    {
        "competitionCode": "PL",
        "utcDate": "2026-08-22T16:30:00Z",
        "homeTeam": {"name": "Manchester City FC"}, # Player B (Pot 1)
        "awayTeam": {"name": "Everton FC"},         # Player A (Pot 3) -> Giant Kill!
        "score": {"fullTime": {"home": 0, "away": 3}},
    },
    # Match 3: Player C (Man Utd) vs Player E (Liverpool) -> 0-0 Draw (Draw + Clean Sheet for both)
    {
        "competitionCode": "PL",
        "utcDate": "2026-08-29T11:30:00Z",
        "homeTeam": {"name": "Manchester United FC"}, # Player C
        "awayTeam": {"name": "Liverpool FC"},          # Player E
        "score": {"fullTime": {"home": 0, "away": 0}},
    },
    # Match 4: Player D (Aston Villa) vs Player F (Bournemouth) -> High-scoring loss (Goal Feast for loser)
    {
        "competitionCode": "PL",
        "utcDate": "2026-09-05T14:00:00Z",
        "homeTeam": {"name": "Aston Villa FC"},       # Player D (Pot 1)
        "awayTeam": {"name": "AFC Bournemouth"},      # Player F (Pot 1)
        "score": {"fullTime": {"home": 4, "away": 3}},
    },
    # Match 5: Player D (Hull City) -> Home Giant Kill (Pot 4 vs Pot 1)
    {
        "competitionCode": "ELC",
        "utcDate": "2026-09-12T18:00:00Z",
        "homeTeam": {"name": "Hull City AFC"},        # Player D (Pot 4) -> Giant Kill!
        "awayTeam": {"name": "Tottenham Hotspur"},    # Player E (Pot 3)
        "score": {"fullTime": {"home": 1, "away": 0}},
    },
    # Match 6: Player F (Coventry) vs Player B (Burnley) -> Regular Win
    {
        "competitionCode": "ELC",
        "utcDate": "2026-09-19T14:00:00Z",
        "homeTeam": {"name": "Coventry City"},        # Player F (Pot 3)
        "awayTeam": {"name": "Burnley FC"},           # Player B (Pot 4)
        "score": {"fullTime": {"home": 2, "away": 1}},
    },
]


def load_matches() -> list[dict]:
    if USE_MOCK_DATA:
        print("🧪 RUNNING IN MOCK DATA MODE - Skipping Football-Data API calls...")
        return MOCK_MATCHES

    return (
        fetch_matches("PL")
        + fetch_matches("ELC")
    )
API_KEY = os.getenv("FOOTBALL_DATA_API_KEY", "").strip()
HEADERS = {"X-Auth-Token": API_KEY} if API_KEY else {}

PLAYERS = {
    "Player A": ["Arsenal", "Chelsea", "Everton", "West Ham United"],
    "Player B": ["Manchester City", "Newcastle United", "Leeds United", "Burnley"],
    "Player C": ["Manchester United", "Brentford", "Crystal Palace", "Wolverhampton Wanderers"],
    "Player D": ["Aston Villa", "Brighton & Hove Albion", "Nottingham Forest", "Hull City"],
    "Player E": ["Liverpool", "Sunderland", "Tottenham Hotspur", "Ipswich Town"],
    "Player F": ["AFC Bournemouth", "Fulham", "Coventry City", "Southampton"],
}

POTS = {
    "pot1": ["Arsenal", "Manchester City", "Manchester United", "Aston Villa", "Liverpool", "AFC Bournemouth"],
    "pot3": ["Everton", "Leeds United", "Crystal Palace", "Nottingham Forest", "Tottenham Hotspur", "Coventry City"],
    "pot4": ["Hull City", "Ipswich Town", "West Ham United", "Burnley", "Wolverhampton Wanderers", "Southampton"],
}

PLAYER_NICKNAMES = {
    "Player A": "364",
    "Player B": "Keano",
    "Player C": "Dookie",
    "Player D": "Rich",
    "Player E": "Robin",
    "Player F": "Daveylad",
}

NAV_LINKS = """
      <a href="index.html" class="nav-btn">Standings</a>
      <a href="players.html" class="nav-btn">Players</a>
      <a href="latest_results.html" class="nav-btn">Latest Results</a>
      <a href="rules.html" class="nav-btn">Rules</a>
    """


def get_player_display_name(player_id: str) -> str:
    return PLAYER_NICKNAMES.get(player_id, player_id)


TEAM_CREST_LOOKUP = {
    "arsenal": "england_arsenal.football-logos.cc.svg",
    "chelsea": "england_chelsea.football-logos.cc.svg",
    "everton": "england_everton.football-logos.cc.svg",
    "west-ham-united": "england_west-ham.football-logos.cc.svg",
    "manchester-city": "england_manchester-city.football-logos.cc.svg",
    "newcastle-united": "england_newcastle.football-logos.cc.svg",
    "leeds-united": "england_leeds-united.football-logos.cc.svg",
    "burnley": "england_burnley.football-logos.cc.svg",
    "manchester-united": "england_manchester-united.football-logos.cc.svg",
    "brentford": "england_brentford.football-logos.cc.svg",
    "crystal-palace": "england_crystal-palace.football-logos.cc.svg",
    "wolverhampton-wanderers": "england_wolves.football-logos.cc.svg",
    "aston-villa": "england_aston-villa.football-logos.cc.svg",
    "brighton-hove-albion": "england_brighton.football-logos.cc.svg",
    "brighton-and-hove-albion": "england_brighton.football-logos.cc.svg",
    "tottenham-hotspur": "england_tottenham.football-logos.cc.svg",
    "ipswich-town": "england_ipswich.football-logos.cc.svg",
    "afc-bournemouth": "england_bournemouth.football-logos.cc.svg",
    "bournemouth": "england_bournemouth.football-logos.cc.svg",
    "fulham": "england_fulham.football-logos.cc.svg",
    "coventry-city": "england_coventry-city.football-logos.cc.svg",
}


def normalize_team_name(team_name: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", team_name.lower()).strip("-")


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


def render_team_label(team_name: str, css_class: str = "team-label") -> str:
    crest_path = get_team_crest_path(team_name)
    crest_html = (
        f'<img class="team-crest" src="{crest_path}" alt="{team_name} crest" loading="lazy">'
        if crest_path
        else ""
    )
    return f'<span class="{css_class}">{crest_html}<span class="team-name-text">{team_name}</span></span>'


def render_team_chip_list(team_names: list[str]) -> str:
    return " ".join(
        render_team_label(team_name, css_class="team-chip") for team_name in team_names
    )


def render_topbar() -> str:
    return f"""
  <div class="topbar">
    <strong>🏆 Sweepstake</strong>
    <div class="nav-links">{NAV_LINKS}</div>
  </div>
"""


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
        return matches
    except requests.RequestException as exc:
        print(f"Error fetching {comp_code}: {exc}")
        return []
    except ValueError as exc:
        print(f"Error fetching {comp_code}: {exc}")
        return []


def load_matches() -> list[dict]:
    return (
        fetch_matches("PL")
        + fetch_matches("ELC")
    )


def team_is_in_player_selection(team_name: str, selected_teams: list[str]) -> bool:
    """Robust team matching to handle API suffixes like 'Arsenal FC' matching 'Arsenal'."""
    clean_api_name = team_name.replace(" FC", "").strip().lower()
    return any(
        selected.lower() == clean_api_name or selected.lower() in team_name.lower()
        for selected in selected_teams
    )


def calculate_scores(matches: list[dict]):
    player_scores = {
        player: {"points": 0, "wins": 0, "draws": 0, "clean_sheets": 0, "giant_kills": 0}
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

                if (
                    away_score > home_score
                    and team_is_in_player_selection(away_team, POTS["pot3"] + POTS["pot4"])
                    and team_is_in_player_selection(home_team, POTS["pot1"])
                ):
                    player_scores[player]["points"] += rule_points["R5"]
                    player_scores[player]["giant_kills"] += 1

    return player_scores


def calculate_match_breakdown(match: dict) -> list[dict]:
    home_team = match.get("homeTeam", {}).get("name", "")
    away_team = match.get("awayTeam", {}).get("name", "")

    score = match.get("score", {}).get("fullTime", {})
    home_score = score.get("home")
    away_score = score.get("away")

    if home_score is None or away_score is None:
        return []

    breakdown = []
    for player, teams in PLAYERS.items():
        points = 0
        reasons: list[str] = []

        home_selected = team_is_in_player_selection(home_team, teams)
        away_selected = team_is_in_player_selection(away_team, teams)

        if home_selected:
            if home_score > away_score:
                points += 3
                reasons.append("win")
            elif home_score == away_score:
                points += 1
                reasons.append("draw")

            if away_score == 0:
                points += 1
                reasons.append("clean sheet")

            if home_score >= 3:
                points += 1
                reasons.append("goal feast")

        if away_selected:
            if away_score > home_score:
                points += 3
                reasons.append("win")
            elif home_score == away_score:
                points += 1
                reasons.append("draw")

            if home_score == 0:
                points += 1
                reasons.append("clean sheet")

            if away_score >= 3:
                points += 1
                reasons.append("goal feast")

        if points:
            nickname = get_player_display_name(player)
            display_label = f"{player} ({nickname})" if nickname and nickname != player else player
            breakdown.append(
                {
                    "player": player,
                    "display_name": nickname,
                    "display_label": display_label,
                    "points": points,
                    "reasons": reasons,
                }
            )

    return breakdown


def render_html(scores, version: str | None = None, output_path: str | None = None):
    version_banner = get_version_banner(version=version)
    sorted_scores = sorted(scores.items(), key=lambda item: item[1]["points"], reverse=True)

    cards_html = ""
    for rank, (player, data) in enumerate(sorted_scores, 1):
        teams_html = render_team_chip_list(PLAYERS[player])
        display_name = get_player_display_name(player)
        cards_html += f"""
        <div class="card">
            <span class="score">{data['points']} pts</span>
            <div class="player-name">#{rank} {display_name}</div>
            <div class="player-id">{player}</div>
            <div class="teams">{teams_html}</div>
            <div class="stats">Wins: {data['wins']} | Draws: {data['draws']} | Clean Sheets: {data['clean_sheets']}</div>
        </div>
        """

    html_content = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>2026/27 Premier League Sweepstake</title>
 <link rel="stylesheet" href="style.css">
</head>
<body>
  {render_topbar()}
  <h1>🏆 2026/27 Sweepstake Standings</h1>
  {version_banner}
  {cards_html}
</body>
</html>"""

    target_path = Path(output_path) if output_path else Path(__file__).with_name("index.html")
    target_path.write_text(html_content, encoding="utf-8")


def render_players_page(version: str | None = None, output_path: str | None = None):
    version_banner = get_version_banner(version=version)
    cards_html = ""
    for player, teams in PLAYERS.items():
        display_name = get_player_display_name(player)
        teams_str = ", ".join(teams)
        cards_html += f"""
        <div class="card">
            <div class="player-name">{display_name}</div>
            <div class="player-id">{player}</div>
            <div class="teams">{teams_str}</div>
        </div>
        """

    html_content = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Players</title>
<link rel="stylesheet" href="style.css">
</head>
<body>
  {render_topbar()}
  <h1>🏆 Players</h1>
  {version_banner}
  {cards_html}
</body>
</html>"""

    target_path = Path(output_path) if output_path else Path(__file__).with_name("players.html")
    target_path.write_text(html_content, encoding="utf-8")


def render_latest_results_page(matches: list[dict], version: str | None = None, output_path: str | None = None):
    version_banner = get_version_banner(version=version)

    sorted_matches = sorted(
        matches, key=lambda match: match.get("utcDate", ""), reverse=True
    )
    recent_matches = sorted_matches[:25]

    matches_html = ""
    for match in recent_matches:
        comp = match.get("competitionCode", "Unknown")
        raw_date = match.get("utcDate", "")
        date_str = (
            raw_date.replace("T", " ")[:16] if raw_date else "Unknown Date"
        )

        home_team = (
            match.get("homeTeam", {}).get("shortName")
            or match.get("homeTeam", {}).get("name", "Unknown")
        )
        away_team = (
            match.get("awayTeam", {}).get("shortName")
            or match.get("awayTeam", {}).get("name", "Unknown")
        )

        score = match.get("score", {}).get("fullTime", {})
        home_score = score.get("home")
        away_score = score.get("away")

        score_display = (
            f"{home_score} - {away_score}"
            if home_score is not None and away_score is not None
            else "TBD"
        )

        breakdown = calculate_match_breakdown(match)
        if breakdown:
            breakdown_html = "".join(
                f"""
                <div class="points-row">
                  <span>{item['display_label']}</span>
                  <span><strong>+{item['points']} pts</strong> ({', '.join(item['reasons'])})</span>
                </div>
                """
                for item in breakdown
            )
        else:
            breakdown_html = '<div class="points-row"><span>No sweepstake players affected by this result</span></div>'

        home_team_display = render_team_label(home_team, css_class="team-label")
        away_team_display = render_team_label(away_team, css_class="team-label")

        matches_html += f"""
        <div class="card">
          <div class="match-meta">
            <span>{comp}</span>
            <span>{date_str} UTC</span>
          </div>
          <div class="match-teams">
            <span class="team home">{home_team_display}</span>
            <span class="score-badge">{score_display}</span>
            <span class="team away">{away_team_display}</span>
          </div>
          <div class="points-breakdown">
            {breakdown_html}
          </div>
        </div>
        """

    html_content = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Latest Results</title>
 <link rel="stylesheet" href="style.css">
</head>
<body>
  {render_topbar()}
  <h1>⚽ Latest Results</h1>
  {version_banner}
  {matches_html}
</body>
</html>"""

    target_path = (
        Path(output_path)
        if output_path
        else Path(__file__).with_name("latest_results.html")
    )
    target_path.write_text(html_content, encoding="utf-8")


if __name__ == "__main__":
    from rules import render_rules_page
# 1. Grab deployment timestamp or generate fallback
    timestamp = os.getenv("DEPLOYMENT_TIMESTAMP") or datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    write_api_fetch_timestamp(timestamp)

    # 2. Version management
    current_version = read_version()
    next_version = bump_version(current_version)
    write_version(next_version)

    # 3. Data processing and page generation
    matches = load_matches()
    scores = calculate_scores(matches)
    render_html(scores, version=next_version)
    render_players_page(version=next_version)
    render_latest_results_page(matches, version=next_version)
    render_rules_page()