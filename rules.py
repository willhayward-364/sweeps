from pathlib import Path

from layout import render_page

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


def render_rules_page(output_path: str | None = None, pots_html: str = "", version: str | None = None) -> None:
    rule_rows = "".join(
        f"""
    <div class="rule-row">
      <div class="rule-text">
        <div class="rule-title">{rule["title"]}</div>
        <div class="rule-desc">{rule["description"]}</div>
      </div>
      <span class="pill">+{rule["points"]}</span>
    </div>"""
        for rule in RULES
    )

    body = f"""
  <div class="card">
    <p class="card-text">Points are awarded to each player based on the outcomes of the matches involving their selected teams.</p>
  </div>

  <h2 class="section-heading">How the teams were drawn</h2>
  <div class="card quote-card">
    <div class="card-heading">💡 Christopher F Keane</div>
    <p class="card-text">"I literally don’t know how many times I have to step in and up here…"</p>
    <ul class="card-list">
      <li>20 PL Teams ranked in order of odds</li>
      <li>Top 18 split into 3 pots</li>
      <li>3 teams each drawn by a fucking wheel which will probably give me Italy again</li>
      <li>bottom 2 split 3 and 3</li>
    </ul>
  </div>

  <h2 class="section-heading">Scoring</h2>
  <div class="card rules-card">{rule_rows}
  </div>
"""
    if pots_html:
        body += f"""
  <h2 class="section-heading">Pots</h2>
{pots_html}
"""

    render_page(
        page="rules.html",
        title="Rules · LSB Sweepstake",
        heading="📜 Rules",
        body=body,
        output_path=output_path or Path(__file__).with_name("rules.html"),
        version=version,
    )
