"""Query commands — run HogQL and natural language queries."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Annotated

import typer

from posthog_cli import client
from posthog_cli.output import console, is_json_mode, print_json

app = typer.Typer(help="Run queries against PostHog data.")


@app.command("run")
def run_query(
    query_json: Annotated[
        str | None,
        typer.Option("--query", help="Query as JSON string (InsightVizNode or HogQL)."),
    ] = None,
    hogql: Annotated[
        str | None,
        typer.Option("--hogql", help="Raw HogQL SQL query to execute."),
    ] = None,
    from_file: Annotated[
        Path | None,
        typer.Option("--from-file", help="Path to a JSON file containing the query."),
    ] = None,
) -> None:
    """Execute a query against PostHog data.

    Provide exactly one of --query, --hogql, or --from-file.
    """
    sources = sum(1 for s in [query_json, hogql, from_file] if s is not None)
    if sources != 1:
        raise typer.BadParameter("Provide exactly one of --query, --hogql, or --from-file.")

    if hogql:
        payload = {
            "kind": "HogQLQuery",
            "query": hogql,
        }
    elif from_file:
        payload = json.loads(from_file.read_text())
    else:
        assert query_json is not None
        payload = json.loads(query_json)

    result = client.post("/query/", data={"query": payload})

    if is_json_mode():
        print_json(result)
    else:
        # Try to print tabular results if possible
        _print_query_results(result)


@app.command("generate")
def generate_query(
    question: Annotated[str, typer.Argument(help="Natural language question about your data.")],
) -> None:
    """Generate and run a HogQL query from a natural language question."""
    result = client.post(
        "/query/",
        data={
            "query": {
                "kind": "HogQLAutocomplete",
                "query": question,
            }
        },
    )

    # The natural language -> HogQL endpoint
    # Try the AI query generation endpoint
    result = client.post(
        "/query/draft_sql/",
        data={"prompt": question},
    )

    if is_json_mode():
        print_json(result)
    else:
        sql = result.get("sql") or result.get("query") or result.get("hogql")
        if sql:
            console.print("[bold]Generated HogQL:[/bold]")
            console.print(sql)
            console.print()

            if typer.confirm("Run this query?"):
                query_result = client.post(
                    "/query/",
                    data={"query": {"kind": "HogQLQuery", "query": sql}},
                )
                _print_query_results(query_result)
        else:
            print_json(result)


def _print_query_results(result: dict) -> None:  # type: ignore[type-arg]
    """Pretty-print query results."""
    columns = result.get("columns", [])
    results_data = result.get("results", [])

    if not results_data:
        console.print("No results.")
        return

    if columns and isinstance(results_data, list) and isinstance(results_data[0], list):
        # Tabular results
        from rich.table import Table

        table = Table()
        for col in columns:
            table.add_column(str(col))
        for row in results_data[:100]:  # cap display at 100 rows
            table.add_row(*[str(v) for v in row])
        console.print(table)
        total = len(results_data)
        if total > 100:
            console.print(f"... and {total - 100} more rows (use --json for full output)")
    else:
        print_json(result)
