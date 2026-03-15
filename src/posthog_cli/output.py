"""Output formatting helpers using Rich."""

from __future__ import annotations

import json
from collections.abc import Sequence
from typing import Any

import typer
from rich.console import Console
from rich.table import Table

console = Console()
err_console = Console(stderr=True)

# Global output format — set by the top-level --json flag
_json_mode = False

# Global yes mode — set by the top-level --yes flag
_yes_mode = False


def set_json_mode(enabled: bool) -> None:
    global _json_mode
    _json_mode = enabled


def is_json_mode() -> bool:
    return _json_mode


def set_yes_mode(enabled: bool) -> None:
    global _yes_mode
    _yes_mode = enabled


def is_yes_mode() -> bool:
    return _yes_mode


def print_json(data: Any) -> None:
    """Print raw JSON to stdout (for piping / scripting)."""
    typer.echo(json.dumps(data, indent=2, default=str))


def print_detail(data: dict[str, Any], fields: Sequence[tuple[str, str]]) -> None:
    """Print a single resource as key-value pairs, or JSON if --json."""
    if _json_mode:
        print_json(data)
        return
    table = Table(show_header=False, box=None, padding=(0, 2))
    table.add_column("Field", style="bold cyan", no_wrap=True)
    table.add_column("Value")
    for label, key in fields:
        val = data
        for part in key.split("."):
            if isinstance(val, dict):
                val = val.get(part, "")
            else:
                val = ""
                break
        table.add_row(label, str(val))
    console.print(table)


def print_table(
    rows: Sequence[dict[str, Any]],
    columns: Sequence[tuple[str, str]],
    *,
    title: str | None = None,
) -> None:
    """Print a list of resources as a table, or JSON if --json."""
    if _json_mode:
        print_json(rows)
        return
    table = Table(title=title, show_lines=False)
    for header, _ in columns:
        table.add_column(header)
    for row in rows:
        values: list[str] = []
        for _, key in columns:
            val = row
            for part in key.split("."):
                if isinstance(val, dict):
                    val = val.get(part, "")
                else:
                    val = ""
                    break
            values.append(str(val))
        table.add_row(*values)
    console.print(table)


def print_success(message: str) -> None:
    if not _json_mode:
        console.print(f"[green]{message}[/green]")


def print_error(message: str) -> None:
    err_console.print(f"[red]{message}[/red]")


def print_warning(message: str) -> None:
    if not _json_mode:
        err_console.print(f"[yellow]{message}[/yellow]")


def confirm(message: str) -> bool:
    if _yes_mode:
        return True
    return typer.confirm(message)
