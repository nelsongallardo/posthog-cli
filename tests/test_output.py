"""Tests for posthog_cli.output module."""

from __future__ import annotations

import json

import pytest

from posthog_cli import output


@pytest.fixture(autouse=True)
def _reset_modes() -> None:
    """Reset global modes before each test."""
    output.set_json_mode(False)
    output.set_yes_mode(False)


class TestJsonMode:
    def test_default_off(self) -> None:
        assert output.is_json_mode() is False

    def test_toggle_on(self) -> None:
        output.set_json_mode(True)
        assert output.is_json_mode() is True

    def test_toggle_off(self) -> None:
        output.set_json_mode(True)
        output.set_json_mode(False)
        assert output.is_json_mode() is False


class TestYesMode:
    def test_default_off(self) -> None:
        assert output.is_yes_mode() is False

    def test_toggle_on(self) -> None:
        output.set_yes_mode(True)
        assert output.is_yes_mode() is True


class TestConfirm:
    def test_yes_mode_skips_prompt(self) -> None:
        output.set_yes_mode(True)
        assert output.confirm("Delete?") is True

    def test_no_yes_mode_delegates_to_typer(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr("typer.confirm", lambda msg: True)
        assert output.confirm("Do it?") is True


class TestPrintJson:
    def test_outputs_json(self, capsys: pytest.CaptureFixture[str]) -> None:
        output.print_json({"key": "value"})
        captured = capsys.readouterr()
        data = json.loads(captured.out)
        assert data == {"key": "value"}

    def test_handles_nested(self, capsys: pytest.CaptureFixture[str]) -> None:
        output.print_json({"a": [1, 2, {"b": 3}]})
        data = json.loads(capsys.readouterr().out)
        assert data["a"][2]["b"] == 3


class TestPrintDetail:
    def test_json_mode(self, capsys: pytest.CaptureFixture[str]) -> None:
        output.set_json_mode(True)
        output.print_detail(
            {"id": 1, "name": "Test"},
            [("ID", "id"), ("Name", "name")],
        )
        data = json.loads(capsys.readouterr().out)
        assert data["id"] == 1

    def test_table_mode(self, capsys: pytest.CaptureFixture[str]) -> None:
        output.print_detail(
            {"id": 1, "name": "Test"},
            [("ID", "id"), ("Name", "name")],
        )
        out = capsys.readouterr().out
        # Rich table output should contain the values
        assert "1" in out
        assert "Test" in out

    def test_nested_key(self, capsys: pytest.CaptureFixture[str]) -> None:
        output.set_json_mode(True)
        output.print_detail(
            {"info": {"nested": "val"}},
            [("Nested", "info.nested")],
        )
        data = json.loads(capsys.readouterr().out)
        assert data["info"]["nested"] == "val"


class TestPrintTable:
    def test_json_mode(self, capsys: pytest.CaptureFixture[str]) -> None:
        output.set_json_mode(True)
        rows = [{"id": 1, "name": "A"}, {"id": 2, "name": "B"}]
        output.print_table(rows, [("ID", "id"), ("Name", "name")])
        data = json.loads(capsys.readouterr().out)
        assert len(data) == 2
        assert data[0]["name"] == "A"

    def test_table_mode(self, capsys: pytest.CaptureFixture[str]) -> None:
        rows = [{"id": 1, "name": "Hello"}]
        output.print_table(rows, [("ID", "id"), ("Name", "name")])
        out = capsys.readouterr().out
        assert "Hello" in out

    def test_empty_rows(self, capsys: pytest.CaptureFixture[str]) -> None:
        output.print_table([], [("ID", "id")])
        out = capsys.readouterr().out
        # Should still render the table header
        assert "ID" in out


class TestPrintSuccess:
    def test_json_mode_suppresses(self, capsys: pytest.CaptureFixture[str]) -> None:
        output.set_json_mode(True)
        output.print_success("done")
        assert capsys.readouterr().out == ""

    def test_normal_mode(self, capsys: pytest.CaptureFixture[str]) -> None:
        output.print_success("done")
        assert "done" in capsys.readouterr().out


class TestPrintWarning:
    def test_json_mode_suppresses(self, capsys: pytest.CaptureFixture[str]) -> None:
        output.set_json_mode(True)
        output.print_warning("careful")
        captured = capsys.readouterr()
        assert captured.err == ""
