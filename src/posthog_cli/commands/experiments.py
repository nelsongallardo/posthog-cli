"""Commands for managing PostHog experiments."""

from __future__ import annotations

import json
from datetime import datetime, timezone
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

app = typer.Typer(help="Manage experiments.")


@app.command("list")
def list_experiments(
    limit: Annotated[int, typer.Option(help="Maximum number of experiments to return.")] = 100,
) -> None:
    """List all experiments."""
    data = client.get("/experiments/", params={"limit": limit})
    rows = data.get("results", [])
    print_table(
        rows,
        [
            ("ID", "id"),
            ("Name", "name"),
            ("Feature Flag Key", "feature_flag_key"),
            ("Start Date", "start_date"),
            ("End Date", "end_date"),
            ("Archived", "archived"),
        ],
    )


@app.command()
def get(
    experiment_id: Annotated[int, typer.Argument(help="Experiment ID.")],
) -> None:
    """Get an experiment by ID."""
    data = client.get(f"/experiments/{experiment_id}/")
    print_detail(
        data,
        [
            ("ID", "id"),
            ("Name", "name"),
            ("Description", "description"),
            ("Feature Flag Key", "feature_flag_key"),
            ("Start Date", "start_date"),
            ("End Date", "end_date"),
            ("Archived", "archived"),
            ("Created At", "created_at"),
        ],
    )


@app.command()
def create(
    name: Annotated[str, typer.Option(help="Experiment name.")],
    feature_flag_key: Annotated[str, typer.Option(help="Feature flag key for the experiment.")],
    description: Annotated[str | None, typer.Option(help="Experiment description.")] = None,
    filters_json: Annotated[
        str | None,
        typer.Option(help="Raw JSON string for experiment parameters."),
    ] = None,
    draft: Annotated[bool, typer.Option("--draft/--no-draft", help="Create as draft.")] = True,
) -> None:
    """Create a new experiment."""
    payload: dict[str, Any] = {
        "name": name,
        "feature_flag_key": feature_flag_key,
    }

    if description is not None:
        payload["description"] = description

    if filters_json is not None:
        try:
            payload["parameters"] = json.loads(filters_json)
        except json.JSONDecodeError as exc:
            raise typer.BadParameter(f"Invalid JSON for --filters-json: {exc}") from exc

    if not draft:
        payload["start_date"] = datetime.now(timezone.utc).isoformat()

    data = client.post("/experiments/", data=payload)
    if is_json_mode():
        print_json(data)
    else:
        print_success(f"Experiment created (ID: {data['id']}).")
        print_detail(
            data,
            [
                ("ID", "id"),
                ("Name", "name"),
                ("Feature Flag Key", "feature_flag_key"),
                ("Start Date", "start_date"),
            ],
        )


@app.command()
def update(
    experiment_id: Annotated[int, typer.Argument(help="Experiment ID.")],
    name: Annotated[str | None, typer.Option(help="New experiment name.")] = None,
    description: Annotated[str | None, typer.Option(help="New description.")] = None,
    archive: Annotated[
        bool | None,
        typer.Option("--archive/--no-archive", help="Archive or unarchive."),
    ] = None,
    launch: Annotated[bool, typer.Option("--launch", help="Launch the experiment now.")] = False,
    conclude: Annotated[
        str | None,
        typer.Option(help="Conclude the experiment with a result: won, lost, or inconclusive."),
    ] = None,
) -> None:
    """Update an existing experiment."""
    payload: dict[str, Any] = {}

    if name is not None:
        payload["name"] = name
    if description is not None:
        payload["description"] = description
    if archive is not None:
        payload["archived"] = archive
    if launch:
        payload["start_date"] = datetime.now(timezone.utc).isoformat()
    if conclude is not None:
        allowed = ("won", "lost", "inconclusive")
        if conclude not in allowed:
            raise typer.BadParameter(f"--conclude must be one of: {', '.join(allowed)}")
        payload["end_date"] = datetime.now(timezone.utc).isoformat()
        payload["parameters"] = {"result": conclude}

    if not payload:
        raise typer.BadParameter("No update options provided. Use --help to see available options.")

    data = client.patch(f"/experiments/{experiment_id}/", data=payload)
    if is_json_mode():
        print_json(data)
    else:
        print_success(f"Experiment {experiment_id} updated.")
        print_detail(
            data,
            [
                ("ID", "id"),
                ("Name", "name"),
                ("Start Date", "start_date"),
                ("End Date", "end_date"),
                ("Archived", "archived"),
            ],
        )


@app.command()
def results(
    experiment_id: Annotated[int, typer.Argument(help="Experiment ID.")],
    refresh: Annotated[bool, typer.Option("--refresh", help="Force a fresh calculation.")] = False,
) -> None:
    """Get experiment results."""
    params = {}
    if refresh:
        params["refresh"] = "true"
    data = client.get(f"/experiments/{experiment_id}/results", params=params or None)
    print_json(data)


@app.command()
def delete(
    experiment_id: Annotated[int, typer.Argument(help="Experiment ID.")],
) -> None:
    """Delete an experiment."""
    if not is_json_mode():
        if not confirm(f"Delete experiment {experiment_id}? This cannot be undone."):
            raise typer.Abort()

    client.delete(f"/experiments/{experiment_id}/")
    if is_json_mode():
        print_json({"deleted": True, "id": experiment_id})
    else:
        print_success(f"Experiment {experiment_id} deleted.")
