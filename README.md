# Sweeps

This project fetches finished football matches from the Football Data API, calculates sweepstake scores for a set of selected teams, and publishes a simple HTML site with standings, player selections, and rules.

## What it does

- Fetches live match results from the Football Data API
- Applies the sweepstake scoring rules to each player selection
- Generates four pages:
  - standings page at [index.html](index.html)
  - players page at [players.html](players.html)
  - latest results page at [latest_results.html](latest_results.html)
  - rules page at [rules.html](rules.html)
- Shows a version banner on every page with:
  - current deployment version
  - last deployment timestamp
  - last successful API fetch timestamp
- Supports mock match data for scoring tests
- Includes a helper script to verify official team names from the API

## Files

- [fetch_and_score.py](fetch_and_score.py) - Main generator script that fetches data, calculates scores, and renders HTML pages
- [rules.py](rules.py) - Defines the scoring rules and renders the rules page
- [version.py](version.py) - Tracks the current version, deployment timestamp, and API fetch timestamp
- [fetch_official_team_names.py](fetch_official_team_names.py) - Helper script to fetch official team names and compare them against local selections
- [test_api_connectivity.py](test_api_connectivity.py) - Regression tests for scoring and rendering
- [github/workflows/update.yml](github/workflows/update.yml) - GitHub Actions workflow that regenerates pages and commits updated outputs

## Requirements

- Python 3.10+
- The `requests` package

Install dependencies with:

```bash
pip install requests
```

## Usage

Set your API key and run the main generator:

```bash
export FOOTBALL_DATA_API_KEY="your-api-key"
python3 fetch_and_score.py
```

This will regenerate:

- [index.html](index.html)
- [players.html](players.html)
- [rules.html](rules.html)

It also updates the version tracking files:

- [.version](.version)
- [.api_fetch_timestamp](.api_fetch_timestamp)

## Helper script

To verify official team names from the API and identify mismatches with local selections:

```bash
export FOOTBALL_DATA_API_KEY="your-api-key"
python3 fetch_official_team_names.py
```

By default this queries the Premier League (`PL`) and EFL Championship (`ELC`). Use `--competitions` to customize the competitions.

Example:

```bash
python3 fetch_official_team_names.py --competitions PL ELC
```

To save the official names to a file:

```bash
python3 fetch_official_team_names.py --output-file official_names.txt
```

## Testing

Run the test script with:

```bash
python3 test_api_connectivity.py
```

## GitHub Actions

The workflow is configured to:

- run on a schedule at 17:00 and 22:00 UTC
- allow manual triggering from the Actions tab
- use the `FOOTBALL_DATA_API_KEY` repository secret
- increment the deployment version and commit generated output on success
