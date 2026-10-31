# Sweeps

A small static website for the LSB Premier League sweepstake. A Python script
fetches finished Premier League matches from the [football-data.org](https://www.football-data.org/)
API, scores them against each player's teams, and writes plain HTML pages that
are published with GitHub Pages.

## Pages

| Page | File | What it shows |
|---|---|---|
| Standings | `index.html` | Compact league table: rank, player, team crests, W / D / CS / GF / GK and points |
| Form | `form.html` | The same table for points scored in the last 7 days |
| Players | `players.html` | Each player and their teams |
| Latest Results | `latest_results.html` | Results grouped by day (UK time), with each involved player's points per team. A button switches the point tags between short (W+3) and full words (Win +3) |
| Upcoming Fixtures | `upcoming_fixtures.html` | Matches in the next 7 days (UK time) with the players who own each team |
| Rules | `rules.html` | Scoring rules and the four pots |

Every page shows a banner with the site version, the update run number, when
the pages were built and when the API was last fetched (UTC).

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

## Files

- `fetch_and_score.py` - fetches matches, calculates scores and writes all the pages
- `rules.py` - scoring rules and the rules page
- `version.py` - site version and the banner
- `style.css` - all styling
- `images/` - team crests and player avatars
- `test_api_connectivity.py` - tests for scoring and page rendering
- `fetch_official_team_names.py` - helper to compare official API team names with local selections
- `.github/workflows/update.yml` - the scheduled update job

## How updates work

The **Automated Sweepstake Update** GitHub Actions job runs at 17:00 and 22:00 UTC
on `main`. It runs `fetch_and_score.py` with the `FOOTBALL_DATA_API_KEY` repository
secret and commits the rebuilt pages, which GitHub Pages then publishes.

It can also be run by hand from **Actions → Automated Sweepstake Update → Run workflow**
on any branch; it commits back to the branch it was run on, so test runs on other
branches never touch `main` or the live site.

Safety checks - the job stops without changing any pages if:

- the API request fails (outage, bad key, rate limit), or
- the API returns fewer finished matches than were last published for the
  season (a stale copy of the data). The count is kept in `.published_matches.json`;
  delete that file to force a publish.

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
