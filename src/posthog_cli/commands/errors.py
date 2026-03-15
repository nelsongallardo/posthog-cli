"""Error tracking commands."""

from __future__ import annotations

from typing import Annotated

import typer

from posthog_cli import client
from posthog_cli.output import is_json_mode, print_detail, print_json, print_table

app = typer.Typer(help="Manage error tracking issues.")


@app.command("list")
def list_errors(
    limit: Annotated[int, typer.Option(help="Maximum number of results.")] = 50,
    search: Annotated[str | None, typer.Option(help="Search by error message.")] = None,
    status: Annotated[
        str | None,
        typer.Option(help="Filter by status (active, resolved, archived)."),
    ] = None,
) -> None:
    """List error tracking issues."""
    params: dict[str, object] = {"limit": limit}
    if search:
        params["search"] = search
    if status:
        params["status"] = status

    data = client.get("/error_tracking/issues/", params=params)
    rows = data.get("results", []) if isinstance(data, dict) else data
    print_table(
        rows,
        [
            ("ID", "id"),
            ("Title", "name"),
            ("Status", "status"),
            ("Occurrences", "occurrences"),
            ("Users", "users"),
            ("First Seen", "first_seen"),
            ("Last Seen", "last_seen"),
        ],
    )


@app.command("get")
def get_error(
    issue_id: Annotated[str, typer.Argument(help="Error tracking issue ID.")],
) -> None:
    """Get details of an error tracking issue."""
    data = client.get(f"/error_tracking/issues/{issue_id}/")
    if is_json_mode():
        print_json(data)
    else:
        print_detail(
            data,
            [
                ("ID", "id"),
                ("Title", "name"),
                ("Description", "description"),
                ("Status", "status"),
                ("Occurrences", "occurrences"),
                ("Users", "users"),
                ("First Seen", "first_seen"),
                ("Last Seen", "last_seen"),
                ("Assignee", "assignee"),
            ],
        )


@app.command("update")
def update_error(
    issue_id: Annotated[str, typer.Argument(help="Error tracking issue ID.")],
    status: Annotated[
        str | None,
        typer.Option(help="New status (active, resolved, archived)."),
    ] = None,
    assignee: Annotated[
        str | None,
        typer.Option(help="Assign to a user ID."),
    ] = None,
) -> None:
    """Update an error tracking issue (status, assignee)."""
    payload: dict[str, object] = {}
    if status is not None:
        payload["status"] = status
    if assignee is not None:
        payload["assignee"] = assignee
    if not payload:
        raise typer.BadParameter("Provide at least one of --status or --assignee.")

    data = client.patch(f"/error_tracking/issues/{issue_id}/", data=payload)
    if data:
        from posthog_cli.output import print_success

        print_success(f"Updated issue {issue_id}.")
