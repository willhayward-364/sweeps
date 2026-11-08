# Sweeps

A small static website for the LSB Premier League sweepstake. A Python script
fetches finished Premier League matches from the [football-data.org](https://www.football-data.org/)
API, scores them against each player's teams, and writes plain HTML pages that
are published with GitHub Pages.

## Pages

| Menu | File | What it shows |
|---|---|---|
| Standings | `index.html` | League table (rank, player, team crests, P / W / D / CS / GF / GK, points). Tap a player to see their points by team. Below it, a **points race** chart (tap any day for everyone's total) and a season progress bar |
| Form | `form.html` | The same table for points scored in the last 7 days |
| Players | `players.html` | Each player's four teams and their pots |
| Results | `latest_results.html` | Results grouped by day (UK time), with each involved player's points per team (Win +3, Clean sheet +1, Loss…) |
| Fixtures | `upcoming_fixtures.html` | Matches in the next 7 days (UK time) with each team's owners underneath |
| Prizes | `prizes.html` | The agreed prizes (£120) and who is leading each; Golden Gloves and Golden Boot expand to a full ranking |
| Rules | `rules.html` | Scoring rules, how the teams were drawn, and the four pots |
| Hall of Shame | `shame.html` | Players who haven't paid their subs |

Every page shares one header/menu (the current page is highlighted) and a footer
with the site version, the update run number, when the pages were built and when the
API was last fetched (UTC). Match times are shown in UK time (GMT/BST).

Hidden extra: tap the LSB logo 10 times quickly.

## Scoring

Defined in `rules.py`. For each match, every player who owns one of the teams gets:

| Rule | Points |
|---|---|
| Win | 3 |
| Draw | 1 |
| Clean sheet | +1 |
| Goal feast (3+ goals) | +1 |
| Giant kill (a Pot 3/4 team beats a Pot 1 team) | +3 |

Players, their nicknames, avatars and the pots are set at the top of `fetch_and_score.py`.

## Things to update by hand

All in `fetch_and_score.py` unless noted:

- `UNPAID_SUBS` - who appears on the Hall of Shame (remove players once they pay).
- `PLAYERS`, `PLAYER_NICKNAMES`, `PLAYER_AVATARS`, `POTS` - for a new season's draw.
- `XMAS_CUTOFF` - the Christmas prize cut-off (currently the end of 25 Dec 2026).
- The Standings page title "Standings 2026/27" in `render_html`.
- Prize amounts and names in `render_prizes_page`.
- `SITE_VERSION` in `version.py` - see Versioning below.

## Files

- `fetch_and_score.py` - fetches matches, calculates scores and writes all the pages
- `layout.py` - the shared page layout: header, menu, footer and the logo Easter egg
- `rules.py` - scoring rules and the rules page
- `version.py` - site version and the footer banner
- `style.css` - all styling (shared sizes and colours at the top)
- `images/` - team crests (small PNGs, with the original SVGs kept alongside) and player photos
- `test_api_connectivity.py` - tests for scoring and page rendering
- `fetch_official_team_names.py` - helper to compare official API team names with local selections
- `.github/workflows/update.yml` - the scheduled update job

## How updates work

The **Automated Sweepstake Update** GitHub Actions job runs on `main` shortly after
matches usually finish: Saturdays and Sundays at 14:35, 17:05 and 19:35 UTC, and every
day at 22:35 UTC. It runs `fetch_and_score.py` with the `FOOTBALL_DATA_API_KEY` repository
secret and commits the rebuilt pages, which GitHub Pages then publishes.

It can also be run by hand from **Actions → Automated Sweepstake Update → Run workflow**
on any branch; it commits back to the branch it was run on, so test runs on other
branches never touch `main` or the live site.

Only one update runs at a time per branch, and each run picks up any newer commits
before saving, so overlapping runs don't clash.

Safety checks - nothing is published when:

- the API request fails (outage, bad key, rate limit) - the run fails (red), or
- the API returns fewer finished matches than were last published for the season
  (a stale copy of the data) - the run succeeds with a yellow "skipped" warning and
  the next run tries again. The count is kept in `.published_matches.json`; delete
  that file to force a publish.

Note: GitHub often starts scheduled runs late (by up to a few hours) when busy.

## Versioning

The site version is set by hand in `version.py` (`SITE_VERSION`) and bumped once
per release to the live site (a merge to `main`), not for every change while work
is in progress:

- `v2.0.1` - a release of small tweaks and fixes
- `v2.1.0` - a release with noticeable new features
- `v3.0.0` - big overhauls

The run number in the banner is GitHub's count of update runs, which goes up with
every results refresh.

## Running locally

```bash
pip install requests
export FOOTBALL_DATA_API_KEY="your-api-key"
python3 fetch_and_score.py
```

Set `USE_MOCK_DATA = True` in `fetch_and_score.py` to build the pages from built-in
sample matches without calling the API.

## Tests

```bash
python3 -m pytest test_api_connectivity.py
```

`test_api_connectivity` and `test_player_points_do_not_decrease` need network access
and an API key; the rest run offline.
