from __future__ import annotations

import os
from datetime import datetime, timezone
from pathlib import Path

API_FETCH_FILE = Path(__file__).resolve().parent / ".api_fetch_timestamp"

# Site version, bumped by hand when the site's code changes:
#   patch (v2.0.1) for small tweaks and fixes,
#   minor (v2.1.0) for noticeable new features,
#   major (v3.0.0) for big overhauls.
SITE_VERSION = "v2.3.1"


def read_version() -> str:
    return SITE_VERSION


def format_version(version: str) -> str:
    return version if version.startswith("v") else f"v{version}"


def get_run_number() -> str | None:
    """GitHub Actions run number of the update that built the pages, if any."""
    return os.getenv("GITHUB_RUN_NUMBER") or None


def get_deployment_timestamp() -> str:
    env_value = os.getenv("DEPLOYMENT_TIMESTAMP")
    if env_value:
        return env_value
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")


def read_api_fetch_timestamp() -> str:
    if API_FETCH_FILE.exists():
        timestamp = API_FETCH_FILE.read_text(encoding="utf-8").strip()
        if timestamp:
            return timestamp
    return "Not available"


def write_api_fetch_timestamp(timestamp: str) -> None:
    API_FETCH_FILE.write_text(timestamp, encoding="utf-8")


def get_version_banner(version: str | None = None, deployed_at: str | None = None) -> str:
    current_version = format_version(version or read_version())
    deployed = deployed_at or get_deployment_timestamp()
    api_fetch = read_api_fetch_timestamp()
    run_number = get_run_number()
    run_html = f' &nbsp;•&nbsp; Run <strong>#{run_number}</strong>' if run_number else ""

    return (
        f'<div class="version-banner">'
        f'Version <strong>{current_version}</strong>{run_html} '
        f'&nbsp;•&nbsp; Last deployed <strong>{deployed}</strong> '
        f'&nbsp;•&nbsp; API last fetched <strong>{api_fetch}</strong>'
        f'</div>'
    )
