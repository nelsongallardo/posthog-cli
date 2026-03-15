"""Commands for managing PostHog surveys."""

from __future__ import annotations

import json
from datetime import datetime, timezone
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

app = typer.Typer(help="Manage surveys.")


@app.command("list")
def list_surveys(
    limit: Annotated[int, typer.Option(help="Maximum number of surveys to return.")] = 100,
) -> None:
    """List all surveys."""
    data = client.get("/surveys/", params={"limit": limit})
    results = data.get("results", [])

    print_table(
        results,
        [
            ("ID", "id"),
            ("Name", "name"),
            ("Type", "type"),
            ("Start Date", "start_date"),
            ("End Date", "end_date"),
            ("Archived", "archived"),
        ],
    )


@app.command()
def get(
    survey_id: Annotated[str, typer.Argument(help="The survey ID.")],
) -> None:
    """Get a survey by ID."""
    data = client.get(f"/surveys/{survey_id}/")

    # Serialize the questions list to a JSON string for display.
    if not is_json_mode():
        questions = data.get("questions")
        if questions is not None:
            data = {**data, "questions": json.dumps(questions, default=str)}

    print_detail(
        data,
        [
            ("ID", "id"),
            ("Name", "name"),
            ("Description", "description"),
            ("Type", "type"),
            ("Questions", "questions"),
            ("Start Date", "start_date"),
            ("End Date", "end_date"),
            ("Created At", "created_at"),
            ("Archived", "archived"),
        ],
    )


@app.command()
def create(
    name: Annotated[str, typer.Option(help="Name of the survey.")] = ...,  # type: ignore[assignment]
    questions_json: Annotated[
        str | None,
        typer.Option(help="JSON string containing an array of question objects."),
    ] = None,
    from_file: Annotated[
        Path | None,
        typer.Option(help="Path to a JSON file with the full survey payload."),
    ] = None,
    description: Annotated[
        str | None,
        typer.Option(help="Description of the survey."),
    ] = None,
    type: Annotated[
        str,
        typer.Option(help="Survey type (popover, api, widget)."),
    ] = "popover",
) -> None:
    """Create a new survey from a JSON file or inline JSON."""
    if from_file and questions_json:
        typer.echo("Error: --from-file and --questions-json are mutually exclusive.", err=True)
        raise typer.Exit(code=1)

    if from_file:
        try:
            payload = json.loads(from_file.read_text())
        except (json.JSONDecodeError, OSError) as exc:
            typer.echo(f"Error reading file: {exc}", err=True)
            raise typer.Exit(code=1)
        # Allow the --name flag to override the name in the file payload.
        payload["name"] = name
    elif questions_json:
        try:
            questions = json.loads(questions_json)
        except json.JSONDecodeError as exc:
            typer.echo(f"Error parsing --questions-json: {exc}", err=True)
            raise typer.Exit(code=1)

        payload: dict[str, Any] = {  # type: ignore[no-redef]
            "name": name,
            "type": type,
            "questions": questions,
        }
        if description is not None:
            payload["description"] = description
    else:
        typer.echo("Error: either --questions-json or --from-file is required.", err=True)
        raise typer.Exit(code=1)

    data = client.post("/surveys/", data=payload)

    if is_json_mode():
        print_json(data)
    else:
        print_success(f"Survey created: {data.get('id')}")


@app.command()
def update(
    survey_id: Annotated[str, typer.Argument(help="The survey ID.")],
    name: Annotated[str | None, typer.Option(help="New name for the survey.")] = None,
    description: Annotated[
        str | None,
        typer.Option(help="New description for the survey."),
    ] = None,
    start: Annotated[
        bool,
        typer.Option("--start", help="Launch the survey now by setting start_date."),
    ] = False,
    stop: Annotated[
        bool,
        typer.Option("--stop", help="Stop the survey now by setting end_date."),
    ] = False,
    data_json: Annotated[
        str | None,
        typer.Option(help="Raw JSON string for arbitrary fields to update."),
    ] = None,
) -> None:
    """Update an existing survey."""
    payload: dict[str, Any] = {}

    if name is not None:
        payload["name"] = name
    if description is not None:
        payload["description"] = description
    if start:
        payload["start_date"] = datetime.now(timezone.utc).isoformat()
    if stop:
        payload["end_date"] = datetime.now(timezone.utc).isoformat()

    if data_json is not None:
        try:
            extra = json.loads(data_json)
        except json.JSONDecodeError as exc:
            typer.echo(f"Error parsing --data-json: {exc}", err=True)
            raise typer.Exit(code=1)
        payload.update(extra)

    if not payload:
        typer.echo("Error: no update fields provided.", err=True)
        raise typer.Exit(code=1)

    data = client.patch(f"/surveys/{survey_id}/", data=payload)

    if is_json_mode():
        print_json(data)
    else:
        print_success(f"Survey updated: {survey_id}")


@app.command()
def stats(
    survey_id: Annotated[str, typer.Argument(help="The survey ID.")],
    date_from: Annotated[
        str | None,
        typer.Option(help="Start date in ISO format (e.g. 2024-01-01)."),
    ] = None,
    date_to: Annotated[
        str | None,
        typer.Option(help="End date in ISO format (e.g. 2024-12-31)."),
    ] = None,
) -> None:
    """Get survey response statistics."""
    params: dict[str, str] = {}
    if date_from is not None:
        params["date_from"] = date_from
    if date_to is not None:
        params["date_to"] = date_to

    data = client.get(f"/surveys/{survey_id}/stats/", params=params or None)

    if is_json_mode():
        print_json(data)
    else:
        print_json(data)


@app.command()
def delete(
    survey_id: Annotated[str, typer.Argument(help="The survey ID.")],
) -> None:
    """Delete a survey by ID."""
    if not confirm(f"Delete survey {survey_id}?"):
        raise typer.Abort()

    client.delete(f"/surveys/{survey_id}/")

    if is_json_mode():
        print_json({"deleted": True, "id": survey_id})
    else:
        print_success(f"Survey deleted: {survey_id}")
