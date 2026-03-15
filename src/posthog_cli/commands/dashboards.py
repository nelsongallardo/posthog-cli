"""CLI commands for managing PostHog dashboards."""

from __future__ import annotations

from typing import Annotated, Any

import typer

from posthog_cli import client
from posthog_cli.output import (
    confirm,
    is_json_mode,
    print_detail,
    print_json,
    print_success,
    print_table,
)

app = typer.Typer(help="Manage dashboards.")


# -- Column / field definitions ------------------------------------------------

_LIST_COLUMNS: list[tuple[str, str]] = [
    ("ID", "id"),
    ("Name", "name"),
    ("Description", "description"),
    ("Pinned", "pinned"),
    ("Created At", "created_at"),
]

_DETAIL_FIELDS: list[tuple[str, str]] = [
    ("ID", "id"),
    ("Name", "name"),
    ("Description", "description"),
    ("Pinned", "pinned"),
    ("Tags", "_tags_display"),
    ("Created At", "created_at"),
]

_TILE_COLUMNS: list[tuple[str, str]] = [
    ("Tile ID", "id"),
    ("Insight ID", "_insight_id"),
    ("Insight Name", "_insight_name"),
]


# -- Helpers -------------------------------------------------------------------


def _enrich_tiles(tiles: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Add flattened insight fields to each tile dict for table display."""
    for tile in tiles:
        insight = tile.get("insight") or {}
        tile["_insight_id"] = str(insight.get("id", ""))
        tile["_insight_name"] = insight.get("name", "")
    return tiles


# -- Commands ------------------------------------------------------------------


@app.command("list")
def list_dashboards(
    search: Annotated[
        str | None,
        typer.Option("--search", help="Filter dashboards by name."),
    ] = None,
    pinned: Annotated[
        bool | None,
        typer.Option("--pinned/--all", help="Show only pinned dashboards."),
    ] = None,
    limit: Annotated[
        int,
        typer.Option("--limit", help="Maximum number of dashboards to return."),
    ] = 100,
) -> None:
    """List all dashboards."""
    params: dict[str, object] = {"limit": limit}
    if search is not None:
        params["search"] = search
    if pinned is True:
        params["pinned"] = "true"

    data = client.get("/dashboards/", params=params)
    results = data.get("results", data) if isinstance(data, dict) else data

    if is_json_mode():
        print_json(results)
    else:
        print_table(results, _LIST_COLUMNS)


@app.command("get")
def get_dashboard(
    dashboard_id: Annotated[
        int,
        typer.Argument(help="The ID of the dashboard."),
    ],
) -> None:
    """Get details of a single dashboard."""
    data = client.get(f"/dashboards/{dashboard_id}/")

    tags = data.get("tags") or []
    data["_tags_display"] = ", ".join(tags) if tags else ""

    if is_json_mode():
        print_json(data)
        return

    print_detail(data, _DETAIL_FIELDS)

    tiles = data.get("tiles") or []
    if tiles:
        _enrich_tiles(tiles)
        typer.echo("")
        print_table(tiles, _TILE_COLUMNS, title="Tiles")


@app.command("create")
def create_dashboard(
    name: Annotated[
        str,
        typer.Option("--name", help="Name of the dashboard."),
    ],
    description: Annotated[
        str,
        typer.Option("--description", help="Description of the dashboard."),
    ] = "",
    pinned: Annotated[
        bool,
        typer.Option("--pinned/--no-pinned", help="Whether the dashboard is pinned."),
    ] = False,
    tags: Annotated[
        str | None,
        typer.Option("--tags", help="Comma-separated list of tags."),
    ] = None,
) -> None:
    """Create a new dashboard."""
    payload: dict[str, object] = {
        "name": name,
        "description": description,
        "pinned": pinned,
    }
    if tags is not None:
        payload["tags"] = [t.strip() for t in tags.split(",") if t.strip()]

    data = client.post("/dashboards/", data=payload)

    if is_json_mode():
        print_json(data)
    else:
        print_success(f"Dashboard '{data.get('name', name)}' created (ID {data.get('id', '?')}).")
        data["_tags_display"] = ", ".join(data.get("tags") or [])
        print_detail(data, _DETAIL_FIELDS)


@app.command("update")
def update_dashboard(
    dashboard_id: Annotated[
        int,
        typer.Argument(help="The ID of the dashboard to update."),
    ],
    name: Annotated[
        str | None,
        typer.Option("--name", help="New name."),
    ] = None,
    description: Annotated[
        str | None,
        typer.Option("--description", help="New description."),
    ] = None,
    pinned: Annotated[
        bool | None,
        typer.Option("--pinned/--no-pinned", help="Set pinned state."),
    ] = None,
    tags: Annotated[
        str | None,
        typer.Option("--tags", help="Comma-separated list of tags."),
    ] = None,
) -> None:
    """Update an existing dashboard."""
    payload: dict[str, object] = {}

    if name is not None:
        payload["name"] = name
    if description is not None:
        payload["description"] = description
    if pinned is not None:
        payload["pinned"] = pinned
    if tags is not None:
        payload["tags"] = [t.strip() for t in tags.split(",") if t.strip()]

    if not payload:
        raise typer.BadParameter("No update options provided. Pass at least one option to update.")

    data = client.patch(f"/dashboards/{dashboard_id}/", data=payload)

    if is_json_mode():
        print_json(data)
    else:
        print_success(f"Dashboard {dashboard_id} updated.")
        data["_tags_display"] = ", ".join(data.get("tags") or [])
        print_detail(data, _DETAIL_FIELDS)


@app.command("add-insight")
def add_insight(
    dashboard_id: Annotated[
        int,
        typer.Option("--dashboard-id", help="The ID of the dashboard."),
    ],
    insight_id: Annotated[
        int,
        typer.Option("--insight-id", help="The ID of the insight to add."),
    ],
) -> None:
    """Add an insight to a dashboard as a tile."""
    data = client.post(
        f"/dashboards/{dashboard_id}/tiles",
        data={"insight": insight_id},
    )

    if is_json_mode():
        print_json(data)
    else:
        print_success(f"Insight {insight_id} added to dashboard {dashboard_id}.")


@app.command("delete")
def delete_dashboard(
    dashboard_id: Annotated[
        int,
        typer.Argument(help="The ID of the dashboard to delete."),
    ],
) -> None:
    """Delete a dashboard."""
    if not confirm(f"Delete dashboard {dashboard_id}? This cannot be undone."):
        raise typer.Abort()

    client.delete(f"/dashboards/{dashboard_id}/")

    if is_json_mode():
        print_json({"deleted": True, "id": dashboard_id})
    else:
        print_success(f"Dashboard {dashboard_id} deleted.")
