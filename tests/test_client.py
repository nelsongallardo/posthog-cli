"""Tests for posthog_cli.client module using pytest-httpx."""

from __future__ import annotations

import pytest
import typer
from pytest_httpx import HTTPXMock

from posthog_cli import client


@pytest.fixture(autouse=True)
def _set_credentials(mock_api_key: str, mock_host: str, mock_project_id: str) -> None:
    """Ensure every test in this module has valid credentials via env vars."""


class TestGet:
    def test_get_project_scoped(self, httpx_mock: HTTPXMock) -> None:
        httpx_mock.add_response(
            url="https://us.posthog.com/api/projects/12345/feature_flags/",
            json={"results": []},
        )
        result = client.get("/feature_flags/")
        assert result == {"results": []}

    def test_get_non_project(self, httpx_mock: HTTPXMock) -> None:
        httpx_mock.add_response(
            url="https://us.posthog.com/api/projects/",
            json={"results": [{"id": 1}]},
        )
        result = client.get("/api/projects/", project=False)
        assert result["results"][0]["id"] == 1

    def test_get_with_params(self, httpx_mock: HTTPXMock) -> None:
        httpx_mock.add_response(
            url="https://us.posthog.com/api/projects/12345/feature_flags/?limit=5",
            json={"results": []},
        )
        client.get("/feature_flags/", params={"limit": 5})

    def test_get_error_exits(self, httpx_mock: HTTPXMock) -> None:
        httpx_mock.add_response(
            url="https://us.posthog.com/api/projects/12345/feature_flags/",
            status_code=403,
            json={"detail": "Forbidden"},
        )
        with pytest.raises((SystemExit, Exception)):
            client.get("/feature_flags/")

    def test_get_sends_auth_header(self, httpx_mock: HTTPXMock) -> None:
        httpx_mock.add_response(
            url="https://us.posthog.com/api/projects/12345/feature_flags/",
            json={},
        )
        client.get("/feature_flags/")
        request = httpx_mock.get_request()
        assert request is not None
        assert request.headers["authorization"] == "Bearer phx_testkey1234567890"


class TestPost:
    def test_post_project_scoped(self, httpx_mock: HTTPXMock) -> None:
        httpx_mock.add_response(
            url="https://us.posthog.com/api/projects/12345/feature_flags/",
            json={"id": 1, "key": "new-flag"},
            status_code=201,
        )
        result = client.post("/feature_flags/", data={"key": "new-flag"})
        assert result["key"] == "new-flag"

    def test_post_204_returns_none(self, httpx_mock: HTTPXMock) -> None:
        httpx_mock.add_response(
            url="https://us.posthog.com/api/projects/12345/query/",
            status_code=204,
        )
        assert client.post("/query/", data={}) is None

    def test_post_error(self, httpx_mock: HTTPXMock) -> None:
        httpx_mock.add_response(
            url="https://us.posthog.com/api/projects/12345/feature_flags/",
            status_code=400,
            json={"error": "Bad request"},
        )
        with pytest.raises((SystemExit, Exception)):
            client.post("/feature_flags/", data={})


class TestPatch:
    def test_patch_project_scoped(self, httpx_mock: HTTPXMock) -> None:
        httpx_mock.add_response(
            url="https://us.posthog.com/api/projects/12345/feature_flags/1/",
            json={"id": 1, "active": False},
        )
        result = client.patch("/feature_flags/1/", data={"active": False})
        assert result["active"] is False

    def test_patch_204(self, httpx_mock: HTTPXMock) -> None:
        httpx_mock.add_response(
            url="https://us.posthog.com/api/projects/12345/something/",
            status_code=204,
        )
        assert client.patch("/something/") is None


class TestDelete:
    def test_delete_project_scoped(self, httpx_mock: HTTPXMock) -> None:
        httpx_mock.add_response(
            url="https://us.posthog.com/api/projects/12345/feature_flags/1/",
            status_code=204,
        )
        # Should not raise
        client.delete("/feature_flags/1/")

    def test_delete_error(self, httpx_mock: HTTPXMock) -> None:
        httpx_mock.add_response(
            url="https://us.posthog.com/api/projects/12345/feature_flags/999/",
            status_code=404,
            json={"detail": "Not found"},
        )
        with pytest.raises((SystemExit, Exception)):
            client.delete("/feature_flags/999/")


class TestErrorDetail:
    def test_json_detail(self) -> None:
        import httpx

        resp = httpx.Response(400, json={"detail": "Bad request"})
        assert client._error_detail(resp) == "Bad request"

    def test_json_error_key(self) -> None:
        import httpx

        resp = httpx.Response(400, json={"error": "Something broke"})
        assert client._error_detail(resp) == "Something broke"

    def test_non_json(self) -> None:
        import httpx

        resp = httpx.Response(500, text="Server Error")
        assert client._error_detail(resp) == "Server Error"
