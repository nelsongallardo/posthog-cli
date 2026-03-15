"""Entity search and docs search commands."""

from __future__ import annotations

from typing import Annotated

import typer

from posthog_cli import client
from posthog_cli.output import is_json_mode, print_json, print_table

app = typer.Typer(help="Search entities and documentation.")


@app.command("persons")
def search_persons(
    query: Annotated[str, typer.Argument(help="Search query (email, name, distinct ID).")],
    limit: Annotated[int, typer.Option(help="Maximum number of results.")] = 20,
) -> None:
    """Search for persons by email, name, or distinct ID."""
    data = client.get("/persons/", params={"search": query, "limit": limit})
    rows = data.get("results", []) if isinstance(data, dict) else data

    if is_json_mode():
        print_json(rows)
    else:
        display_rows = []
        for person in rows:
            props = person.get("properties", {})
            display_rows.append({
                "id": person.get("id", ""),
                "distinct_ids": ", ".join(person.get("distinct_ids", [])[:3]),
                "email": props.get("email", ""),
                "name": props.get("name", ""),
                "created_at": person.get("created_at", ""),
            })
        print_table(
            display_rows,
            [
                ("ID", "id"),
                ("Distinct IDs", "distinct_ids"),
                ("Email", "email"),
                ("Name", "name"),
                ("Created At", "created_at"),
            ],
        )


@app.command("groups")
def search_groups(
    query: Annotated[str, typer.Argument(help="Search query.")],
    group_type_index: Annotated[int, typer.Option("--type-index", help="Group type index.")] = 0,
    limit: Annotated[int, typer.Option(help="Maximum number of results.")] = 20,
) -> None:
    """Search for groups."""
    data = client.get(
        "/groups/",
        params={"search": query, "group_type_index": group_type_index, "limit": limit},
    )
    rows = data.get("results", []) if isinstance(data, dict) else data

    if is_json_mode():
        print_json(rows)
    else:
        print_table(
            rows,
            [
                ("Group Key", "group_key"),
                ("Group Type Index", "group_type_index"),
                ("Created At", "created_at"),
            ],
        )


@app.command("events")
def list_event_definitions(
    search: Annotated[str | None, typer.Option(help="Filter by event name.")] = None,
    limit: Annotated[int, typer.Option(help="Maximum number of results.")] = 50,
) -> None:
    """List event definitions in the project."""
    params: dict[str, object] = {"limit": limit}
    if search:
        params["search"] = search

    data = client.get("/event_definitions/", params=params)
    rows = data.get("results", []) if isinstance(data, dict) else data
    print_table(
        rows,
        [
            ("Name", "name"),
            ("Volume (30d)", "volume_30_day"),
            ("Query Usage (30d)", "query_usage_30_day"),
            ("Last Seen", "last_seen_at"),
        ],
    )


@app.command("properties")
def list_properties(
    search: Annotated[str | None, typer.Option(help="Filter by property name.")] = None,
    event: Annotated[str | None, typer.Option(help="Filter properties by event name.")] = None,
    limit: Annotated[int, typer.Option(help="Maximum number of results.")] = 50,
) -> None:
    """List property definitions in the project."""
    params: dict[str, object] = {"limit": limit}
    if search:
        params["search"] = search
    if event:
        params["event_names"] = [event]

    data = client.get("/property_definitions/", params=params)
    rows = data.get("results", []) if isinstance(data, dict) else data
    print_table(
        rows,
        [
            ("Name", "name"),
            ("Type", "property_type"),
            ("Is Numerical", "is_numerical"),
            ("Query Usage (30d)", "query_usage_30_day"),
        ],
    )
