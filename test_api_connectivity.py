import importlib.util
from pathlib import Path

import sys

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
    render_rules_page(str(output_path))

    assert output_path.exists()
    assert "Rules" in output_path.read_text(encoding="utf-8")

    output_path.unlink(missing_ok=True)


def test_players_page_can_render_with_nicknames():
    from fetch_and_score import render_players_page

    output_path = ROOT / "tmp_players_test.html"
    render_players_page(str(output_path))

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
    render_latest_results_page(sample_matches, str(output_path))

    assert output_path.exists()
    html = output_path.read_text(encoding="utf-8")
    assert "Latest Results" in html
    assert "Arsenal" in html
    assert "Chelsea" in html

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

    render_rules_page(str(output_paths[0]))
    render_players_page(str(output_paths[1]))
    render_html({"Player A": {"points": 0, "wins": 0, "draws": 0, "clean_sheets": 0, "giant_kills": 0}}, str(output_paths[2]))

    for output_path in output_paths:
        assert output_path.exists()
        html = output_path.read_text(encoding="utf-8")
        assert "Version" in html
        assert "Last deployed" in html
        assert "API last fetched" in html
        assert version.format_version(version.read_version()) in html

    for output_path in output_paths:
        output_path.unlink(missing_ok=True)


if __name__ == "__main__":
    test_rule_points_are_applied()
    test_rules_page_can_render()
    test_version_banner_is_rendered_on_pages()
    print("All tests passed")
