"""CLI commands for managing PostHog insights."""

from __future__ import annotations

import json
from pathlib import Path
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

app = typer.Typer(help="Manage insights.")


# -- Column / field definitions ------------------------------------------------

_LIST_COLUMNS: list[tuple[str, str]] = [
    ("ID", "id"),
    ("Name", "name"),
    ("Description", "description"),
    ("Favorited", "favorited"),
    ("Last Modified At", "last_modified_at"),
]

_DETAIL_FIELDS: list[tuple[str, str]] = [
    ("ID", "id"),
    ("Name", "name"),
    ("Description", "description"),
    ("Favorited", "favorited"),
    ("Tags", "_tags_str"),
    ("Query", "_query_json"),
    ("Last Modified At", "last_modified_at"),
    ("Created At", "created_at"),
]


# -- Helpers -------------------------------------------------------------------

def _parse_query(query_json: str | None, from_file: Path | None) -> dict[str, Any]:
    """Parse a query object from a JSON string or a file path.

    Exactly one of *query_json* or *from_file* must be provided.
    """
    if query_json is not None and from_file is not None:
        raise typer.BadParameter("Provide either --query-json or --from-file, not both.")
    if query_json is not None:
        try:
            result: dict[str, Any] = json.loads(query_json)
            return result
        except json.JSONDecodeError as exc:
            raise typer.BadParameter(f"Invalid JSON for --query-json: {exc}") from exc
    if from_file is not None:
        try:
            result = json.loads(from_file.read_text(encoding="utf-8"))
            return result
        except json.JSONDecodeError as exc:
            raise typer.BadParameter(f"Invalid JSON in {from_file}: {exc}") from exc
        except OSError as exc:
            raise typer.BadParameter(f"Cannot read file {from_file}: {exc}") from exc
    raise typer.BadParameter("Provide --query-json or --from-file.")


def _enrich(data: dict[str, Any]) -> dict[str, Any]:
    """Add display-friendly synthetic fields to an insight dict."""
    data["_query_json"] = json.dumps(data.get("query", {}), indent=2)
    tags = data.get("tags") or []
    data["_tags_str"] = ", ".join(str(t) for t in tags) if tags else ""
    return data


# -- Commands ------------------------------------------------------------------

@app.command("list")
def list_insights(
    search: Annotated[
        str | None,
        typer.Option("--search", help="Filter insights by name."),
    ] = None,
    limit: Annotated[
        int,
        typer.Option("--limit", help="Maximum number of insights to return."),
    ] = 100,
    favorited: Annotated[
        bool,
        typer.Option("--favorited", help="Show only favorited insights."),
    ] = False,
) -> None:
    """List all insights."""
    params: dict[str, object] = {"limit": limit}
    if search is not None:
        params["search"] = search
    if favorited:
        params["favorited"] = "true"

    data = client.get("/insights/", params=params)
    results = data.get("results", data) if isinstance(data, dict) else data

    if is_json_mode():
        print_json(results)
    else:
        print_table(results, _LIST_COLUMNS)


@app.command("get")
def get_insight(
    insight_id: Annotated[
        int,
        typer.Argument(help="The ID of the insight."),
    ],
) -> None:
    """Get details of a single insight."""
    data = client.get(f"/insights/{insight_id}/")
    _enrich(data)

    if is_json_mode():
        print_json(data)
    else:
        print_detail(data, _DETAIL_FIELDS)


@app.command("create")
def create_insight(
    name: Annotated[
        str,
        typer.Option("--name", help="Name for the insight."),
    ],
    query_json: Annotated[
        str | None,
        typer.Option("--query-json", help="JSON string with the query object."),
    ] = None,
    from_file: Annotated[
        Path | None,
        typer.Option("--from-file", help="Path to a JSON file containing the query object."),
    ] = None,
    description: Annotated[
        str,
        typer.Option("--description", help="Description for the insight."),
    ] = "",
    favorited: Annotated[
        bool,
        typer.Option("--favorited/--no-favorited", help="Mark the insight as favorited."),
    ] = False,
    tags: Annotated[
        str | None,
        typer.Option("--tags", help="Comma-separated list of tags."),
    ] = None,
) -> None:
    """Create a new insight from a query definition."""
    query = _parse_query(query_json, from_file)
    tag_list = [t.strip() for t in tags.split(",") if t.strip()] if tags else []

    payload: dict[str, object] = {
        "name": name,
        "description": description,
        "favorited": favorited,
        "query": query,
        "tags": tag_list,
    }

    data = client.post("/insights/", data=payload)
    _enrich(data)

    if is_json_mode():
        print_json(data)
    else:
        print_success(f"Insight '{data.get('name', name)}' created (ID {data.get('id', '?')}).")
        print_detail(data, _DETAIL_FIELDS)


@app.command("update")
def update_insight(
    insight_id: Annotated[
        int,
        typer.Argument(help="The ID of the insight to update."),
    ],
    name: Annotated[
        str | None,
        typer.Option("--name", help="New name."),
    ] = None,
    description: Annotated[
        str | None,
        typer.Option("--description", help="New description."),
    ] = None,
    favorited: Annotated[
        bool | None,
        typer.Option("--favorited/--no-favorited", help="Set favorited state."),
    ] = None,
    query_json: Annotated[
        str | None,
        typer.Option("--query-json", help="New query as a JSON string."),
    ] = None,
    tags: Annotated[
        str | None,
        typer.Option("--tags", help="Comma-separated list of tags."),
    ] = None,
) -> None:
    """Update an existing insight."""
    payload: dict[str, object] = {}

    if name is not None:
        payload["name"] = name
    if description is not None:
        payload["description"] = description
    if favorited is not None:
        payload["favorited"] = favorited
    if query_json is not None:
        try:
            payload["query"] = json.loads(query_json)
        except json.JSONDecodeError as exc:
            raise typer.BadParameter(f"Invalid JSON for --query-json: {exc}") from exc
    if tags is not None:
        payload["tags"] = [t.strip() for t in tags.split(",") if t.strip()]

    if not payload:
        raise typer.BadParameter("No update options provided. Pass at least one option to update.")

    data = client.patch(f"/insights/{insight_id}/", data=payload)
    _enrich(data)

    if is_json_mode():
        print_json(data)
    else:
        print_success(f"Insight {insight_id} updated.")
        print_detail(data, _DETAIL_FIELDS)


@app.command("query")
def query_insight(
    insight_id: Annotated[
        int,
        typer.Argument(help="The ID of the insight whose query to execute."),
    ],
) -> None:
    """Execute an existing insight's query and print the results."""
    insight = client.get(f"/insights/{insight_id}/")
    query = insight.get("query")
    if not query:
        raise typer.BadParameter(f"Insight {insight_id} has no query defined.")

    data = client.post("/query/", data={"query": query})
    print_json(data)


@app.command("delete")
def delete_insight(
    insight_id: Annotated[
        int,
        typer.Argument(help="The ID of the insight to delete."),
    ],
) -> None:
    """Delete an insight."""
    if not is_json_mode():
        if not confirm(f"Delete insight {insight_id}? This cannot be undone."):
            raise typer.Abort()

    client.delete(f"/insights/{insight_id}/")

    if is_json_mode():
        print_json({"deleted": True, "id": insight_id})
    else:
        print_success(f"Insight {insight_id} deleted.")
