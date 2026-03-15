"""HTTP client for the PostHog API."""

from __future__ import annotations

from typing import Any

import httpx
import typer
from rich.console import Console

from posthog_cli.config import get_api_key, get_host, require_project_id

_TIMEOUT = 30.0
_err = Console(stderr=True)


def _headers() -> dict[str, str]:
    return {
        "Authorization": f"Bearer {get_api_key()}",
        "Content-Type": "application/json",
    }


def _base_url() -> str:
    return get_host().rstrip("/")


def _project_url(path: str = "") -> str:
    return f"{_base_url()}/api/projects/{require_project_id()}{path}"


def _error_detail(resp: httpx.Response) -> str:
    try:
        body = resp.json()
        if isinstance(body, dict):
            return body.get("detail") or body.get("error") or str(body)
        return str(body)
    except Exception:
        return resp.text


def _check(resp: httpx.Response) -> None:
    if resp.is_error:
        _err.print(
            f"[red]API error {resp.status_code}:[/red] "
            f"{_error_detail(resp)}"
        )
        raise typer.Exit(code=1)


# ── Generic helpers ──────────────────────────────────────────────────


def get(
    path: str,
    *,
    params: dict[str, Any] | None = None,
    project: bool = True,
) -> Any:
    url = _project_url(path) if project else f"{_base_url()}{path}"
    resp = httpx.get(url, headers=_headers(), params=params, timeout=_TIMEOUT)
    _check(resp)
    return resp.json()


def post(
    path: str,
    *,
    data: dict[str, Any] | None = None,
    project: bool = True,
) -> Any:
    url = _project_url(path) if project else f"{_base_url()}{path}"
    resp = httpx.post(
        url, headers=_headers(), json=data or {}, timeout=_TIMEOUT
    )
    _check(resp)
    if resp.status_code == 204:
        return None
    return resp.json()


def patch(
    path: str,
    *,
    data: dict[str, Any] | None = None,
    project: bool = True,
) -> Any:
    url = _project_url(path) if project else f"{_base_url()}{path}"
    resp = httpx.patch(
        url, headers=_headers(), json=data or {}, timeout=_TIMEOUT
    )
    _check(resp)
    if resp.status_code == 204:
        return None
    return resp.json()


def delete(path: str, *, project: bool = True) -> None:
    url = _project_url(path) if project else f"{_base_url()}{path}"
    resp = httpx.delete(url, headers=_headers(), timeout=_TIMEOUT)
    _check(resp)
