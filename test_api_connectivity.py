import importlib.util
import os
from pathlib import Path
import sys
import requests

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

spec = importlib.util.spec_from_file_location("fetch_and_score", ROOT / "fetch_and_score.py")
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


def test_rule_points_are_applied():
    sample_match = {
        "homeTeam": {"name": "Arsenal FC"},
        "awayTeam": {"name": "Chelsea FC"},
        "score": {"fullTime": {"home": 3, "away": 0}},
    }

    scores = module.calculate_scores([sample_match])

    # Player E (Robin) owns Arsenal: win 3 + clean sheet 1 + goal feast 1
    assert scores["Player E"]["points"] == 5
    assert scores["Player E"]["wins"] == 1
    assert scores["Player E"]["played"] == 1
    assert scores["Player F"]["played"] == 1
    assert scores["Player A"]["played"] == 0
    assert scores["Player E"]["clean_sheets"] == 1
    assert scores["Player E"]["goal_feasts"] == 1
    # Player F (Davey) owns Chelsea: a loss earns nothing
    assert scores["Player F"]["points"] == 0
    # Nobody else is involved
    assert all(scores[p]["points"] == 0 for p in ("Player A", "Player B", "Player C", "Player D"))


def test_giant_kill_bonus():
    # Hull City (Pot 4) beat Chelsea (Pot 1)
    match = {
        "homeTeam": {"name": "Hull City AFC"},
        "awayTeam": {"name": "Chelsea FC"},
        "score": {"fullTime": {"home": 2, "away": 1}},
    }
    scores = module.calculate_scores([match])
    assert scores["Player C"]["points"] == 6  # win 3 + giant kill 3
    assert scores["Player C"]["giant_kills"] == 1


def test_stale_api_data_is_not_published(tmp_path=None):
    import tempfile

    state_file = Path(tempfile.mkdtemp()) / "published.json"
    season_matches = [{"seasonStartDate": "2026-08-15"} for _ in range(87)]

    # First publish records the count
    module.check_matches_not_stale(season_matches, state_file)
    module.record_published_matches(season_matches, state_file)

    # Same or more matches is fine
    module.check_matches_not_stale(season_matches + [{"seasonStartDate": "2026-08-15"}], state_file)

    # Fewer matches in the same season is stale
    try:
        module.check_matches_not_stale(season_matches[:80], state_file)
        assert False, "expected StaleDataError"
    except module.StaleDataError:
        pass

    # A new season resets the count
    module.check_matches_not_stale([{"seasonStartDate": "2027-08-14"}], state_file)


def test_rules_page_can_render():
    from rules import render_rules_page

    output_path = ROOT / "tmp_rules_test.html"
    render_rules_page(output_path=str(output_path))

    assert output_path.exists()
    assert "Rules" in output_path.read_text(encoding="utf-8")

    output_path.unlink(missing_ok=True)


def test_players_page_can_render_with_nicknames():
    from fetch_and_score import render_players_page

    output_path = ROOT / "tmp_players_test.html"
    render_players_page(output_path=str(output_path))

    assert output_path.exists()
    html = output_path.read_text(encoding="utf-8")
    assert "Players" in html
    assert "364" in html or "Keano" in html or "Dookie" in html
    assert "Player A" not in html  # only nicknames are shown

    output_path.unlink(missing_ok=True)


def test_latest_results_page_can_render():
    from fetch_and_score import render_latest_results_page

    output_path = ROOT / "tmp_latest_results_test.html"
    sample_matches = [
        {
            "competitionCode": "PL",
            "utcDate": "2026-07-30T20:00:00Z",
            "homeTeam": {"name": "Arsenal"},
            "awayTeam": {"name": "Chelsea"},
            "score": {"fullTime": {"home": 3, "away": 1}},
        }
    ]
    render_latest_results_page(sample_matches, output_path=str(output_path))

    assert output_path.exists()
    html = output_path.read_text(encoding="utf-8")
    assert "Latest Results" in html
    assert "Arsenal" in html
    assert "Chelsea" in html

    output_path.unlink(missing_ok=True)


def test_latest_results_page_shows_player_point_breakdown():
    from fetch_and_score import render_latest_results_page

    output_path = ROOT / "tmp_latest_results_breakdown_test.html"
    sample_matches = [
        {
            "competitionCode": "PL",
            "utcDate": "2026-07-30T20:00:00Z",
            "homeTeam": {"name": "Arsenal"},
            "awayTeam": {"name": "Chelsea"},
            "score": {"fullTime": {"home": 3, "away": 0}},
        }
    ]
    render_latest_results_page(sample_matches, output_path=str(output_path))

    html = output_path.read_text(encoding="utf-8")
    assert "Robin" in html          # Arsenal owner, shown by nickname
    assert "Player E" not in html
    assert '<span class="row-total">+5</span>' in html
    assert "Win +3" in html
    assert "Clean sheet +1" in html
    assert "Goal feast +1" in html

    output_path.unlink(missing_ok=True)


def test_latest_results_page_shows_zero_point_players_last():
    from fetch_and_score import calculate_match_breakdown, render_latest_results_page

    match = {
        "competitionCode": "PL",
        "utcDate": "2026-07-30T20:00:00Z",
        "homeTeam": {"name": "Arsenal"},
        "awayTeam": {"name": "Chelsea"},
        "score": {"fullTime": {"home": 2, "away": 1}},
    }

    breakdown = calculate_match_breakdown(match)
    by_player = {item["player"]: item for item in breakdown}
    assert by_player["Player E"]["points"] == 3          # Arsenal win
    assert by_player["Player F"]["points"] == 0          # Chelsea loss still listed
    assert by_player["Player F"]["reasons"] == ["loss"]
    assert by_player["Player E"]["teams"][0]["team"] == "Arsenal"
    assert by_player["Player E"]["teams"][0]["items"] == [("win", 3)]
    assert breakdown[-1]["player"] == "Player F"         # zero-point rows at the bottom
    assert "Player A" not in by_player                   # uninvolved players not listed

    output_path = ROOT / "tmp_latest_results_zero_points_test.html"
    render_latest_results_page([match], output_path=str(output_path))
    html = output_path.read_text(encoding="utf-8")
    assert '<span class="row-total">0</span>' in html
    assert ">Loss<" in html
    assert "+0" not in html
    output_path.unlink(missing_ok=True)


def test_breakdown_splits_points_by_team_when_player_owns_both():
    from fetch_and_score import calculate_match_breakdown

    # Davey (Player F) owns both Hull City and Chelsea
    match = {
        "homeTeam": {"name": "Hull City AFC"},
        "awayTeam": {"name": "Chelsea FC"},
        "score": {"fullTime": {"home": 2, "away": 1}},
    }
    item = {i["player"]: i for i in calculate_match_breakdown(match)}["Player F"]
    teams = {t["team"]: t for t in item["teams"]}
    assert teams["Hull City"]["items"] == [("win", 3), ("giant kill", 3)]
    assert teams["Chelsea"]["items"] == []
    assert item["points"] == 6


def test_kickoff_times_shown_in_uk_time():
    from fetch_and_score import format_kickoff_time

    # Winter (GMT = UTC) and summer (BST = UTC+1)
    assert format_kickoff_time("2026-11-07T15:00:00Z", "TBD") == "2026-11-07 15:00 GMT"
    assert format_kickoff_time("2026-08-22T14:00:00Z", "TBD") == "2026-08-22 15:00 BST"
    # Clocks went back at 01:00 UTC on 25 Oct 2026
    assert format_kickoff_time("2026-10-25T00:30:00Z", "TBD") == "2026-10-25 01:30 BST"
    assert format_kickoff_time("2026-10-25T01:30:00Z", "TBD") == "2026-10-25 01:30 GMT"
    assert format_kickoff_time("", "TBD") == "TBD"


def test_all_pages_share_layout_with_version_in_footer():
    import tempfile
    from fetch_and_score import (
        render_html, render_form_page, render_players_page,
        render_latest_results_page, render_upcoming_fixtures_page, render_pots_quadrant,
    )
    from rules import render_rules_page

    out = Path(tempfile.mkdtemp())
    match = {
        "utcDate": "2026-10-31T15:00:00Z", "status": "FINISHED",
        "homeTeam": {"name": "Arsenal FC"}, "awayTeam": {"name": "Chelsea FC"},
        "score": {"fullTime": {"home": 1, "away": 0}},
    }
    render_html(module.calculate_scores([match]), [match], output_path=out / "index.html")
    render_form_page([match], output_path=out / "form.html")
    render_players_page(output_path=out / "players.html")
    render_latest_results_page([match], output_path=out / "latest_results.html")
    render_rules_page(output_path=out / "rules.html", pots_html=render_pots_quadrant())

    for page in ["index.html", "form.html", "players.html", "latest_results.html", "rules.html"]:
        html = (out / page).read_text(encoding="utf-8")
        assert html.count('class="topbar"') == 1, page
        assert 'class="page-title' in html, page  # kept for screen readers
        assert f'href="{page}" class="nav-btn active"' in html, page
        # Version banner sits in the footer, after the page content
        assert html.index('class="site-footer"') > html.index("</main>"), page
        assert 'class="version-banner"' in html.split('class="site-footer"')[1], page
        assert "style=" not in html, page  # no one-off inline styles


def test_upcoming_fixtures_skip_finished_matches():
    import tempfile
    from fetch_and_score import render_upcoming_fixtures_page

    original = module.load_upcoming_matches
    import fetch_and_score
    fetch_and_score.load_upcoming_matches = lambda: [
        {"utcDate": "2026-10-31T12:30:00Z", "status": "FINISHED",
         "homeTeam": {"name": "Chelsea FC"}, "awayTeam": {"name": "Manchester United FC"}},
        {"utcDate": "2026-11-01T14:00:00Z", "status": "TIMED",
         "homeTeam": {"name": "Everton FC"}, "awayTeam": {"name": "Fulham FC"}},
    ]
    try:
        out = Path(tempfile.mkdtemp()) / "upcoming.html"
        render_upcoming_fixtures_page(output_path=out)
        html = out.read_text(encoding="utf-8")
        assert "Everton" in html
        assert "Chelsea" not in html
    finally:
        fetch_and_score.load_upcoming_matches = original


def test_shame_page_lists_unpaid_players():
    import tempfile
    import fetch_and_score
    from fetch_and_score import render_shame_page

    out = Path(tempfile.mkdtemp()) / "shame.html"
    render_shame_page(output_path=out)
    html = out.read_text(encoding="utf-8")
    for player in fetch_and_score.UNPAID_SUBS:
        assert fetch_and_score.get_player_display_name(player) in html
    assert 'href="shame.html" class="nav-btn active"' in html

    original = list(fetch_and_score.UNPAID_SUBS)
    fetch_and_score.UNPAID_SUBS.clear()
    try:
        render_shame_page(output_path=out)
        assert "Everyone has paid" in out.read_text(encoding="utf-8")
    finally:
        fetch_and_score.UNPAID_SUBS.extend(original)


def test_latest_results_page_renders_team_crests():
    from fetch_and_score import render_latest_results_page

    output_path = ROOT / "tmp_latest_results_crests_test.html"
    sample_matches = [
        {
            "competitionCode": "PL",
            "utcDate": "2026-07-30T20:00:00Z",
            "homeTeam": {"name": "Arsenal"},
            "awayTeam": {"name": "Chelsea"},
            "score": {"fullTime": {"home": 3, "away": 0}},
        }
    ]
    render_latest_results_page(sample_matches, output_path=str(output_path))

    html = output_path.read_text(encoding="utf-8")
    assert 'class="crest' in html
    assert 'images/crests/england_arsenal.football-logos.cc.png' in html

    output_path.unlink(missing_ok=True)


def test_version_banner_is_rendered_on_pages():
    import version
    from fetch_and_score import render_html, render_players_page
    from rules import render_rules_page

    output_paths = [
        ROOT / "tmp_rules_test.html",
        ROOT / "tmp_players_test.html",
        ROOT / "tmp_index_test.html",
    ]

    render_rules_page(output_path=str(output_paths[0]))
    render_players_page(output_path=str(output_paths[1]))
    render_html(
        {"Player A": {"points": 0, "wins": 0, "draws": 0, "clean_sheets": 0, "goal_feasts": 0, "giant_kills": 0}},
        [],
        output_path=str(output_paths[2]),
    )

    for output_path in output_paths:
        assert output_path.exists()
        html = output_path.read_text(encoding="utf-8")
        assert "Version" in html
        assert "Last deployed" in html
        assert "API last fetched" in html
        assert version.format_version(version.read_version()) in html

    for output_path in output_paths:
        output_path.unlink(missing_ok=True)


def test_api_connectivity():
    """Validates live connectivity with Football-Data API."""
    api_key = os.getenv("FOOTBALL_DATA_API_KEY", "").strip()
    headers = {"X-Auth-Token": api_key} if api_key else {}
    url = "https://api.football-data.org/v4/competitions/PL"

    print("\n📡 Testing API Connectivity...")
    if not api_key:
        print("  ⚠️ Warning: FOOTBALL_DATA_API_KEY environment variable is missing.")

    try:
        response = requests.get(url, headers=headers, timeout=10)
        assert response.status_code in (200, 429), f"API returned error status code: {response.status_code}"
        if response.status_code == 200:
            print("  ✅ Live API connection successful!")
        elif response.status_code == 429:
            print("  ⚠️ API rate limit reached (status 429). Server responded.")
    except requests.RequestException as exc:
        assert False, f"API Connection failed completely: {exc}"

import re
from pathlib import Path
from fetch_and_score import calculate_scores, load_matches


def extract_scores_from_html(filepath: Path) -> dict[str, int]:
    """Parses player IDs and their current total points from an existing index.html file."""
    if not filepath.exists():
        return {}

    content = filepath.read_text(encoding="utf-8")
    # League table format: <tr data-player="Player X"> ... <td class="col-pts">N</td>
    # (older builds used class="lt-pts")
    pattern = r'<tr data-player="(.*?)">[\s\S]*?<td class="(?:col|lt)-pts">(\d+)</td>'
    matches = re.findall(pattern, content)
    if matches:
        return {player.strip(): int(points) for player, points in matches}

    # Card format: <div class="card" data-player="Player X"> <span class="score">N pts</span>
    pattern = r'data-player="(.*?)">\s*<span class="score">(\d+)\s*pts</span>'
    matches = re.findall(pattern, content)
    if matches:
        return {player.strip(): int(points) for player, points in matches}

    # Older format: <span class="score">N pts</span> ... <div class="player-id">Player X</div>
    pattern = r'<span class="score">(\d+)\s*pts</span>[\s\S]*?<div class="player-id">(.*?)</div>'
    matches = re.findall(pattern, content)

    return {player.strip(): int(points) for points, player in matches}


def test_player_points_do_not_decrease():
    """Ensures that newly fetched/calculated scores never regress below previously released totals."""
    index_path = Path(__file__).parent / "index.html"
    previous_scores = extract_scores_from_html(index_path)

    # Skip test on initial setup if index.html doesn't exist yet
    if not previous_scores:
        print("Notice: No existing index.html found to compare scores against.")
        return

    # Calculate new scores from live match data
    matches = load_matches()
    new_scores = calculate_scores(matches)

    # Assert no player's score dropped
    for player, old_points in previous_scores.items():
        new_points = new_scores.get(player, {}).get("points", 0)
        assert new_points >= old_points, (
            f"❌ Point regression detected for {player}! "
            f"Previous released score was {old_points} pts, but new score calculated is {new_points} pts."
        )

if __name__ == "__main__":
    test_player_points_do_not_decrease()
    print("✅ Score regression check passed!")

if __name__ == "__main__":
    test_rule_points_are_applied()
    test_rules_page_can_render()
    test_players_page_can_render_with_nicknames()
    test_latest_results_page_can_render()
    test_version_banner_is_rendered_on_pages()
    test_api_connectivity()
    print("\n🎉 All tests passed successfully!")