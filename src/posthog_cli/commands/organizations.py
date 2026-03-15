"""Organization management commands."""

from __future__ import annotations

import typer

from posthog_cli import client
from posthog_cli.output import print_detail, print_table

app = typer.Typer(help="Manage organizations.")


@app.command("list")
def list_orgs() -> None:
    """List all organizations you belong to."""
    data = client.get("/api/organizations/", project=False)
    rows = data.get("results", data) if isinstance(data, dict) else data
    print_table(
        rows,
        [("ID", "id"), ("Name", "name"), ("Created At", "created_at")],
    )


@app.command("get")
def get_org(
    org_id: str = typer.Argument(help="Organization ID."),
) -> None:
    """Get details of a specific organization."""
    data = client.get(f"/api/organizations/{org_id}/", project=False)
    print_detail(
        data,
        [
            ("ID", "id"),
            ("Name", "name"),
            ("Slug", "slug"),
            ("Created At", "created_at"),
            ("Members Count", "membership_count"),
        ],
    )
