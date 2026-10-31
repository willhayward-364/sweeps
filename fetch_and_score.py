import json
import os
import re
from datetime import datetime, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

import requests

from rules import RULES
from version import (
    get_version_banner,
    read_version,
    write_api_fetch_timestamp,
)

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
    "Player F": "Daveylad",
}

PLAYER_AVATARS = {
    "Player A": "images/player_avatars/364_avatar.jpg",
    "Player B": "images/player_avatars/keano_avatar.jpg",
    "Player C": "images/player_avatars/dookie_avatar.jpg",
    "Player D": "images/player_avatars/Rich_avatar.jpg",
    "Player E": "images/player_avatars/Robin_avatar.jpg",
    "Player F": "images/player_avatars/Daveylad_avatar.jpg",
}

NAV_LINKS = """
      <a href="index.html" class="nav-btn">Standings</a>
      <a href="form.html" class="nav-btn">Form</a>
      <a href="players.html" class="nav-btn">Players</a>
      <a href="latest_results.html" class="nav-btn">Latest Results</a>
      <a href="upcoming_fixtures.html" class="nav-btn">Upcoming Fixtures</a>
      <a href="rules.html" class="nav-btn">Rules</a>
    """


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
    "arsenal": "england_arsenal.football-logos.cc.svg",
    "aston-villa": "england_aston-villa.football-logos.cc.svg",
    "afc-bournemouth": "england_bournemouth.football-logos.cc.svg",
    "bournemouth": "england_bournemouth.football-logos.cc.svg",
    "brentford": "england_brentford.football-logos.cc.svg",
    "brighton-hove-albion": "england_brighton.football-logos.cc.svg",
    "brighton-and-hove-albion": "england_brighton.football-logos.cc.svg",
    "burnley": "england_burnley.football-logos.cc.svg",
    "chelsea": "england_chelsea.football-logos.cc.svg",
    "coventry": "england_coventry-city.football-logos.cc.svg",
    "coventry-city": "england_coventry-city.football-logos.cc.svg",
    "crystal-palace": "england_crystal-palace.football-logos.cc.svg",
    "everton": "england_everton.football-logos.cc.svg",
    "fulham": "england_fulham.football-logos.cc.svg",
    "hull-city": "england_hull-city.football-logos.cc.svg",
    "ipswich-town": "england_ipswich.football-logos.cc.svg",
    "leeds-united": "england_leeds-united.football-logos.cc.svg",
    "liverpool": "england_liverpool.football-logos.cc.svg",
    "manchester-city": "england_manchester-city.football-logos.cc.svg",
    "manchester-united": "england_manchester-united.football-logos.cc.svg",
    "millwall": "england_millwall.football-logos.cc.svg",
    "newcastle-united": "england_newcastle.football-logos.cc.svg",
    "nottingham-forest": "england_nottingham-forest.football-logos.cc.svg",
    "sunderland": "england_sunderland.football-logos.cc.svg",
    "tottenham-hotspur": "england_tottenham.football-logos.cc.svg",
    "west-ham-united": "england_west-ham.football-logos.cc.svg",
    "wolverhampton-wanderers": "england_wolves.football-logos.cc.svg",
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


def render_team_label(team_name: str, css_class: str = "team-label") -> str:
    crest_path = get_team_crest_path(team_name)
    crest_html = (
        f'<img class="team-crest" src="{crest_path}" alt="{team_name} crest" loading="lazy">'
        if crest_path
        else ""
    )
    return f'<span class="{css_class}">{crest_html}<span class="team-name-text">{team_name}</span></span>'


def get_team_slug(team_name: str) -> str:
    """Converts a team name like 'Aston Villa' to 'aston-villa' for the SVG filename."""
    return team_name.lower().replace(" ", "-").replace("&", "and")


def render_pots_quadrant() -> str:
    """Generates the 4-quadrant HTML grid populated with teams and SVG icons."""
    pot_labels = {
        "pot1": "Pot 1 (Top Tier)",
        "pot2": "Pot 2 (Upper Tier)",
        "pot3": "Pot 3 (Mid Tier)",
        "pot4": "Pot 4 (Challengers)",
    }

    quadrant_cards = []

    for pot_key, title in pot_labels.items():
        teams = POTS.get(pot_key, [])

        team_items = []
        for team in teams:
            # 💡 Uses standard render_team_label so .team-label & .team-name-text keep their styling
            label_html = render_team_label(team)
            team_items.append(f'          <div class="pot-team-item">{label_html}</div>')

        teams_block = "\n".join(team_items)
        
        # 💡 Adding "card" ensures it inherits the site's exact card background and borders!
        card_html = f"""      <div class="card pot-card">
        <h3>{title}</h3>
        <div class="pot-team-list">
{teams_block}
        </div>
      </div>"""
        quadrant_cards.append(card_html)

    return '<div class="pots-grid">\n' + "\n".join(quadrant_cards) + "\n</div>"


def render_team_chip_list(team_names: list[str]) -> str:
    return " ".join(
        render_team_label(team_name, css_class="team-chip") for team_name in team_names
    )


# Easter egg: tap the LSB logo 10 times in quick succession and it turns into
# the Tottenham crest (for this browser session). Another 10 taps turn it back.
EASTER_EGG_TAPS = 10
EASTER_EGG_CREST = "images/crests/england_tottenham.football-logos.cc.svg"


def render_topbar() -> str:
    return f"""
  <div class="topbar">
    <div class="topbar-brand">
      <img src="images/crests/LSB_crest.PNG" alt="Sweepstake Logo" class="topbar-logo" id="site-logo">
      <strong>LSB Official Agreed Sweepstake</strong>
    </div>
    <div class="nav-links">{NAV_LINKS}</div>
  </div>
  <script>
    (function () {{
      var logo = document.getElementById("site-logo");
      if (!logo) return;
      var original = logo.getAttribute("src");
      var egg = "{EASTER_EGG_CREST}";
      var taps = 0, timer = null;
      function show(on, animate) {{
        logo.src = on ? egg : original;
        logo.alt = on ? "Tottenham Hotspur crest" : "Sweepstake Logo";
        logo.classList.toggle("logo-egg", on);
        if (animate) {{
          logo.classList.remove("logo-spin");
          void logo.offsetWidth;
          logo.classList.add("logo-spin");
        }}
      }}
      var active = false;
      try {{ active = sessionStorage.getItem("spursLogo") === "1"; }} catch (e) {{}}
      if (active) show(true, false);
      logo.addEventListener("click", function () {{
        taps += 1;
        clearTimeout(timer);
        timer = setTimeout(function () {{ taps = 0; }}, 1500);
        if (taps >= {EASTER_EGG_TAPS}) {{
          taps = 0;
          active = !active;
          show(active, true);
          try {{ sessionStorage.setItem("spursLogo", active ? "1" : "0"); }} catch (e) {{}}
        }}
      }});
    }})();
  </script>"""


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


REASON_ABBREVIATIONS = {
    "win": ("W", "Win"),
    "draw": ("D", "Draw"),
    "clean sheet": ("CS", "Clean sheet"),
    "goal feast": ("GF", "Goal feast"),
    "giant kill": ("GK", "Giant kill"),
}


def render_match_breakdown(breakdown: list[dict]) -> str:
    """Compact per-player lines under a result: avatar, name, team crest + point tags, total."""
    if not breakdown:
        return '<div class="rc-empty">No sweepstake players affected</div>'

    rows = []
    for item in breakdown:
        avatar_path = get_player_avatar_path(item["player"])
        total = item["points"]

        team_parts = []
        for entry in item["teams"]:
            crest_path = get_team_crest_path(entry["team"])
            crest_html = (
                f'<img class="rc-crest" src="{crest_path}" alt="{entry["team"]}" title="{entry["team"]}" loading="lazy">'
                if crest_path
                else f'<span class="rc-team-text">{entry["team"]}</span>'
            )
            if entry["items"]:
                tags = "".join(
                    f'<span class="rc-tag" title="{REASON_ABBREVIATIONS[reason][1]}">'
                    f'<span class="t-ab">{REASON_ABBREVIATIONS[reason][0]}+{pts}</span>'
                    f'<span class="t-full">{REASON_ABBREVIATIONS[reason][1]} +{pts}</span></span>'
                    for reason, pts in entry["items"]
                )
            else:
                tags = (
                    '<span class="rc-tag rc-tag-loss" title="Loss">'
                    '<span class="t-ab">L</span><span class="t-full">Loss</span></span>'
                )
            team_parts.append(f'<span class="rc-team-pts">{crest_html}{tags}</span>')

        rows.append(
            f"""
          <div class="rc-row">
            <span class="rc-player"><img class="rc-avatar" src="{avatar_path}" alt="" loading="lazy">{item['display_name']}</span>
            <span class="rc-detail">{''.join(team_parts)}</span>
            <span class="rc-total">{f"+{total}" if total else "0"}</span>
          </div>"""
        )
    return "".join(rows)


# ==========================================
# Weekly Card Component Generator
# ==========================================
def render_weekly_card(weekly_scores: dict) -> str:
    """Compact table of points scored in the last 7 days."""
    sorted_weekly = sorted(weekly_scores.items(), key=lambda item: item[1]["points"], reverse=True)

    rows = []
    for player, data in sorted_weekly:
        rank = 1 + sum(1 for other in weekly_scores.values() if other["points"] > data["points"])
        display_name = get_player_display_name(player)
        avatar_path = get_player_avatar_path(player)
        rows.append(
            f"""
      <tr>
        <td class="lt-rank">{rank}</td>
        <td class="lt-player"><img class="lt-avatar" src="{avatar_path}" alt="" loading="lazy"><span>{display_name}</span></td>
        <td class="lt-stat">{data['wins']}</td>
        <td class="lt-stat">{data['draws']}</td>
        <td class="lt-stat">{data['clean_sheets']}</td>
        <td class="lt-stat">{data['goal_feasts']}</td>
        <td class="lt-stat">{data['giant_kills']}</td>
        <td class="lt-pts">{data['points']}</td>
      </tr>"""
        )

    return f"""
  <div class="card league-card">
    <div class="lt-title">Points scored in the last 7 days</div>
    <table class="league-table">
      <thead>
        <tr>
          <th class="lt-rank">#</th>
          <th class="lt-player">Player</th>
          <th class="lt-stat" title="Wins">W</th>
          <th class="lt-stat" title="Draws">D</th>
          <th class="lt-stat" title="Clean sheets">CS</th>
          <th class="lt-stat" title="Goal feasts">GF</th>
          <th class="lt-stat" title="Giant kills">GK</th>
          <th class="lt-pts">Pts</th>
        </tr>
      </thead>
      <tbody>{''.join(rows)}
      </tbody>
    </table>
    <div class="lt-key">W wins · D draws · CS clean sheets · GF goal feasts · GK giant kills</div>
  </div>
"""

# ==========================================
# Standings Page (league table)
# ==========================================
def render_league_table(scores: dict) -> str:
    """Compact league table: rank, player, team crests, stats and points."""
    sorted_scores = sorted(scores.items(), key=lambda item: item[1]["points"], reverse=True)

    rows = []
    for player, data in sorted_scores:
        # Players level on points share a rank (e.g. 2, 2, 4)
        rank = 1 + sum(1 for other in scores.values() if other["points"] > data["points"])
        display_name = get_player_display_name(player)
        avatar_path = get_player_avatar_path(player)

        crests = []
        for team in PLAYERS[player]:
            crest_path = get_team_crest_path(team)
            if crest_path:
                crests.append(
                    f'<img class="lt-crest" src="{crest_path}" alt="{team}" title="{team}" loading="lazy">'
                )

        rows.append(
            f"""
      <tr data-player="{player}">
        <td class="lt-rank">{rank}</td>
        <td class="lt-player"><img class="lt-avatar" src="{avatar_path}" alt="" loading="lazy"><span>{display_name}</span></td>
        <td class="lt-teams">{''.join(crests)}</td>
        <td class="lt-stat">{data['wins']}</td>
        <td class="lt-stat">{data['draws']}</td>
        <td class="lt-stat">{data['clean_sheets']}</td>
        <td class="lt-stat">{data['goal_feasts']}</td>
        <td class="lt-stat">{data['giant_kills']}</td>
        <td class="lt-pts">{data['points']}</td>
      </tr>"""
        )

    return f"""
  <div class="card league-card">
    <table class="league-table">
      <thead>
        <tr>
          <th class="lt-rank">#</th>
          <th class="lt-player">Player</th>
          <th class="lt-teams">Teams</th>
          <th class="lt-stat" title="Wins">W</th>
          <th class="lt-stat" title="Draws">D</th>
          <th class="lt-stat" title="Clean sheets">CS</th>
          <th class="lt-stat" title="Goal feasts">GF</th>
          <th class="lt-stat" title="Giant kills">GK</th>
          <th class="lt-pts">Pts</th>
        </tr>
      </thead>
      <tbody>{''.join(rows)}
      </tbody>
    </table>
    <div class="lt-key">W wins · D draws · CS clean sheets · GF goal feasts · GK giant kills</div>
  </div>"""


def render_html(scores: dict, matches: list[dict] | None = None, version: str | None = None, output_path: str | None = None):
    """Standings page (index.html): the full league table."""
    version_banner = get_version_banner(version=version)

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
  {render_league_table(scores)}
</body>
</html>"""

    target_path = Path(output_path) if output_path else Path(__file__).with_name("index.html")
    target_path.write_text(html_content, encoding="utf-8")


# ==========================================
# Form Page (last 7 days)
# ==========================================
def render_form_page(matches: list[dict], version: str | None = None, output_path: str | None = None):
    """Form page (form.html): points scored in the last 7 days."""
    version_banner = get_version_banner(version=version)
    weekly_card_html = render_weekly_card(calculate_weekly_scores(matches))

    html_content = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Form Guide</title>
  <link rel="stylesheet" href="style.css">
</head>
<body>
  {render_topbar()}
  <h1>⚡ Form Guide</h1>
  {version_banner}
  {weekly_card_html}
</body>
</html>"""

    target_path = Path(output_path) if output_path else Path(__file__).with_name("form.html")
    target_path.write_text(html_content, encoding="utf-8")

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

def get_players_for_team(team_name: str) -> list[dict]:
    """Finds all players who have selected a given team."""
    matched = []
    for player_id, teams in PLAYERS.items():
        if team_is_in_player_selection(team_name, teams):
            matched.append({
                "player_id": player_id,
                "display_name": get_player_display_name(player_id),
                "avatar_path": get_player_avatar_path(player_id),
            })
    return matched


def render_team_player_badges(team_name: str) -> str:
    """Renders player avatar and nickname badges underneath the team label."""
    players = get_players_for_team(team_name)
    if not players:
        return ""

    badges_html = ""
    for p in players:
        badges_html += f"""
        <div class="owner-badge" style="display: inline-flex; align-items: center; gap: 6px; margin-top: 6px;">
            <img class="player-avatar" src="{p['avatar_path']}" alt="{p['display_name']}" width="20" height="20" style="border-radius: 50%; object-fit: cover;" loading="lazy">
            <span style="font-size: 0.85rem; font-weight: 600; color: #ffb703;">{p['display_name']}</span>
        </div>
        """
    return f'<div class="team-owners" style="display: flex; flex-wrap: wrap; gap: 8px;">{badges_html}</div>'

def render_upcoming_fixtures_page(version: str | None = None, output_path: str | None = None):
    version_banner = get_version_banner(version=version)
    matches = load_upcoming_matches()

    sorted_matches = sorted(
        matches, key=lambda match: match.get("utcDate", "")
    )[:25]

    matches_html = ""
    for match in sorted_matches:
        comp = match.get("competitionCode", "Unknown")
        raw_date = match.get("utcDate", "")
        date_str = format_kickoff_time(raw_date, "TBD")

        home_team = (
            match.get("homeTeam", {}).get("shortName")
            or match.get("homeTeam", {}).get("name", "Unknown")
        )
        away_team = (
            match.get("awayTeam", {}).get("shortName")
            or match.get("awayTeam", {}).get("name", "Unknown")
        )

        home_team_display = render_team_label(home_team, css_class="team-label")
        away_team_display = render_team_label(away_team, css_class="team-label")

        home_owners_html = render_team_player_badges(home_team)
        away_owners_html = render_team_player_badges(away_team)

        matches_html += f"""
        <div class="card">
          <div class="match-meta">
            <span>{comp}</span>
            <span>{date_str}</span>
          </div>
          <div class="match-teams" style="display: flex; justify-content: space-between; align-items: flex-start; gap: 16px;">
            <div class="team-column home" style="flex: 1;">
              {home_team_display}
              {home_owners_html}
            </div>
            <span class="score-badge" style="align-self: center;">VS</span>
            <div class="team-column away" style="flex: 1; text-align: right;">
              {away_team_display}
              <div style="display: flex; justify-content: flex-end;">
                {away_owners_html}
              </div>
            </div>
          </div>
        </div>
        """

    if not matches_html:
        matches_html = '<div class="card"><p>No upcoming fixtures scheduled at this time.</p></div>'

    html_content = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Upcoming Fixtures in the next 7 days</title>
  <link rel="stylesheet" href="style.css">
</head>
<body>
  {render_topbar()}
  <h1>📅 Upcoming Fixtures in the next 7 days</h1>
  {version_banner}
  {matches_html}
</body>
</html>"""

    target_path = Path(output_path) if output_path else Path(__file__).with_name("upcoming_fixtures.html")
    target_path.write_text(html_content, encoding="utf-8")

def render_players_page(version: str | None = None, output_path: str | None = None):
    version_banner = get_version_banner(version=version)
    cards_html = ""
    for player, teams in PLAYERS.items():
        display_name = get_player_display_name(player)
        teams_str = ", ".join(teams)

        # 1. Resolve avatar path & build tag
        avatar_path = get_player_avatar_path(player)
        avatar_html = f'<img class="player-avatar" src="{avatar_path}" alt="{display_name} avatar" width="150" height="150" loading="lazy">'

        cards_html += f"""
        <div class="card">
            <div class="player-name-wrapper">
                {avatar_html}
                <span class="player-name">{display_name}</span>
            </div>
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


def _uk_kickoff(utc_date: str) -> datetime | None:
    try:
        return datetime.fromisoformat(utc_date.replace("Z", "+00:00")).astimezone(UK_TIMEZONE)
    except (AttributeError, ValueError):
        return None


def render_latest_results_page(matches: list[dict], version: str | None = None, output_path: str | None = None):
    version_banner = get_version_banner(version=version)

    sorted_matches = sorted(
        matches, key=lambda match: match.get("utcDate", ""), reverse=True
    )
    recent_matches = sorted_matches[:380]  # Limit to the most recent 380 matches

    matches_html = ""
    current_day = None
    for match in recent_matches:
        kickoff = _uk_kickoff(match.get("utcDate", ""))

        # Day heading whenever the (UK) date changes
        day_label = kickoff.strftime("%A %-d %B") if kickoff else "Date unknown"
        if day_label != current_day:
            matches_html += f'\n  <h2 class="day-heading">{day_label}</h2>'
            current_day = day_label
        time_label = kickoff.strftime("%H:%M %Z") if kickoff else ""

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
            f"{home_score}-{away_score}"
            if home_score is not None and away_score is not None
            else "TBD"
        )

        def crest(team_name: str) -> str:
            path = get_team_crest_path(team_name)
            return f'<img class="team-crest" src="{path}" alt="{team_name} crest" loading="lazy">' if path else ""

        breakdown_html = render_match_breakdown(calculate_match_breakdown(match))

        matches_html += f"""
  <div class="card result-card">
    <div class="rc-score">
      <span class="rc-team rc-home"><span class="rc-name">{home_team}</span>{crest(home_team)}</span>
      <span class="rc-mid"><span class="rc-badge">{score_display}</span><span class="rc-time">{time_label}</span></span>
      <span class="rc-team rc-away">{crest(away_team)}<span class="rc-name">{away_team}</span></span>
    </div>
    <div class="rc-breakdown">{breakdown_html}
    </div>
  </div>"""

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
  <div class="rc-toolbar">
    <span class="lt-key rc-key">W win · D draw · L loss · CS clean sheet · GF goal feast · GK giant kill</span>
    <button type="button" id="toggle-words" class="nav-btn rc-toggle" aria-pressed="false">Show full words</button>
  </div>
  {matches_html}
  <script>
    // Switch the point tags between short (W+3) and full words (Win +3); remembered on this device.
    (function () {{
      var button = document.getElementById("toggle-words");
      function apply(full) {{
        document.body.classList.toggle("full-words", full);
        button.textContent = full ? "Show short" : "Show full words";
        button.setAttribute("aria-pressed", full ? "true" : "false");
      }}
      var saved = false;
      try {{ saved = localStorage.getItem("fullWords") === "1"; }} catch (e) {{}}
      apply(saved);
      button.addEventListener("click", function () {{
        var full = !document.body.classList.contains("full-words");
        apply(full);
        try {{ localStorage.setItem("fullWords", full ? "1" : "0"); }} catch (e) {{}}
      }});
    }})();
  </script>
</body>
</html>"""

    target_path = (
        Path(output_path)
        if output_path
        else Path(__file__).with_name("latest_results.html")
    )
    target_path.write_text(html_content, encoding="utf-8")


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
    render_rules_page(pots_html=render_pots_quadrant(), topbar_html=render_topbar())
    record_published_matches(matches)