"""Shared fixtures for posthog-cli tests."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest


@pytest.fixture(autouse=True)
def _isolate_config(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """Redirect config file/dir to a temp directory for every test."""
    import posthog_cli.config as cfg

    config_dir = tmp_path / "posthog-cli"
    config_dir.mkdir()
    config_file = config_dir / "config.json"

    monkeypatch.setattr(cfg, "CONFIG_DIR", config_dir)
    monkeypatch.setattr(cfg, "CONFIG_FILE", config_file)

    # Also clear env vars that might leak from the host.
    monkeypatch.delenv("POSTHOG_API_KEY", raising=False)
    monkeypatch.delenv("POSTHOG_HOST", raising=False)
    monkeypatch.delenv("POSTHOG_PROJECT_ID", raising=False)


@pytest.fixture()
def saved_config(tmp_path: Path) -> Path:
    """Write a minimal valid config and return its path.

    Because _isolate_config already patches CONFIG_FILE we need to import
    the *current* value of the attribute after monkeypatch ran.
    """
    import posthog_cli.config as cfg

    cfg._save_config(
        {
            "api_key": "phx_testkey1234567890",
            "host": "https://us.posthog.com",
            "project_id": "12345",
        }
    )
    return cfg.CONFIG_FILE


@pytest.fixture()
def mock_api_key(monkeypatch: pytest.MonkeyPatch) -> str:
    key = "phx_testkey1234567890"
    monkeypatch.setenv("POSTHOG_API_KEY", key)
    return key


@pytest.fixture()
def mock_project_id(monkeypatch: pytest.MonkeyPatch) -> str:
    pid = "12345"
    monkeypatch.setenv("POSTHOG_PROJECT_ID", pid)
    return pid


@pytest.fixture()
def mock_host(monkeypatch: pytest.MonkeyPatch) -> str:
    host = "https://us.posthog.com"
    monkeypatch.setenv("POSTHOG_HOST", host)
    return host


# ── Sample API response payloads ─────────────────────────────────────


SAMPLE_FLAG: dict[str, Any] = {
    "id": 1,
    "key": "beta-feature",
    "name": "Beta Feature",
    "description": "A test flag",
    "active": True,
    "created_at": "2025-01-01T00:00:00Z",
    "filters": {
        "groups": [{"properties": [], "rollout_percentage": 50}]
    },
}

SAMPLE_FLAGS_LIST: dict[str, Any] = {
    "results": [SAMPLE_FLAG],
    "count": 1,
}

SAMPLE_PROJECT: dict[str, Any] = {
    "id": 12345,
    "name": "My Project",
    "organization": "My Org",
    "created_at": "2025-01-01T00:00:00Z",
}

SAMPLE_PROJECTS_LIST: dict[str, Any] = {
    "results": [SAMPLE_PROJECT],
    "count": 1,
}

SAMPLE_ORG_RESPONSE: dict[str, Any] = {
    "results": [{"name": "Test Org"}],
}
