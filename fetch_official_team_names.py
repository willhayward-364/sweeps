import argparse
import os
import sys
from pathlib import Path

import requests

API_BASE = "https://api.football-data.org/v4"
API_KEY_ENV = "FOOTBALL_DATA_API_KEY"


def get_api_key() -> str:
    api_key = os.getenv(API_KEY_ENV, "").strip()
    if not api_key:
        raise SystemExit(
            f"Missing API key. Set the environment variable {API_KEY_ENV} before running this script."
        )
    return api_key


def fetch_teams_for_competition(competition_code: str, api_key: str) -> list[dict]:
    url = f"{API_BASE}/competitions/{competition_code}/teams"
    headers = {"X-Auth-Token": api_key}

    response = requests.get(url, headers=headers, timeout=15)
    response.raise_for_status()
    payload = response.json()
    return payload.get("teams", [])


def collect_official_team_names(competition_codes: list[str], api_key: str) -> dict[str, list[dict[str, str]]]:
    official_names: dict[str, list[dict[str, str]]] = {}
    for comp_code in competition_codes:
        teams = fetch_teams_for_competition(comp_code, api_key)
        official_names[comp_code] = [
            {"id": str(team.get("id", "")), "name": team.get("name", "")}
            for team in teams
            if team.get("name")
        ]
    return official_names


def format_team_list(teams: list[dict[str, str]]) -> str:
    return "\n".join(f'{team["id"]}\t{team["name"]}' for team in teams)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Fetch official team names from Football Data API and compare them against local selections."
    )
    parser.add_argument(
        "--competitions",
        nargs="+",
        default=["PL", "ELC"],
        help="Competition codes to query (default: PL ELC).",
    )
    parser.add_argument(
        "--output-file",
        help="Write the official team names to a text file.",
    )
    parser.add_argument(
        "--no-compare",
        action="store_true",
        help="Do not compare the official team names against local selections.",
    )
    args = parser.parse_args()

    api_key = get_api_key()
    official_names = collect_official_team_names(args.competitions, api_key)

    for comp_code, teams in official_names.items():
        print(f"\n=== Official teams for {comp_code} ===")
        print(format_team_list(teams))

    if args.output_file:
        out_path = Path(args.output_file)
        out_text = []
        for comp_code, teams in official_names.items():
            out_text.append(f"# {comp_code}")
            out_text.extend(f'{team["id"]}\t{team["name"]}' for team in teams)
            out_text.append("")
        out_path.write_text("\n".join(out_text), encoding="utf-8")
        print(f"\nOfficial team names written to {out_path}")

    if not args.no_compare:
        try:
            from fetch_and_score import PLAYERS
        except ImportError:
            print("\nUnable to import local player selections for comparison.")
            return 0

        local_names = {team for teams in PLAYERS.values() for team in teams}
        api_names = {team["name"] for teams in official_names.values() for team in teams}

        missing = sorted(local_names - api_names)
        new_api = sorted(api_names - local_names)

        print("\n=== Local team names missing from API data ===")
        if missing:
            print("\n".join(missing))
        else:
            print("None")

        print("\n=== Official API team names not present in local selections ===")
        if new_api:
            print("\n".join(new_api))
        else:
            print("None")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
