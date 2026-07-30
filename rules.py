from pathlib import Path

from version import get_version_banner

RULES = [
    {
        "ref": "R1",
        "title": "Win bonus",
        "description": "A selected team that wins a match earns 3 points for the player.",
        "points": 3,
        "applies_to": "match_result",
    },
    {
        "ref": "R2",
        "title": "Draw bonus",
        "description": "A selected team that draws a match earns 1 point for the player.",
        "points": 1,
        "applies_to": "match_result",
    },
    {
        "ref": "R3",
        "title": "Clean sheet bonus",
        "description": "If a selected team keeps a clean sheet, the player earns 1 extra point.",
        "points": 1,
        "applies_to": "clean_sheet",
    },
    {
        "ref": "R4",
        "title": "Goal feast bonus",
        "description": "If a selected team scores 3 or more goals, the player earns 1 extra point.",
        "points": 1,
        "applies_to": "goal_feast",
    },
    {
        "ref": "R5",
        "title": "Giant-killer bonus",
        "description": "If a selected team from Pot 3 or Pot 4 beats a Pot 1 team, the player earns 3 extra points.",
        "points": 3,
        "applies_to": "giant_killer",
    },
]


def render_rules_page(output_path: str | None = None) -> None:
    html_lines = [
        "<!DOCTYPE html>",
        "<html lang=\"en\">",
        "<head>",
        "  <meta charset=\"UTF-8\">",
        "  <meta name=\"viewport\" content=\"width=device-width, initial-scale=1.0\">",
        "  <title>Sweepstake Rules</title>",
        "  <style>",
        "    body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; background: #0b132b; color: #ffffff; padding: 20px; max-width: 700px; margin: 0 auto; }",
        "    .topbar { display: flex; justify-content: space-between; align-items: center; background: #1c2541; border: 1px solid #3a506b; border-radius: 999px; padding: 10px 16px; margin-bottom: 20px; }",
        "    .topbar a { color: #48cae4; text-decoration: none; font-weight: 600; }",
        "    .rule-card { background: #1c2541; border-radius: 12px; padding: 15px; margin-bottom: 12px; border: 1px solid #3a506b; }",
        "    .rule-ref { color: #48cae4; font-weight: bold; margin-bottom: 6px; }",
        "    .rule-title { color: #ffb703; font-weight: bold; margin-bottom: 6px; }",
        "    .rule-desc { color: #cbd5e1; }",
        "  </style>",
        "</head>",
        "<body>",
        "  <div class=\"topbar\">",
        "    <strong>🏆 Sweepstake</strong>",
        "    <div>",
        "      <a href=\"index.html\">Standings</a>",
        "      <a href=\"players.html\">Players</a>",
        "      <a href=\"latest_results.html\">Latest Results</a>",
        "      <a href=\"rules.html\">Rules</a>",
        "    </div>",
        "  </div>",
        "  <h1>Rules</h1>",
        f"  {get_version_banner()}",
        "  <p>Points are awarded to each player based on the outcomes of the matches involving their selected teams.</p>",
    ]

    for rule in RULES:
        html_lines.extend([
            "  <div class=\"rule-card\">",
            f"    <div class=\"rule-ref\">{rule['ref']}</div>",
            f"    <div class=\"rule-title\">{rule['title']} ({rule['points']} point{'s' if rule['points'] != 1 else ''})</div>",
            f"    <div class=\"rule-desc\">{rule['description']}</div>",
            "  </div>",
        ])

    html_lines.extend(["</body>", "</html>"])

    target_path = Path(output_path) if output_path else Path(__file__).with_name("rules.html")
    target_path.write_text("\n".join(html_lines) + "\n", encoding="utf-8")
