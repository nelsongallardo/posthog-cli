"""Project management commands."""

from __future__ import annotations

import typer

from posthog_cli import client
from posthog_cli.config import get_project_id, save_project_id
from posthog_cli.output import print_detail, print_success, print_table

app = typer.Typer(help="Manage projects.")


@app.command("list")
def list_projects() -> None:
    """List all projects across your organizations."""
    data = client.get("/api/projects/", project=False)
    rows = data.get("results", data) if isinstance(data, dict) else data
    current = get_project_id()
    for row in rows:
        if str(row.get("id")) == str(current):
            row["name"] = f"{row['name']} (active)"
    print_table(
        rows,
        [
            ("ID", "id"),
            ("Name", "name"),
            ("Organization", "organization"),
            ("Created At", "created_at"),
        ],
    )


@app.command("current")
def current_project() -> None:
    """Show the currently active project."""
    pid = get_project_id()
    if not pid:
        typer.echo("No active project. Run: posthog project switch <id>")
        raise typer.Exit(code=1)
    data = client.get(f"/api/projects/{pid}/", project=False)
    print_detail(
        data,
        [
            ("ID", "id"),
            ("Name", "name"),
            ("Organization", "organization"),
            ("Created At", "created_at"),
        ],
    )


@app.command("switch")
def switch_project(
    project_id: str = typer.Argument(help="Project ID to switch to."),
) -> None:
    """Set the active project for all commands."""
    # Validate that the project exists
    client.get(f"/api/projects/{project_id}/", project=False)
    save_project_id(project_id)
    print_success(f"Switched to project {project_id}.")
