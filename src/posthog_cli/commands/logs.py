"""Log querying commands."""

from __future__ import annotations

from typing import Annotated

import typer

from posthog_cli import client
from posthog_cli.output import console, is_json_mode, print_json, print_table

app = typer.Typer(help="Query and explore logs.")


@app.command("query")
def query_logs(
    date_from: Annotated[
        str, typer.Option(help="Start date (ISO 8601).")
    ],
    date_to: Annotated[
        str, typer.Option(help="End date (ISO 8601).")
    ],
    severity: Annotated[
        list[str] | None,
        typer.Option(help="Severity: trace, debug, info, warn, error, fatal."),
    ] = None,
    service: Annotated[
        list[str] | None,
        typer.Option(help="Filter by service name."),
    ] = None,
    search: Annotated[
        str | None, typer.Option(help="Free text search in log messages.")
    ] = None,
    limit: Annotated[
        int, typer.Option(help="Maximum number of results.")
    ] = 100,
    cursor: Annotated[
        str | None, typer.Option(help="Pagination cursor.")
    ] = None,
) -> None:
    """Query logs with filters."""
    payload: dict[str, object] = {
        "date_from": date_from,
        "date_to": date_to,
        "limit": limit,
        "order_by": "latest",
    }
    if severity:
        payload["severity_levels"] = severity
    if service:
        payload["service_names"] = service
    if search:
        payload["filters"] = [
            {"key": "message", "type": "log", "operator": "icontains", "value": search}
        ]
    if cursor:
        payload["after"] = cursor

    data = client.post("/logs/query/", data=payload)  # type: ignore[arg-type]

    if is_json_mode():
        print_json(data)
    else:
        results = data.get("results", [])
        if not results:
            console.print("No log entries found.")
            return

        print_table(
            results,
            [
                ("Timestamp", "timestamp"),
                ("Severity", "severity_text"),
                ("Service", "service_name"),
                ("Message", "body"),
            ],
        )

        next_cursor = data.get("nextCursor")
        if next_cursor:
            console.print(f"\nNext page: --cursor {next_cursor}")


@app.command("attributes")
def list_attributes() -> None:
    """List available log attributes for filtering."""
    data = client.get("/logs/attributes/")
    if is_json_mode():
        print_json(data)
    else:
        attributes = data if isinstance(data, list) else data.get("results", [])
        for attr in attributes:
            if isinstance(attr, str):
                console.print(f"  {attr}")
            elif isinstance(attr, dict):
                console.print(f"  {attr.get('key', attr)}")
