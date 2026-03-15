"""Authentication commands for the PostHog CLI."""

from __future__ import annotations

import typer

from posthog_cli.config import (
    CONFIG_FILE,
    get_api_key,
    get_config_path,
    get_host,
    get_project_id,
    save_credentials,
)
from posthog_cli.output import console, print_detail, print_error, print_success

app = typer.Typer(help="Manage authentication.")


CLOUD_HOSTS = [
    "https://us.posthog.com",
    "https://eu.posthog.com",
]


def _try_auth(
    api_key: str, host: str
) -> tuple[bool, str | None, dict | None]:
    """Attempt authentication against a host.

    Returns (success, error_message, response_json).
    """
    import httpx

    try:
        resp = httpx.get(
            f"{host}/api/organizations/",
            headers={"Authorization": f"Bearer {api_key}"},
            timeout=15.0,
        )
    except httpx.HTTPError as exc:
        return False, f"Could not reach {host}: {exc}", None

    if resp.is_error:
        try:
            detail = resp.json()
            msg = (
                detail.get("detail")
                or detail.get("error")
                or str(detail)
            )
        except Exception:
            msg = resp.text
        return False, msg, None

    return True, None, resp.json()


@app.command()
def login(
    api_key: str = typer.Option(
        ...,
        prompt="Personal API key",
        hide_input=True,
        help="PostHog personal API key.",
    ),
    host: str = typer.Option(
        "",
        help="PostHog instance URL (auto-detected for cloud).",
    ),
    project_id: str = typer.Option(
        None,
        prompt="Project ID (leave blank to skip)",
        prompt_required=False,
        help="Default project ID to use.",
    ),
) -> None:
    """Authenticate with a PostHog instance."""
    api_key = api_key.strip()
    host = host.strip().rstrip("/")

    if not api_key:
        print_error("API key cannot be empty.")
        raise typer.Exit(code=1)

    pid = project_id.strip() if project_id else None

    if host:
        # Explicit host — try it directly.
        ok, err, data = _try_auth(api_key, host)
        if not ok:
            print_error(f"Authentication failed: {err}")
            raise typer.Exit(code=1)
    else:
        # No host given — auto-detect by trying each cloud region.
        console.print("Detecting PostHog region...")
        data = None
        for candidate in CLOUD_HOSTS:
            ok, err, data = _try_auth(api_key, candidate)
            if ok:
                host = candidate
                console.print(f"Found account on {host}")
                break
        else:
            print_error(
                "Could not authenticate against US or EU cloud. "
                "If you use a self-hosted instance, pass --host."
            )
            raise typer.Exit(code=1)

    save_credentials(api_key=api_key, host=host, project_id=pid or None)

    results = (data or {}).get("results") or []
    if results:
        org_name = results[0].get("name", "unknown")
        print_success(
            f"Logged in successfully. Organization: {org_name}"
        )
    else:
        print_success("Logged in successfully.")


@app.command()
def status() -> None:
    """Show the current authentication status."""
    try:
        api_key = get_api_key()
    except typer.BadParameter:
        api_key = None

    host = get_host()
    project_id = get_project_id()
    config_path = get_config_path()

    # Mask the API key, showing only the last four characters.
    if api_key:
        visible = api_key[-4:] if len(api_key) > 4 else api_key
        masked_key = f"{'*' * (len(api_key) - len(visible))}{visible}"
    else:
        masked_key = None

    info = {
        "logged_in": "Yes" if api_key else "No",
        "host": host,
        "api_key": masked_key or "Not set",
        "project_id": project_id or "Not set",
        "config_file": str(config_path),
    }

    print_detail(
        info,
        [
            ("Logged in", "logged_in"),
            ("Host", "host"),
            ("API key", "api_key"),
            ("Project ID", "project_id"),
            ("Config file", "config_file"),
        ],
    )


@app.command()
def logout() -> None:
    """Remove stored credentials."""
    if not CONFIG_FILE.exists():
        console.print("No credentials found. Already logged out.")
        return

    confirmed = typer.confirm("Remove stored credentials?")
    if not confirmed:
        console.print("Aborted.")
        raise typer.Abort()

    CONFIG_FILE.unlink()
    print_success("Credentials removed.")
