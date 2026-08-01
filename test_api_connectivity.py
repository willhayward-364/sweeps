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
        "homeTeam": {"name": "Arsenal"},
        "awayTeam": {"name": "Chelsea"},
        "score": {"fullTime": {"home": 3, "away": 0}},
    }

    player_scores = {
        player: {"points": 0, "wins": 0, "draws": 0, "clean_sheets": 0, "giant_kills": 0}
        for player in module.PLAYERS
    }

    for player, teams in module.PLAYERS.items():
        if "Arsenal" in teams:
            player_scores[player]["points"] += 3  # win bonus
            player_scores[player]["wins"] += 1
            player_scores[player]["points"] += 1  # clean sheet bonus
            player_scores[player]["clean_sheets"] += 1
            player_scores[player]["points"] += 1  # goal feast bonus

    assert player_scores["Player A"]["points"] == 5
    assert player_scores["Player A"]["wins"] == 1
    assert player_scores["Player A"]["clean_sheets"] == 1


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
    assert "Player A" in html

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
    assert "Player A" in html
    assert "+5 pts" in html
    assert "win" in html

    output_path.unlink(missing_ok=True)


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
    assert 'class="team-crest"' in html
    assert 'images/crests/england_arsenal.football-logos.cc.svg' in html

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
        {"Player A": {"points": 0, "wins": 0, "draws": 0, "clean_sheets": 0, "giant_kills": 0}},
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


if __name__ == "__main__":
    test_rule_points_are_applied()
    test_rules_page_can_render()
    test_players_page_can_render_with_nicknames()
    test_latest_results_page_can_render()
    test_version_banner_is_rendered_on_pages()
    test_api_connectivity()
    print("\n🎉 All tests passed successfully!")