from __future__ import annotations

import os
from datetime import datetime, timezone
from pathlib import Path

VERSION_FILE = Path(__file__).resolve().parent / ".version"
API_FETCH_FILE = Path(__file__).resolve().parent / ".api_fetch_timestamp"
DEFAULT_VERSION = "v0.01"


def read_version() -> str:
    # 1. Check if running inside GitHub Actions (uses build number automatically, e.g., v0.12)
    run_number = os.getenv("GITHUB_RUN_NUMBER")
    if run_number:
        return f"v0.{int(run_number):02d}"

    # 2. Fallback for local testing: read from .version file
    if VERSION_FILE.exists():
        version = VERSION_FILE.read_text(encoding="utf-8").strip()
        if version:
            return version
            
    return DEFAULT_VERSION


def write_version(version: str) -> None:
    VERSION_FILE.write_text(version, encoding="utf-8")


def bump_version(current_version: str | None = None) -> str:
    version = current_version or read_version()
    try:
        major, minor = version.lstrip("v").split(".")
        minor_value = int(minor) + 1
        return f"v{major}.{minor_value:02d}"
    except ValueError:
        return DEFAULT_VERSION


def format_version(version: str) -> str:
    return version if version.startswith("v") else f"v{version}"


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
    
    return (
        f'<div class="version-banner">'
        f'Version <strong>{current_version}</strong> &nbsp;•&nbsp; Last deployed <strong>{deployed}</strong> '
        f'&nbsp;•&nbsp; API last fetched <strong>{api_fetch}</strong>'
        f'</div>'
    )