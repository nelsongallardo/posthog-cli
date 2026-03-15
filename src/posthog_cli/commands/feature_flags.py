"""CLI commands for managing PostHog feature flags."""

from __future__ import annotations

import json
from typing import Annotated

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

app = typer.Typer(help="Manage feature flags.")


# ── Helpers ────────────────────────────────────────────────────────────


def _rollout_percentage(flag: dict) -> str:
    """Extract the rollout percentage from a feature flag's filters."""
    try:
        groups = flag.get("filters", {}).get("groups", [])
        if groups:
            pct = groups[0].get("rollout_percentage")
            if pct is not None:
                return f"{pct}%"
    except (AttributeError, IndexError, TypeError):
        pass
    return ""


_LIST_COLUMNS: list[tuple[str, str]] = [
    ("ID", "id"),
    ("Key", "key"),
    ("Name", "name"),
    ("Active", "active"),
    ("Rollout %", "_rollout_pct"),
]

_DETAIL_FIELDS: list[tuple[str, str]] = [
    ("ID", "id"),
    ("Key", "key"),
    ("Name", "name"),
    ("Description", "description"),
    ("Active", "active"),
    ("Created at", "created_at"),
    ("Filters", "_filters_json"),
]


# ── Commands ───────────────────────────────────────────────────────────


@app.command("list")
def list_flags(
    search: Annotated[
        str | None,
        typer.Option("--search", help="Filter flags by key or name."),
    ] = None,
    limit: Annotated[
        int,
        typer.Option("--limit", help="Maximum number of flags to return."),
    ] = 100,
    active: Annotated[
        bool | None,
        typer.Option(
            "--active/--inactive",
            help="Show only active or inactive flags.",
        ),
    ] = None,
) -> None:
    """List all feature flags."""
    params: dict[str, object] = {"limit": limit}
    if search is not None:
        params["search"] = search
    if active is not None:
        params["active"] = str(active).lower()

    data = client.get("/feature_flags/", params=params)
    results = data.get("results", data) if isinstance(data, dict) else data

    for row in results:
        row["_rollout_pct"] = _rollout_percentage(row)

    if is_json_mode():
        print_json(results)
    else:
        print_table(results, _LIST_COLUMNS)


@app.command("get")
def get_flag(
    flag_id: Annotated[
        int,
        typer.Argument(help="The ID of the feature flag."),
    ],
) -> None:
    """Get details of a single feature flag."""
    data = client.get(f"/feature_flags/{flag_id}/")
    data["_filters_json"] = json.dumps(data.get("filters", {}), indent=2)

    if is_json_mode():
        print_json(data)
    else:
        print_detail(data, _DETAIL_FIELDS)


@app.command("create")
def create_flag(
    key: Annotated[
        str,
        typer.Option("--key", help="Unique key for the feature flag."),
    ],
    name: Annotated[
        str,
        typer.Option("--name", help="Human-readable name."),
    ],
    description: Annotated[
        str,
        typer.Option("--description", help="Optional description."),
    ] = "",
    active: Annotated[
        bool,
        typer.Option("--active/--no-active", help="Whether the flag is active."),
    ] = True,
    rollout_percentage: Annotated[
        int,
        typer.Option("--rollout-percentage", help="Rollout percentage (0-100)."),
    ] = 100,
    filters_json: Annotated[
        str | None,
        typer.Option("--filters-json", help="Raw JSON string for advanced filters."),
    ] = None,
) -> None:
    """Create a new feature flag."""
    if filters_json is not None:
        try:
            filters = json.loads(filters_json)
        except json.JSONDecodeError as exc:
            raise typer.BadParameter(f"Invalid JSON for --filters-json: {exc}") from exc
    else:
        filters = {
            "groups": [
                {
                    "properties": [],
                    "rollout_percentage": rollout_percentage,
                },
            ],
        }

    payload: dict[str, object] = {
        "key": key,
        "name": name,
        "description": description,
        "active": active,
        "filters": filters,
    }

    data = client.post("/feature_flags/", data=payload)
    data["_filters_json"] = json.dumps(data.get("filters", {}), indent=2)

    if is_json_mode():
        print_json(data)
    else:
        print_success(f"Feature flag '{data.get('key', key)}' created (ID {data.get('id', '?')}).")
        print_detail(data, _DETAIL_FIELDS)


@app.command("update")
def update_flag(
    flag_id: Annotated[
        int,
        typer.Argument(help="The ID of the feature flag to update."),
    ],
    name: Annotated[
        str | None,
        typer.Option("--name", help="New name."),
    ] = None,
    description: Annotated[
        str | None,
        typer.Option("--description", help="New description."),
    ] = None,
    active: Annotated[
        bool | None,
        typer.Option("--active/--no-active", help="Set active state."),
    ] = None,
    rollout_percentage: Annotated[
        int | None,
        typer.Option("--rollout-percentage", help="New rollout percentage (0-100)."),
    ] = None,
    filters_json: Annotated[
        str | None,
        typer.Option("--filters-json", help="Raw JSON string for advanced filters."),
    ] = None,
) -> None:
    """Update an existing feature flag."""
    payload: dict[str, object] = {}

    if name is not None:
        payload["name"] = name
    if description is not None:
        payload["description"] = description
    if active is not None:
        payload["active"] = active
    if filters_json is not None:
        try:
            payload["filters"] = json.loads(filters_json)
        except json.JSONDecodeError as exc:
            raise typer.BadParameter(f"Invalid JSON for --filters-json: {exc}") from exc
    if rollout_percentage is not None and filters_json is None:
        # Fetch current filters so we only update the rollout percentage.
        current = client.get(f"/feature_flags/{flag_id}/")
        default = {"groups": [{"properties": [], "rollout_percentage": 100}]}
        filters = current.get("filters", default)
        groups = filters.get("groups", [])
        if groups:
            groups[0]["rollout_percentage"] = rollout_percentage
        else:
            groups.append({"properties": [], "rollout_percentage": rollout_percentage})
        filters["groups"] = groups
        payload["filters"] = filters

    if not payload:
        raise typer.BadParameter("No update options provided. Pass at least one option to update.")

    data = client.patch(f"/feature_flags/{flag_id}/", data=payload)
    data["_filters_json"] = json.dumps(data.get("filters", {}), indent=2)

    if is_json_mode():
        print_json(data)
    else:
        print_success(f"Feature flag {flag_id} updated.")
        print_detail(data, _DETAIL_FIELDS)


@app.command("delete")
def delete_flag(
    flag_id: Annotated[
        int,
        typer.Argument(help="The ID of the feature flag to delete."),
    ],
) -> None:
    """Delete a feature flag."""
    if not confirm(f"Delete feature flag {flag_id}? This cannot be undone."):
        raise typer.Abort()

    client.delete(f"/feature_flags/{flag_id}/")

    if is_json_mode():
        print_json({"deleted": True, "id": flag_id})
    else:
        print_success(f"Feature flag {flag_id} deleted.")
