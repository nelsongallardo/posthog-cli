"""Configuration and authentication management."""

from __future__ import annotations

import json
import os
from pathlib import Path

import typer

CONFIG_DIR = Path(typer.get_app_dir("posthog-cli"))
CONFIG_FILE = CONFIG_DIR / "config.json"

# Environment variable names
ENV_API_KEY = "POSTHOG_API_KEY"
ENV_HOST = "POSTHOG_HOST"
ENV_PROJECT_ID = "POSTHOG_PROJECT_ID"

DEFAULT_HOST = "https://us.posthog.com"


def _ensure_config_dir() -> None:
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)


def _load_config() -> dict[str, str]:
    if CONFIG_FILE.exists():
        return json.loads(CONFIG_FILE.read_text())  # type: ignore[no-any-return]
    return {}


def _save_config(config: dict[str, str]) -> None:
    _ensure_config_dir()
    CONFIG_FILE.write_text(json.dumps(config, indent=2) + "\n")
    CONFIG_FILE.chmod(0o600)


def get_api_key() -> str:
    """Return the API key from env var or config file."""
    key = os.environ.get(ENV_API_KEY) or _load_config().get("api_key")
    if not key:
        raise typer.BadParameter(
            f"No API key found. Set {ENV_API_KEY} or run: posthog auth login"
        )
    return key


def get_host() -> str:
    """Return the PostHog host from env var or config file."""
    return os.environ.get(ENV_HOST) or _load_config().get("host") or DEFAULT_HOST


def get_project_id() -> str | None:
    """Return the project ID from env var or config file."""
    return os.environ.get(ENV_PROJECT_ID) or _load_config().get("project_id")


def require_project_id() -> str:
    """Return the project ID, raising an error if not set."""
    pid = get_project_id()
    if not pid:
        raise typer.BadParameter(
            f"No project ID set. Set {ENV_PROJECT_ID} or run: posthog project switch"
        )
    return pid


def save_credentials(
    api_key: str,
    host: str = DEFAULT_HOST,
    project_id: str | None = None,
) -> None:
    """Persist credentials to the config file."""
    config = _load_config()
    config["api_key"] = api_key
    config["host"] = host
    if project_id:
        config["project_id"] = project_id
    _save_config(config)


def save_project_id(project_id: str) -> None:
    """Persist the active project ID."""
    config = _load_config()
    config["project_id"] = project_id
    _save_config(config)


def get_config_path() -> Path:
    return CONFIG_FILE
