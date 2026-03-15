"""PostHog CLI — manage your PostHog instance from the command line."""

from __future__ import annotations

from typing import Annotated

import typer

from posthog_cli import __version__
from posthog_cli.commands import (
    activity,
    api,
    auth,
    dashboards,
    errors,
    experiments,
    feature_flags,
    insights,
    logs,
    organizations,
    projects,
    query,
    search,
    surveys,
)
from posthog_cli.output import set_json_mode, set_yes_mode

app = typer.Typer(
    name="posthog",
    help="PostHog CLI — manage flags, experiments, surveys, dashboards, and more.",
    no_args_is_help=True,
)


def _version_callback(value: bool) -> None:
    if value:
        typer.echo(f"posthog-cli {__version__}")
        raise typer.Exit()


@app.callback()
def main(
    version: Annotated[
        bool | None,
        typer.Option(
            "--version", "-v",
            help="Show version and exit.",
            callback=_version_callback,
            is_eager=True,
        ),
    ] = None,
    json_output: Annotated[
        bool,
        typer.Option("--json", "-j", help="Output results as JSON."),
    ] = False,
    yes: Annotated[
        bool,
        typer.Option("--yes", "-y", help="Skip confirmation prompts."),
    ] = False,
) -> None:
    """PostHog CLI — manage your PostHog instance from the command line."""
    set_json_mode(json_output)
    set_yes_mode(yes)


# Register command groups
app.add_typer(activity.app, name="activity")
app.add_typer(auth.app, name="auth")
app.add_typer(organizations.app, name="org")
app.add_typer(projects.app, name="project")
app.add_typer(feature_flags.app, name="flag")
app.add_typer(experiments.app, name="experiment")
app.add_typer(surveys.app, name="survey")
app.add_typer(dashboards.app, name="dashboard")
app.add_typer(insights.app, name="insight")
app.add_typer(errors.app, name="error")
app.add_typer(logs.app, name="log")
app.add_typer(query.app, name="query")
app.add_typer(search.app, name="search")
app.add_typer(api.app, name="api")


if __name__ == "__main__":
    app()
