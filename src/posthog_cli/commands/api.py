"""Raw API commands — call arbitrary PostHog API endpoints."""

from __future__ import annotations

import json
from typing import Annotated

import typer

from posthog_cli import client
from posthog_cli.output import print_json, print_success

app = typer.Typer(help="Call arbitrary PostHog API endpoints.")


@app.command("get")
def api_get(
    path: Annotated[str, typer.Argument(help="API path, e.g. /feature_flags/")],
) -> None:
    """Send a GET request to the PostHog API."""
    result = client.get(path)
    print_json(result)


@app.command("post")
def api_post(
    path: Annotated[str, typer.Argument(help="API path, e.g. /query/")],
    data: Annotated[
        str,
        typer.Option("--data", "-d", help="JSON request body."),
    ] = "{}",
) -> None:
    """Send a POST request to the PostHog API."""
    parsed = json.loads(data)
    result = client.post(path, data=parsed)
    print_json(result)


@app.command("patch")
def api_patch(
    path: Annotated[str, typer.Argument(help="API path, e.g. /feature_flags/123/")],
    data: Annotated[
        str,
        typer.Option("--data", "-d", help="JSON request body."),
    ] = "{}",
) -> None:
    """Send a PATCH request to the PostHog API."""
    parsed = json.loads(data)
    result = client.patch(path, data=parsed)
    print_json(result)


@app.command("delete")
def api_delete(
    path: Annotated[str, typer.Argument(help="API path, e.g. /feature_flags/123/")],
) -> None:
    """Send a DELETE request to the PostHog API."""
    client.delete(path)
    print_success(f"DELETE {path} succeeded.")
