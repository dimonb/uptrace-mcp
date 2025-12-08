# Uptrace MCP Server

Model Context Protocol (MCP) server for [Uptrace](https://uptrace.dev) observability platform. Provides tools for querying traces, spans, and errors through Claude Desktop or other MCP clients.

## Features

- 🔍 **Query error spans** - Get detailed error information with traces and stack traces
- 📊 **Query spans** - Filter and search spans using Uptrace Query Language (UQL)
- 🔗 **Trace visualization** - Get full trace trees with all related spans
- 📈 **Aggregations** - Group and aggregate spans by services, operations, etc.
- 🏷️ **Service discovery** - List all services reporting telemetry data

## Installation

### Prerequisites

- Python 3.10 or higher
- Poetry (recommended) or pip
- Uptrace instance (self-hosted or cloud)

### Using Poetry (recommended)

```bash
cd uptrace-mcp
poetry install
```

### Using pip

```bash
pip install -e .
```

## Configuration

Create a `.env` file in the project root or set environment variables:

```bash
UPTRACE_URL=https://uptrace.finlab.team
UPTRACE_PROJECT_ID=3
UPTRACE_API_TOKEN=your_token_here
```

### Getting your Uptrace API token

1. Log in to your Uptrace instance
2. Go to your user profile
3. Navigate to "Auth Tokens" section
4. Create a new token with read access

**Note**: User auth tokens do not work with Single Sign-On (SSO). If using SSO, create a separate user account with API access.

## Usage

### As MCP Server

Add to your Claude Desktop config (`~/Library/Application Support/Claude/claude_desktop_config.json` on macOS):

```json
{
  "mcpServers": {
    "uptrace": {
      "command": "poetry",
      "args": ["run", "uptrace-mcp"],
      "cwd": "/Users/your-username/work/pet/uptrace-mcp",
      "env": {
        "UPTRACE_URL": "https://uptrace.finlab.team",
        "UPTRACE_PROJECT_ID": "3",
        "UPTRACE_API_TOKEN": "your_token_here"
      }
    }
  }
}
```

Restart Claude Desktop and the Uptrace tools will be available.

### Running Directly

```bash
# Using poetry
poetry run uptrace-mcp

# Or if installed with pip
uptrace-mcp
```

## Available Tools

### `get_error_spans`

Get spans with error status within a time range.

**Parameters:**
- `hours` (optional): Number of hours to look back (default: 3)
- `limit` (optional): Maximum spans to return (default: 100)

**Example:**
```
Get error spans from the last 6 hours
```

### `get_spans`

Query spans with custom filters using UQL.

**Parameters:**
- `time_gte` (required): Start time in ISO format (YYYY-MM-DDTHH:MM:SSZ)
- `time_lt` (required): End time in ISO format (YYYY-MM-DDTHH:MM:SSZ)
- `query` (optional): UQL query string
- `limit` (optional): Maximum spans to return (default: 100)

**Example:**
```
Get spans where service_name = "aktar" and http_status_code = 404
from 2025-12-08T09:00:00Z to 2025-12-08T10:00:00Z
```

### `get_trace`

Get all spans for a specific trace ID.

**Parameters:**
- `trace_id` (required): Trace ID to retrieve

**Example:**
```
Get trace with ID 301015e15d95f1ea12af767ebf0ffcca
```

### `query_groups`

Query and aggregate spans by groups.

**Parameters:**
- `time_gte` (required): Start time in ISO format
- `time_lt` (required): End time in ISO format
- `query` (required): UQL query with grouping
- `limit` (optional): Maximum groups to return (default: 100)

**Example:**
```
Group spans by service_name and count errors
from 2025-12-08T09:00:00Z to 2025-12-08T10:00:00Z
query: "where _status_code = 'error' | group by service_name | count()"
```

### `get_services`

Get list of services that have reported spans.

**Parameters:**
- `hours` (optional): Number of hours to look back (default: 24)

**Example:**
```
Get all services from the last 48 hours
```

## UQL Query Examples

Uptrace uses a SQL-like query language. Here are some examples:

### Filter by status
```
where _status_code = "error"
```

### Filter by service and time
```
where service_name = "aktar" and _dur_ms > 1000
```

### HTTP errors
```
where _system = "httpserver" and http_status_code >= 400
```

### Group and aggregate
```
group by service_name | count() | avg(_dur_ms)
```

### Complex query
```
where _status_code = "error" and service_name in ("aktar", "gravipay")
| group by service_name, _name
| select service_name, _name, count(), p99(_dur_ms)
```

## Development

### Running tests

```bash
poetry run pytest
```

### Code formatting

```bash
poetry run black src/
poetry run ruff check src/
```

### Type checking

```bash
poetry run mypy src/
```

## Architecture

```
uptrace-mcp/
├── src/
│   └── uptrace_mcp/
│       ├── __init__.py
│       ├── server.py      # MCP server with tool handlers
│       ├── client.py      # Uptrace API client
│       └── models.py      # Pydantic data models
├── tests/                 # Test suite
├── pyproject.toml        # Poetry configuration
└── README.md
```

## Troubleshooting

### Connection Issues

If you get connection errors:
1. Verify `UPTRACE_URL` is correct and includes protocol (https://)
2. Check that `UPTRACE_PROJECT_ID` is a valid number
3. Ensure `UPTRACE_API_TOKEN` is valid and not expired

### Permission Errors

If you get 403 Forbidden errors:
- Verify the token has access to the specified project
- Check if SSO is enabled (requires separate API user account)

### No Data Returned

If queries return no data:
- Check the time range is correct (use UTC timezone)
- Verify spans exist in that time period via Uptrace UI
- Try a broader query without filters first

## API Documentation

For more information about Uptrace API and UQL syntax, see:
- [Uptrace Query Language](https://uptrace.dev/features/querying/spans)
- [Uptrace API](https://uptrace.dev/features/json-api)

## License

MIT

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.
