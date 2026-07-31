import os
import random
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


def render_topbar() -> str:
    return f"""
  <div class="topbar">
    <strong>🏆 Sweepstake</strong>
    <div class="nav-links">{NAV_LINKS}</div>
  </div>
"""


def get_player_display_name(player_id: str) -> str:
    return PLAYER_NICKNAMES.get(player_id, player_id)


def render_topbar() -> str:
    return f"""
  <div class="topbar">
    <strong>🏆 Sweepstake</strong>
    <div>{NAV_LINKS}</div>
  </div>
"""


def fetch_matches(comp_code: str):
    url = f"https://api.football-data.org/v4/competitions/{comp_code}/matches?status=FINISHED&season=2025"

    try:
        response = requests.get(url, headers=HEADERS, timeout=10)
        response.raise_for_status()
        timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
        write_api_fetch_timestamp(timestamp)

        matches = response.json().get("matches", [])
        for match in matches:
            match["competitionCode"] = comp_code
        return matches
    except requests.RequestException as exc:
        print(f"Error fetching {comp_code}: {exc}")
        return []


def build_mock_matches():
    raise NotImplementedError


def load_matches() -> list[dict]:
    if USE_MOCK_DATA:
        return build_mock_matches()

    return fetch_matches("PL") + fetch_matches("ELC")


def team_is_in_player_selection(team_name: str, selected_teams: list[str]) -> bool:
    return any(team_name == selected_team for selected_team in selected_teams)


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


def render_html(scores, output_path: str | None = None):
    version_banner = get_version_banner()
    sorted_scores = sorted(scores.items(), key=lambda item: item[1]["points"], reverse=True)

    cards_html = ""
    for rank, (player, data) in enumerate(sorted_scores, 1):
        teams_str = ", ".join(PLAYERS[player])
        display_name = get_player_display_name(player)
        cards_html += f"""
        <div class="card">
            <span class="score">{data['points']} pts</span>
            <div class="player-name">#{rank} {display_name}</div>
            <div class="player-id">{player}</div>
            <div class="teams">{teams_str}</div>
            <div class="stats">Wins: {data['wins']} | Draws: {data['draws']} | Clean Sheets: {data['clean_sheets']}</div>
        </div>
        """

    html_content = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>2026/27 Premier League Sweepstake</title>
  <style>
    body {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; background: #0b132b; color: #ffffff; padding: 20px; max-width: 600px; margin: 0 auto; }}
    h1 {{ text-align: center; color: #48cae4; font-size: 1.5rem; margin-bottom: 20px; }}
    .topbar {{ display: flex; justify-content: space-between; align-items: center; background: #1c2541; border: 1px solid #3a506b; border-radius: 999px; padding: 10px 16px; margin-bottom: 20px; }}
    .topbar a {{ color: #48cae4; text-decoration: none; font-weight: 600; }}
    .card {{ background: #1c2541; border-radius: 12px; padding: 15px; margin-bottom: 15px; border: 1px solid #3a506b; }}
    .player-name {{ font-weight: bold; font-size: 1.2rem; color: #ffb703; }}
    .player-id {{ font-size: 0.8rem; color: #a0aec0; margin-top: 2px; }}
    .teams {{ font-size: 0.9rem; color: #cbd5e1; margin-top: 6px; }}
    .stats {{ font-size: 0.8rem; color: #a0aec0; margin-top: 8px; border-top: 1px solid #2d3748; padding-top: 6px; }}
    .score {{ font-size: 1.4rem; font-weight: bold; float: right; color: #48cae4; }}
  </style>
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


def render_players_page(output_path: str | None = None):
    version_banner = get_version_banner()
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
  <style>
    body {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; background: #0b132b; color: #ffffff; padding: 20px; max-width: 600px; margin: 0 auto; }}
    h1 {{ text-align: center; color: #48cae4; font-size: 1.5rem; margin-bottom: 20px; }}
    .topbar {{ display: flex; justify-content: space-between; align-items: center; background: #1c2541; border: 1px solid #3a506b; border-radius: 999px; padding: 10px 16px; margin-bottom: 20px; }}
    .topbar a {{ color: #48cae4; text-decoration: none; font-weight: 600; }}
    .card {{ background: #1c2541; border-radius: 12px; padding: 15px; margin-bottom: 15px; border: 1px solid #3a506b; }}
    .player-name {{ font-weight: bold; font-size: 1.2rem; color: #ffb703; }}
    .player-id {{ font-size: 0.8rem; color: #a0aec0; margin-top: 2px; }}
    .teams {{ font-size: 0.9rem; color: #cbd5e1; margin-top: 6px; }}
  </style>
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


def render_latest_results_page(matches: list[dict], output_path: str | None = None):
    version_banner = get_version_banner()

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

        matches_html += f"""
        <div class="card">
          <div class="match-meta">
            <span>{comp}</span>
            <span>{date_str} UTC</span>
          </div>
          <div class="match-teams">
            <span class="team home">{home_team}</span>
            <span class="score-badge">{score_display}</span>
            <span class="team away">{away_team}</span>
          </div>
        </div>
        """

    html_content = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Latest Results</title>
  <style>
    body {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; background: #0b132b; color: #ffffff; padding: 20px; max-width: 600px; margin: 0 auto; }}
    h1 {{ text-align: center; color: #48cae4; font-size: 1.5rem; margin-bottom: 20px; }}
    .topbar {{ display: flex; justify-content: space-between; align-items: center; background: #1c2541; border: 1px solid #3a506b; border-radius: 999px; padding: 10px 16px; margin-bottom: 20px; }}
    .topbar a {{ color: #48cae4; text-decoration: none; font-weight: 600; font-size: 0.9rem; margin-left: 6px; }}
    .card {{ background: #1c2541; border-radius: 12px; padding: 15px; margin-bottom: 15px; border: 1px solid #3a506b; }}
    .match-meta {{ font-size: 0.8rem; color: #a0aec0; display: flex; justify-content: space-between; margin-bottom: 10px; }}
    .match-teams {{ display: flex; justify-content: space-between; align-items: center; font-size: 0.95rem; font-weight: bold; }}
    .team {{ width: 38%; color: #ffffff; }}
    .team.home {{ text-align: right; }}
    .team.away {{ text-align: left; }}
    .score-badge {{ color: #ffb703; font-size: 1.1rem; font-weight: 800; background: #0f1c33; padding: 4px 10px; border-radius: 6px; border: 1px solid #3a506b; text-align: center; white-space: nowrap; }}
  </style>
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

    current_version = read_version()
    next_version = bump_version(current_version)
    write_version(next_version)

    matches = load_matches()
    scores = calculate_scores(matches)
    render_html(scores)
    render_players_page()
    render_latest_results_page(matches)
    render_rules_page()