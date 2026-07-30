# Sweeps

This project fetches finished football matches from the Football Data API, calculates sweepstake scores for a set of selected teams, and writes an HTML standings page.

## Files

- [fetch_and_score.py](fetch_and_score.py) - Python script that fetches match data, calculates scores, and generates [index.html](index.html)
- [github/workflows/update.yml](github/workflows/update.yml) - GitHub Actions workflow that runs the script automatically every Sunday at 23:00 UTC
- [index.html](index.html) - Generated standings page

## Requirements

- Python 3.10+
- The `requests` package

Install dependencies with:

```bash
pip install requests
```

## Usage

Set your API key and run the script:

```bash
export FOOTBALL_DATA_API_KEY="your-api-key"
python3 fetch_and_score.py
```

The script will generate or update [index.html](index.html).

## GitHub Actions

The workflow is configured to:

- run on a schedule every Sunday at 23:00 UTC
- allow manual triggering from the Actions tab
- use the `FOOTBALL_DATA_API_KEY` repository secret
