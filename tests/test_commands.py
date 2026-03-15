"""End-to-end CLI command tests using typer.testing.CliRunner."""

from __future__ import annotations

import json
from typing import Any
from unittest.mock import patch

import pytest
from typer.testing import CliRunner

from posthog_cli.main import app
from tests.conftest import (
    SAMPLE_FLAG,
    SAMPLE_FLAGS_LIST,
    SAMPLE_ORG_RESPONSE,
    SAMPLE_PROJECT,
    SAMPLE_PROJECTS_LIST,
)

runner = CliRunner()


# ── Helpers ──────────────────────────────────────────────────────────


def _env_vars() -> dict[str, str]:
    return {
        "POSTHOG_API_KEY": "phx_testkey1234567890",
        "POSTHOG_HOST": "https://us.posthog.com",
        "POSTHOG_PROJECT_ID": "12345",
    }


# ── Global / main app tests ─────────────────────────────────────────


class TestMainApp:
    def test_version(self) -> None:
        result = runner.invoke(app, ["--version"])
        assert result.exit_code == 0
        assert "posthog-cli" in result.stdout

    def test_help(self) -> None:
        result = runner.invoke(app, ["--help"])
        assert result.exit_code == 0
        assert "PostHog CLI" in result.stdout


# ── Feature flag commands ────────────────────────────────────────────


class TestFlagCommands:
    def test_flag_list(self) -> None:
        with patch("posthog_cli.client.get", return_value=SAMPLE_FLAGS_LIST):
            result = runner.invoke(app, ["flag", "list"], env=_env_vars())
        assert result.exit_code == 0
        assert "beta-feature" in result.stdout

    def test_flag_list_json(self) -> None:
        with patch("posthog_cli.client.get", return_value=SAMPLE_FLAGS_LIST):
            result = runner.invoke(app, ["--json", "flag", "list"], env=_env_vars())
        assert result.exit_code == 0
        data = json.loads(result.stdout)
        assert isinstance(data, list)
        assert data[0]["key"] == "beta-feature"

    def test_flag_get(self) -> None:
        with patch("posthog_cli.client.get", return_value=SAMPLE_FLAG.copy()):
            result = runner.invoke(app, ["flag", "get", "1"], env=_env_vars())
        assert result.exit_code == 0
        assert "beta-feature" in result.stdout

    def test_flag_get_json(self) -> None:
        with patch("posthog_cli.client.get", return_value=SAMPLE_FLAG.copy()):
            result = runner.invoke(app, ["--json", "flag", "get", "1"], env=_env_vars())
        assert result.exit_code == 0
        data = json.loads(result.stdout)
        assert data["key"] == "beta-feature"

    def test_flag_create(self) -> None:
        created = {**SAMPLE_FLAG, "id": 2, "key": "new-flag", "name": "New"}
        with patch("posthog_cli.client.post", return_value=created):
            result = runner.invoke(
                app,
                ["--json", "flag", "create", "--key", "new-flag", "--name", "New"],
                env=_env_vars(),
            )
        assert result.exit_code == 0
        data = json.loads(result.stdout)
        assert data["key"] == "new-flag"

    def test_flag_update(self) -> None:
        updated = {**SAMPLE_FLAG, "name": "Updated Name"}
        with patch("posthog_cli.client.patch", return_value=updated):
            result = runner.invoke(
                app,
                ["--json", "flag", "update", "1", "--name", "Updated Name"],
                env=_env_vars(),
            )
        assert result.exit_code == 0
        data = json.loads(result.stdout)
        assert data["name"] == "Updated Name"

    def test_flag_delete(self) -> None:
        with patch("posthog_cli.client.delete"):
            result = runner.invoke(
                app,
                ["--yes", "--json", "flag", "delete", "1"],
                env=_env_vars(),
            )
        assert result.exit_code == 0
        data = json.loads(result.stdout)
        assert data["deleted"] is True

    def test_flag_list_with_search(self) -> None:
        with patch("posthog_cli.client.get", return_value=SAMPLE_FLAGS_LIST) as mock_get:
            result = runner.invoke(
                app, ["flag", "list", "--search", "beta"], env=_env_vars()
            )
        assert result.exit_code == 0
        call_args = mock_get.call_args
        assert call_args[1]["params"]["search"] == "beta"


# ── Project commands ─────────────────────────────────────────────────


class TestProjectCommands:
    def test_project_list(self) -> None:
        with patch("posthog_cli.client.get", return_value=SAMPLE_PROJECTS_LIST):
            result = runner.invoke(app, ["project", "list"], env=_env_vars())
        assert result.exit_code == 0
        assert "My Project" in result.stdout

    def test_project_current(self) -> None:
        with patch("posthog_cli.client.get", return_value=SAMPLE_PROJECT):
            result = runner.invoke(app, ["project", "current"], env=_env_vars())
        assert result.exit_code == 0
        assert "My Project" in result.stdout

    def test_project_current_no_project(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        env = {**_env_vars()}
        del env["POSTHOG_PROJECT_ID"]
        monkeypatch.delenv("POSTHOG_PROJECT_ID", raising=False)
        result = runner.invoke(app, ["project", "current"], env=env)
        assert result.exit_code == 1

    def test_project_switch(self) -> None:
        with (
            patch("posthog_cli.client.get", return_value=SAMPLE_PROJECT),
            patch("posthog_cli.commands.projects.save_project_id") as mock_save,
        ):
            result = runner.invoke(
                app, ["project", "switch", "99999"], env=_env_vars()
            )
        assert result.exit_code == 0
        mock_save.assert_called_once_with("99999")


# ── Auth commands ────────────────────────────────────────────────────


class TestAuthCommands:
    def test_auth_status_logged_in(self) -> None:
        env = _env_vars()
        result = runner.invoke(app, ["auth", "status"], env=env)
        assert result.exit_code == 0
        assert "Yes" in result.stdout

    def test_auth_status_not_logged_in(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.delenv("POSTHOG_API_KEY", raising=False)
        result = runner.invoke(app, ["auth", "status"])
        assert result.exit_code == 0
        assert "No" in result.stdout

    def test_auth_status_json(self) -> None:
        env = _env_vars()
        result = runner.invoke(app, ["--json", "auth", "status"], env=env)
        assert result.exit_code == 0
        data = json.loads(result.stdout)
        assert data["logged_in"] == "Yes"

    def test_auth_login_auto_detect(self) -> None:
        """Test login with auto-detection (no --host)."""
        from posthog_cli.commands.auth import _try_auth

        with (
            patch(
                "posthog_cli.commands.auth._try_auth",
                return_value=(True, None, SAMPLE_ORG_RESPONSE),
            ),
            patch("posthog_cli.config.save_credentials") as mock_save,
        ):
            result = runner.invoke(
                app,
                ["auth", "login", "--api-key", "phx_newkey"],
                input="\n",  # blank project ID
            )
        assert result.exit_code == 0
        assert "Logged in" in result.stdout

    def test_auth_login_explicit_host(self) -> None:
        with (
            patch(
                "posthog_cli.commands.auth._try_auth",
                return_value=(True, None, SAMPLE_ORG_RESPONSE),
            ),
            patch("posthog_cli.commands.auth.save_credentials") as mock_save,
        ):
            result = runner.invoke(
                app,
                [
                    "auth",
                    "login",
                    "--api-key",
                    "phx_key",
                    "--host",
                    "https://eu.posthog.com",
                ],
                input="\n",
            )
        assert result.exit_code == 0
        mock_save.assert_called_once()

    def test_auth_login_fail(self) -> None:
        with patch(
            "posthog_cli.commands.auth._try_auth",
            return_value=(False, "Invalid key", None),
        ):
            result = runner.invoke(
                app,
                [
                    "auth",
                    "login",
                    "--api-key",
                    "phx_bad",
                    "--host",
                    "https://us.posthog.com",
                ],
                input="\n",
            )
        assert result.exit_code == 1
