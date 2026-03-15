# PostHog CLI

[![CI](https://github.com/nelsongallardo/posthog-cli/actions/workflows/ci.yml/badge.svg)](https://github.com/nelsongallardo/posthog-cli/actions/workflows/ci.yml)
[![PyPI version](https://img.shields.io/pypi/v/phog-cli)](https://pypi.org/project/phog-cli/)
[![Python](https://img.shields.io/pypi/pyversions/phog-cli)](https://pypi.org/project/phog-cli/)
[![License: MIT](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)
[![Downloads](https://img.shields.io/pypi/dm/phog-cli)](https://pypi.org/project/phog-cli/)

> **Note:** This is an independent, community-built project. It is **not** affiliated with, endorsed by, or maintained by [PostHog Inc.](https://posthog.com) For PostHog's official CLI, see [posthog/posthog/cli](https://github.com/PostHog/posthog/tree/master/cli).

A full-featured command-line interface for [PostHog](https://posthog.com) — the open-source product analytics platform. Manage feature flags, experiments, surveys, dashboards, insights, error tracking, logs, and more, all from your terminal.

Built with AI agents in mind: every command supports `--json` output, `--yes` for non-interactive use, and a raw `posthog api` escape hatch for anything the CLI doesn't cover yet.

## Why?

PostHog's official CLI focuses on event capture, sourcemaps, and a handful of endpoints. This CLI covers the **full product management surface** — everything you can do in the PostHog UI, you can do here:

- Feature flags with rollout controls
- A/B experiments with results
- Surveys with response stats
- Dashboards and insights
- Error tracking
- Log querying
- HogQL queries and natural language query generation
- Person, group, event, and property search
- One-command product analytics summary

## Installation

### From source (recommended for now)

```bash
git clone https://github.com/nelsongallardo/posthog-cli.git
cd posthog-cli
python -m venv .venv
source .venv/bin/activate
pip install -e .
```

### From PyPI

```bash
pip install phog-cli
```

## Quick Start

```bash
# 1. Authenticate (auto-detects US/EU cloud)
posthog auth login

# 2. Pick your project
posthog project list
posthog project switch <project-id>

# 3. Get a full product health report
posthog activity summary
```

## Authentication

### Interactive login

```bash
posthog auth login
```

You'll be prompted for your [Personal API Key](https://posthog.com/docs/api#personal-api-keys). The CLI auto-detects whether your account is on US or EU cloud. For self-hosted instances, pass `--host`:

```bash
posthog auth login --host https://posthog.yourcompany.com
```

### Environment variables

For CI/CD, scripts, or AI agent workflows:

```bash
export POSTHOG_API_KEY="phx_..."
export POSTHOG_HOST="https://us.posthog.com"     # or https://eu.posthog.com
export POSTHOG_PROJECT_ID="12345"
```

### Auth status

```bash
posthog auth status
posthog auth logout
```

## Commands

### Overview

| Command | Description |
|---------|-------------|
| `posthog auth` | Login, logout, check auth status |
| `posthog org` | List and inspect organizations |
| `posthog project` | List, switch, and inspect projects |
| `posthog flag` | Create, list, update, delete feature flags |
| `posthog experiment` | Manage A/B experiments and view results |
| `posthog survey` | Create, manage surveys and view response stats |
| `posthog dashboard` | Manage dashboards and their tiles |
| `posthog insight` | Create, manage, and query saved insights |
| `posthog error` | Browse and manage error tracking issues |
| `posthog log` | Query logs with filters |
| `posthog query` | Run HogQL queries or generate SQL from natural language |
| `posthog search` | Search persons, groups, events, and properties |
| `posthog activity` | Quick analytics — active users, top events, product summary |
| `posthog api` | Raw API escape hatch (GET, POST, PATCH, DELETE) |

Every command supports `--help` for detailed usage.

### Activity & Analytics

```bash
# Full product health report (auto-discovers your events)
posthog activity summary
posthog activity summary --date-from -90d

# Active users
posthog activity users                          # weekly active users
posthog activity users --period daily
posthog activity users --period monthly

# Top events by volume
posthog activity events --date-from -30d

# Pageview trends
posthog activity pageviews --date-from -7d --interval day
```

The `activity summary` command runs 8 queries in parallel and returns: WAU trends, all custom events with unique user counts, weekly trend breakdowns, traffic sources, top pages, and browser stats. One command, full product context.

### Feature Flags

```bash
# List all flags
posthog flag list
posthog flag list --active           # only active flags

# Create a flag
posthog flag create \
  --key new-checkout \
  --name "New Checkout Flow" \
  --rollout-percentage 50

# Update rollout
posthog flag update <id> --rollout-percentage 100

# Get details
posthog flag get <id>

# Delete
posthog flag delete <id>
```

### Experiments

```bash
# List experiments
posthog experiment list

# Create a draft
posthog experiment create \
  --name "Button Color Test" \
  --feature-flag-key button-color

# Launch / end
posthog experiment update <id> --launch
posthog experiment update <id> --end

# View results
posthog experiment results <id>
posthog experiment results <id> --refresh

# Delete
posthog experiment delete <id>
```

### Surveys

```bash
# List surveys
posthog survey list

# Create from inline JSON
posthog survey create \
  --name "NPS Survey" \
  --questions-json '[{"type": "rating", "question": "How likely are you to recommend us?", "scale": 10}]'

# Create from a file
posthog survey create --name "Feedback" --from-file survey.json

# Launch / stop
posthog survey update <id> --start
posthog survey update <id> --stop

# View response stats
posthog survey stats <id>

# Delete
posthog survey delete <id>
```

### Dashboards

```bash
posthog dashboard list
posthog dashboard get <id>
posthog dashboard create --name "KPIs"
posthog dashboard add-insight <dashboard-id> --insight-id <insight-id>
posthog dashboard delete <id>
```

### Insights

```bash
posthog insight list
posthog insight get <id>
posthog insight query <id>              # execute the insight's saved query
posthog insight query <id> --refresh    # force refresh
posthog insight delete <id>
```

### Error Tracking

```bash
posthog error list
posthog error list --status active --search "TypeError"
posthog error get <issue-id>
posthog error update <issue-id> --status resolved
```

### Logs

```bash
posthog log query --date-from -1d
posthog log attributes                  # list available log attributes
```

### Queries (HogQL)

```bash
# Run a HogQL query
posthog query run --hogql "SELECT event, count() FROM events GROUP BY event ORDER BY count() DESC LIMIT 10"

# Run from a JSON file (InsightVizNode format)
posthog query run --from-file my-query.json

# Generate HogQL from natural language
posthog query generate "show me the top 10 countries by pageviews"
```

### Search

```bash
posthog search persons --search "john@example.com"
posthog search events --search "checkout"
posthog search groups
posthog search properties
```

### Raw API Access

For anything the CLI doesn't cover yet:

```bash
posthog api get /surveys/
posthog api post /query/ --data '{"query": {"kind": "HogQLQuery", "query": "SELECT 1"}}'
posthog api patch /feature_flags/123/ --data '{"active": false}'
posthog api delete /feature_flags/123/
```

All `api` commands use the active project context and output raw JSON.

## Global Options

```bash
posthog --json <command>     # Machine-readable JSON output
posthog --yes <command>      # Skip all confirmation prompts
posthog --version            # Show version
posthog --help               # Show help
```

### Designed for AI Agents

The `--json` and `--yes` flags make this CLI composable and safe for automated workflows:

```bash
# AI agent workflow: get flag list as JSON, pipe to jq
posthog --json flag list | jq '.[] | select(.active) | .key'

# Non-interactive: delete without confirmation prompt
posthog --yes flag delete 123

# Full product context for an AI agent in one call
posthog --json activity summary
```

## Configuration

Credentials are stored at `~/.config/posthog-cli/config.json` with `600` file permissions. The config file contains:

- `api_key` — your PostHog Personal API Key
- `host` — API host (e.g., `https://eu.posthog.com`)
- `project_id` — currently active project

Environment variables (`POSTHOG_API_KEY`, `POSTHOG_HOST`, `POSTHOG_PROJECT_ID`) take precedence over the config file.

## Development

```bash
git clone https://github.com/nelsongallardo/posthog-cli.git
cd posthog-cli
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"

# Lint
ruff check src/

# Type check
mypy src/

# Test
pytest
```

## Tech Stack

- [Typer](https://typer.tiangolo.com/) — CLI framework
- [httpx](https://www.python-httpx.org/) — HTTP client
- [Rich](https://rich.readthedocs.io/) — Terminal formatting
- [Pydantic](https://docs.pydantic.dev/) — Data validation

## Acknowledgments

This is an independent, community-driven project built on top of the [PostHog](https://posthog.com) REST API. It is not officially affiliated with or endorsed by PostHog Inc.

PostHog is an open-source product analytics platform that provides event tracking, feature flags, A/B testing, surveys, session replay, and more. Thanks to the PostHog team for building an incredible platform and providing a comprehensive, well-documented API that makes community tools like this possible.

- [PostHog Website](https://posthog.com)
- [PostHog GitHub](https://github.com/PostHog/posthog)
- [PostHog API Documentation](https://posthog.com/docs/api)

## License

MIT — see [LICENSE](LICENSE) for details.
