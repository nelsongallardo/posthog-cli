"""Tests for posthog_cli.config module."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
import typer

from posthog_cli import config as cfg


class TestLoadSave:
    def test_load_empty_returns_dict(self) -> None:
        assert cfg._load_config() == {}

    def test_save_and_load_roundtrip(self) -> None:
        cfg._save_config({"api_key": "phx_abc", "host": "https://eu.posthog.com"})
        loaded = cfg._load_config()
        assert loaded["api_key"] == "phx_abc"
        assert loaded["host"] == "https://eu.posthog.com"

    def test_save_sets_permissions(self) -> None:
        cfg._save_config({"api_key": "phx_abc"})
        mode = cfg.CONFIG_FILE.stat().st_mode & 0o777
        assert mode == 0o600

    def test_save_creates_parent_dir(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        nested = tmp_path / "deep" / "nested"
        monkeypatch.setattr(cfg, "CONFIG_DIR", nested)
        monkeypatch.setattr(cfg, "CONFIG_FILE", nested / "config.json")
        cfg._save_config({"api_key": "phx_x"})
        assert (nested / "config.json").exists()


class TestGetApiKey:
    def test_from_env(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("POSTHOG_API_KEY", "phx_env")
        assert cfg.get_api_key() == "phx_env"

    def test_from_config_file(self, saved_config: Path) -> None:
        assert cfg.get_api_key() == "phx_testkey1234567890"

    def test_env_overrides_file(
        self, monkeypatch: pytest.MonkeyPatch, saved_config: Path
    ) -> None:
        monkeypatch.setenv("POSTHOG_API_KEY", "phx_override")
        assert cfg.get_api_key() == "phx_override"

    def test_missing_raises(self) -> None:
        with pytest.raises(typer.BadParameter, match="No API key"):
            cfg.get_api_key()


class TestGetHost:
    def test_default(self) -> None:
        assert cfg.get_host() == "https://us.posthog.com"

    def test_from_env(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("POSTHOG_HOST", "https://custom.host")
        assert cfg.get_host() == "https://custom.host"

    def test_from_config(self, saved_config: Path) -> None:
        assert cfg.get_host() == "https://us.posthog.com"


class TestGetProjectId:
    def test_none_by_default(self) -> None:
        assert cfg.get_project_id() is None

    def test_from_env(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("POSTHOG_PROJECT_ID", "999")
        assert cfg.get_project_id() == "999"

    def test_from_config(self, saved_config: Path) -> None:
        assert cfg.get_project_id() == "12345"


class TestRequireProjectId:
    def test_raises_when_missing(self) -> None:
        with pytest.raises(typer.BadParameter, match="No project ID"):
            cfg.require_project_id()

    def test_returns_id(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("POSTHOG_PROJECT_ID", "42")
        assert cfg.require_project_id() == "42"


class TestSaveCredentials:
    def test_save_all(self) -> None:
        cfg.save_credentials("phx_key", "https://eu.posthog.com", "55")
        c = cfg._load_config()
        assert c["api_key"] == "phx_key"
        assert c["host"] == "https://eu.posthog.com"
        assert c["project_id"] == "55"

    def test_save_without_project(self) -> None:
        cfg.save_credentials("phx_key", "https://us.posthog.com")
        c = cfg._load_config()
        assert c["api_key"] == "phx_key"
        assert "project_id" not in c

    def test_save_project_id(self, saved_config: Path) -> None:
        cfg.save_project_id("99999")
        assert cfg._load_config()["project_id"] == "99999"
