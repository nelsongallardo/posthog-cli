"""Tests for posthog_cli.commands.activity module."""

from __future__ import annotations

import json
from unittest.mock import patch

import pytest

from posthog_cli.commands.activity import _parse_interval, _safe_pct


class TestParseInterval:
    def test_days(self) -> None:
        assert _parse_interval("-30d") == "30 DAY"

    def test_weeks(self) -> None:
        assert _parse_interval("-4w") == "4 WEEK"

    def test_months(self) -> None:
        assert _parse_interval("-3m") == "3 MONTH"

    def test_no_dash(self) -> None:
        assert _parse_interval("7d") == "7 DAY"

    def test_unknown_suffix_defaults(self) -> None:
        assert _parse_interval("-90x") == "30 DAY"

    def test_just_number(self) -> None:
        assert _parse_interval("90") == "30 DAY"


class TestSafePct:
    def test_normal(self) -> None:
        assert _safe_pct(50, 100) == "50.0%"

    def test_zero_denom(self) -> None:
        assert _safe_pct(10, 0) == "N/A"

    def test_precision(self) -> None:
        assert _safe_pct(1, 3) == "33.3%"


class TestSummaryCommandJson:
    """Test the summary command in JSON mode."""

    def test_summary_json_output(
        self,
        mock_api_key: str,
        mock_project_id: str,
        mock_host: str,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        from posthog_cli.commands.activity import summary
        from posthog_cli.output import set_json_mode

        set_json_mode(True)

        fake_results = {
            "wau": [[" 2025-01-06", 100]],
            "top_events": [["$pageview", 500]],
            "custom_events": [],
            "weekly_custom_trends": [],
            "traffic_sources": [],
            "top_pages": [],
            "pageview_total": [[1000, 200]],
            "browsers": [],
        }

        with patch(
            "posthog_cli.commands.activity._build_summary",
            return_value=fake_results,
        ):
            summary(date_from="-30d")

        out = capsys.readouterr().out
        data = json.loads(out)
        assert "wau" in data
        assert data["pageview_total"] == [[1000, 200]]

        # Reset
        set_json_mode(False)
