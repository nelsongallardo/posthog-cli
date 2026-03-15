"""Convenience commands for common analytics queries."""

from __future__ import annotations

import concurrent.futures
from typing import Annotated, Any

import typer

from posthog_cli import client
from posthog_cli.output import console, is_json_mode, print_json, print_table

app = typer.Typer(help="Quick analytics — active users, top events, and more.")


def _trend_query(
    event: str,
    math: str,
    date_from: str,
    interval: str,
    name: str,
) -> dict[str, Any]:
    result: dict[str, Any] = client.post(
        "/query/",
        data={
            "query": {
                "kind": "InsightVizNode",
                "source": {
                    "kind": "TrendsQuery",
                    "series": [
                        {
                            "kind": "EventsNode",
                            "event": event,
                            "custom_name": name,
                            "math": math,
                        }
                    ],
                    "dateRange": {"date_from": date_from},
                    "interval": interval,
                },
            }
        },
    )
    return result


@app.command("users")
def active_users(
    period: Annotated[
        str,
        typer.Option(
            help="Period: daily, weekly, or monthly.",
        ),
    ] = "weekly",
    date_from: Annotated[
        str, typer.Option(help="Start date (e.g. -30d, -90d).")
    ] = "-30d",
) -> None:
    """Show active users over time."""
    math_map = {
        "daily": ("dau", "day"),
        "weekly": ("weekly_active", "week"),
        "monthly": ("monthly_active", "month"),
    }
    if period not in math_map:
        raise typer.BadParameter(
            f"Invalid period '{period}'. Use: daily, weekly, monthly."
        )

    math, interval = math_map[period]
    label = f"{period.title()} Active Users"

    data = _trend_query("$pageview", math, date_from, interval, label)

    if is_json_mode():
        print_json(data)
        return

    results = data.get("results", [])
    if not results:
        console.print("No data.")
        return

    series = results[0]
    rows = [
        {"period": lbl, "active_users": str(int(val))}
        for lbl, val in zip(series["labels"], series["data"])
    ]
    print_table(
        rows,
        [("Period", "period"), (label, "active_users")],
    )


@app.command("events")
def top_events(
    date_from: Annotated[
        str, typer.Option(help="Start date (e.g. -7d, -30d).")
    ] = "-7d",
    limit: Annotated[
        int, typer.Option(help="Number of top events.")
    ] = 10,
) -> None:
    """Show top events by volume."""
    data = client.post(
        "/query/",
        data={
            "query": {
                "kind": "HogQLQuery",
                "query": (
                    "SELECT event, count() as count "
                    "FROM events "
                    f"WHERE timestamp >= now() - INTERVAL {_parse_interval(date_from)} "
                    "GROUP BY event "
                    "ORDER BY count DESC "
                    f"LIMIT {limit}"
                ),
            }
        },
    )

    if is_json_mode():
        print_json(data)
        return

    results = data.get("results", [])
    if not results:
        console.print("No events found.")
        return

    rows = [
        {"event": row[0], "count": str(row[1])} for row in results
    ]
    print_table(rows, [("Event", "event"), ("Count", "count")])


@app.command("pageviews")
def pageviews(
    date_from: Annotated[
        str, typer.Option(help="Start date (e.g. -7d, -30d).")
    ] = "-7d",
    interval: Annotated[
        str, typer.Option(help="Interval: hour, day, week, month.")
    ] = "day",
) -> None:
    """Show pageview trends."""
    data = _trend_query(
        "$pageview", "total", date_from, interval, "Pageviews"
    )

    if is_json_mode():
        print_json(data)
        return

    results = data.get("results", [])
    if not results:
        console.print("No data.")
        return

    series = results[0]
    rows = [
        {"period": lbl, "pageviews": str(int(val))}
        for lbl, val in zip(series["labels"], series["data"])
    ]
    print_table(rows, [("Period", "period"), ("Pageviews", "pageviews")])


def _parse_interval(date_from: str) -> str:
    """Convert '-30d' style to '30 DAY' for HogQL."""
    s = date_from.lstrip("-")
    if s.endswith("d"):
        return f"{s[:-1]} DAY"
    if s.endswith("w"):
        return f"{s[:-1]} WEEK"
    if s.endswith("m"):
        return f"{s[:-1]} MONTH"
    return "30 DAY"


# ── Summary command ─────────────────────────────────────────────────


def _hogql(sql: str) -> Any:
    """Execute a HogQL query and return results."""
    data = client.post(
        "/query/",
        data={"query": {"kind": "HogQLQuery", "query": sql}},
    )
    return data.get("results", [])


def _hogql_row(sql: str) -> list[Any]:
    """Execute a HogQL query expecting a single row."""
    rows = _hogql(sql)
    return rows[0] if rows else []


def _safe_pct(num: float, denom: float) -> str:
    if denom == 0:
        return "N/A"
    return f"{num / denom * 100:.1f}%"


def _build_summary(interval: str) -> dict[str, Any]:
    """Run all summary queries in parallel and return structured data."""

    queries: dict[str, str] = {}

    # 1. WAU trend
    queries["wau"] = (
        "SELECT toStartOfWeek(timestamp) as week, "
        "count(distinct person_id) as users "
        "FROM events "
        f"WHERE timestamp > now() - interval {interval} "
        "GROUP BY week ORDER BY week"
    )

    # 2. Top events by volume
    queries["top_events"] = (
        "SELECT event, count() as count "
        "FROM events "
        f"WHERE timestamp > now() - interval {interval} "
        "GROUP BY event ORDER BY count DESC LIMIT 15"
    )

    # 3. Top custom events (excluding $ prefixed)
    queries["custom_events"] = (
        "SELECT event, count() as count, "
        "count(distinct person_id) as unique_users "
        "FROM events "
        f"WHERE timestamp > now() - interval {interval} "
        "AND event NOT LIKE '$%' "
        "GROUP BY event ORDER BY count DESC LIMIT 20"
    )

    # 4. Weekly custom event trends
    queries["weekly_custom_trends"] = (
        "SELECT toStartOfWeek(timestamp) as week, event, count() as count "
        "FROM events "
        f"WHERE timestamp > now() - interval {interval} "
        "AND event NOT LIKE '$%' "
        "AND event IN ("
        "  SELECT event FROM events "
        f"  WHERE timestamp > now() - interval {interval} "
        "  AND event NOT LIKE '$%' "
        "  GROUP BY event ORDER BY count() DESC LIMIT 8"
        ") "
        "GROUP BY week, event ORDER BY week, event"
    )

    # 5. Traffic sources
    queries["traffic_sources"] = (
        "SELECT properties.$referring_domain as source, "
        "count(distinct person_id) as users "
        "FROM events "
        f"WHERE event = '$pageview' AND timestamp > now() - interval {interval} "
        "AND properties.$referring_domain IS NOT NULL "
        "AND properties.$referring_domain != '' "
        "GROUP BY source ORDER BY users DESC LIMIT 10"
    )

    # 6. Top pages
    queries["top_pages"] = (
        "SELECT properties.$current_url as page, count() as views "
        "FROM events "
        f"WHERE event = '$pageview' AND timestamp > now() - interval {interval} "
        "GROUP BY page ORDER BY views DESC LIMIT 10"
    )

    # 7. Total pageviews
    queries["pageview_total"] = (
        "SELECT count() as views, count(distinct person_id) as visitors "
        "FROM events "
        f"WHERE event = '$pageview' AND timestamp > now() - interval {interval}"
    )

    # 8. Browser breakdown
    queries["browsers"] = (
        "SELECT properties.$browser as browser, "
        "count(distinct person_id) as users "
        "FROM events "
        f"WHERE event = '$pageview' AND timestamp > now() - interval {interval} "
        "AND properties.$browser IS NOT NULL "
        "GROUP BY browser ORDER BY users DESC LIMIT 5"
    )

    # Run all queries in parallel
    results: dict[str, Any] = {}
    with concurrent.futures.ThreadPoolExecutor(max_workers=8) as pool:
        futures = {pool.submit(_hogql, sql): name for name, sql in queries.items()}
        for future in concurrent.futures.as_completed(futures):
            name = futures[future]
            try:
                results[name] = future.result()
            except Exception as exc:
                results[name] = {"error": str(exc)}

    return results


def _render_summary(results: dict[str, Any], date_range: str) -> None:
    """Render the summary as Rich output."""
    console.print()
    console.rule(f"[bold]Product Summary ({date_range})[/bold]")

    # -- Pageview totals --
    pv = results.get("pageview_total", [])
    if pv and not isinstance(pv, dict):
        row = pv[0] if pv else [0, 0]
        console.print(
            f"\n[bold cyan]Pageviews:[/bold cyan] {int(row[0]):,}  |  "
            f"[bold cyan]Unique visitors:[/bold cyan] {int(row[1]):,}"
        )

    # -- WAU trend --
    wau = results.get("wau", [])
    if wau and not isinstance(wau, dict):
        console.print()
        console.rule("[bold]Weekly Active Users[/bold]", style="dim")
        rows = [{"week": str(r[0])[:10], "users": str(int(r[1]))} for r in wau]
        print_table(rows, [("Week", "week"), ("Users", "users")])

    # -- Top custom events with unique users --
    custom = results.get("custom_events", [])
    if custom and not isinstance(custom, dict):
        console.print()
        console.rule("[bold]Custom Events (your product)[/bold]", style="dim")
        rows = [
            {
                "event": r[0],
                "count": str(int(r[1])),
                "unique_users": str(int(r[2])),
            }
            for r in custom
        ]
        print_table(
            rows,
            [("Event", "event"), ("Total", "count"), ("Unique Users", "unique_users")],
        )

    # -- Weekly trends for top custom events --
    weekly = results.get("weekly_custom_trends", [])
    if weekly and not isinstance(weekly, dict):
        console.print()
        console.rule("[bold]Weekly Trends (Top Custom Events)[/bold]", style="dim")
        # Pivot: weeks as rows, events as columns
        weeks_order: list[str] = []
        events_set: list[str] = []
        grid: dict[str, dict[str, int]] = {}
        for row in weekly:
            week = str(row[0])[:10]
            event = row[1]
            count = int(row[2])
            if week not in grid:
                grid[week] = {}
                weeks_order.append(week)
            if event not in events_set:
                events_set.append(event)
            grid[week][event] = count

        table_rows = []
        for week in weeks_order:
            r: dict[str, str] = {"week": week}
            for ev in events_set:
                r[ev] = str(grid[week].get(ev, 0))
            table_rows.append(r)

        cols: list[tuple[str, str]] = [("Week", "week")]
        for ev in events_set:
            # Shorten long event names for table headers
            label = ev if len(ev) <= 20 else ev[:18] + ".."
            cols.append((label, ev))
        print_table(table_rows, cols)

    # -- Traffic sources --
    traffic = results.get("traffic_sources", [])
    if traffic and not isinstance(traffic, dict):
        console.print()
        console.rule("[bold]Traffic Sources[/bold]", style="dim")
        rows = [
            {"source": r[0], "users": str(int(r[1]))} for r in traffic
        ]
        print_table(rows, [("Source", "source"), ("Unique Users", "users")])

    # -- Top pages --
    pages = results.get("top_pages", [])
    if pages and not isinstance(pages, dict):
        console.print()
        console.rule("[bold]Top Pages[/bold]", style="dim")
        rows = [
            {"page": r[0], "views": str(int(r[1]))} for r in pages
        ]
        print_table(rows, [("Page", "page"), ("Views", "views")])

    # -- Browser breakdown --
    browsers = results.get("browsers", [])
    if browsers and not isinstance(browsers, dict):
        console.print()
        console.rule("[bold]Browsers[/bold]", style="dim")
        rows = [
            {"browser": r[0], "users": str(int(r[1]))} for r in browsers
        ]
        print_table(rows, [("Browser", "browser"), ("Users", "users")])

    console.print()


@app.command("summary")
def summary(
    date_from: Annotated[
        str, typer.Option(help="Start date (e.g. -30d, -90d).")
    ] = "-30d",
) -> None:
    """Comprehensive product analytics summary.

    Auto-discovers your custom events and shows: WAU trends, event volumes
    with weekly breakdowns, traffic sources, top pages, and browser stats.
    Designed for AI agents to get full product context in one call.
    """
    interval = _parse_interval(date_from)

    with console.status("[bold green]Fetching analytics...[/bold green]"):
        data = _build_summary(interval)

    if is_json_mode():
        print_json(data)
        return

    _render_summary(data, date_from)
