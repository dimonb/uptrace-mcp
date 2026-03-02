# Uptrace MCP Server

Model Context Protocol (MCP) server for [Uptrace](https://uptrace.dev) observability platform. Provides tools for querying traces, spans, and errors through Claude Desktop or other MCP clients.

## Features

- 🔍 **Query error spans** - Get detailed error information with traces and stack traces
- 📊 **Query spans** - Filter and search spans using Uptrace Query Language (UQL)
- 🔗 **Trace visualization** - Get full trace trees with all related spans
- 📈 **Aggregations** - Group and aggregate spans by services, operations, etc.
- 📝 **Query logs** - Search and filter logs by severity, service, and custom UQL queries
- 📉 **Query metrics** - Query metrics using PromQL-compatible syntax
- 🏷️ **Service discovery** - List all services reporting telemetry data
- 📚 **Query syntax documentation** - Get comprehensive UQL syntax reference

## Installation

### Prerequisites

- Python 3.10 or higher
- Poetry (recommended) or pip
- Uptrace instance (self-hosted or cloud)

### Using uv (recommended)

```bash
uvx --from . uptrace-mcp
```

### Using pip

```bash
pip install -e .
```

## Configuration

Create a `.env` file in the project root or set environment variables:

```bash
UPTRACE_URL=https://uptrace.xxx
UPTRACE_PROJECT_ID=3
UPTRACE_API_TOKEN=your_token_here
```

You can also use a YAML file for configuration by passing the `--config` parameter.
```yaml
# config.yaml
uptrace:
  api_url: "https://uptrace.example.com"
  project_id: "1"
  api_token: "your-api-token"
logging:
  level: "DEBUG"
  file: "/path/to/uptrace-mcp.log"
```

The `logging` section is optional. By default, the server logs to standard error (`stderr`) at the `INFO` level.

### Getting your Uptrace API token

1. Log in to your Uptrace instance
2. Go to your user profile
3. Navigate to "Auth Tokens" section
4. Create a new token with read access

**Note**: User auth tokens do not work with Single Sign-On (SSO). If using SSO, create a separate user account with API access.

## Usage

### As MCP Server

#### Cursor IDE

📖 **Detailed setup guide**: See [CURSOR_SETUP.md](CURSOR_SETUP.md) for comprehensive instructions.

To add this MCP server to Cursor:

1. Open Cursor Settings (Cmd+, on macOS or Ctrl+, on Windows/Linux)
2. Search for "MCP" or navigate to **Features** → **Model Context Protocol**
3. Click **Edit Config** or open the MCP configuration file directly

The configuration file location:
- **macOS**: `~/Library/Application Support/Cursor/User/globalStorage/saoudrizwan.claude-dev/settings/cline_mcp_settings.json`
- **Windows**: `%APPDATA%\Cursor\User\globalStorage\saoudrizwan.claude-dev\settings\cline_mcp_settings.json`
- **Linux**: `~/.config/Cursor/User/globalStorage/saoudrizwan.claude-dev\settings\cline_mcp_settings.json`

**Quick setup**: You can use the example configuration file `cursor-mcp-config.json.example` as a template. Copy it to your Cursor MCP settings file and update the paths and credentials.

**Important**: The `cwd` parameter specifies the working directory where the command will be executed. This must be the root directory of your `uptrace-mcp` project (where `pyproject.toml` is located).

Add the following configuration (replace the paths with your actual project paths):

```json
{
  "mcpServers": {
    "uptrace": {
      "command": "uvx",
      "args": ["--from", "/path/to/uptrace-mcp", "uptrace-mcp"],
      "env": {
        "UPTRACE_URL": "https://uptrace.xxx",
        "UPTRACE_PROJECT_ID": "3",
        "UPTRACE_API_TOKEN": "your_token_here"
      }
    }
  }
}
```

Or using a config file:

```json
{
  "mcpServers": {
    "uptrace": {
      "command": "uvx",
      "args": ["--from", "/path/to/uptrace-mcp", "uptrace-mcp", "--config", "/path/to/config.yaml"]
    }
  }
}
```

**Configuration parameters:**
- `command` - Should be `uvx`
- `args` - Arguments passed to the command (`["--from", "project_path", "uptrace-mcp"]`)
- `env` - Environment variables for the server (can be omitted if using `--config`)

After saving the configuration, restart Cursor. The Uptrace tools will be available in the MCP tools panel.

#### Claude Desktop

Add to your Claude Desktop config (`~/Library/Application Support/Claude/claude_desktop_config.json` on macOS):

```json
{
  "mcpServers": {
    "uptrace": {
      "command": "uvx",
      "args": ["--from", "/Users/your-username/work/pet/uptrace-mcp", "uptrace-mcp"],
      "env": {
        "UPTRACE_URL": "https://uptrace.xxx",
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
# Using uv
uv run uptrace-mcp

# Or if installed with pip
uptrace-mcp

# With config
uv run uptrace-mcp --config config.yaml
```

## Available Tools

### Spans & Traces

#### `uptrace_search_spans`

Search spans with custom filters using UQL. Use `where _status_code = "error"` to find error spans.

**Parameters:**
- `time_gte` (required): Start time in ISO format (YYYY-MM-DDTHH:MM:SSZ)
- `time_lt` (required): End time in ISO format (YYYY-MM-DDTHH:MM:SSZ)
- `query` (optional): UQL query string
- `limit` (optional): Maximum spans to return (default: 100)

**Examples:**
```
Search spans where service_name = "aktar" and http_status_code = 404
from 2025-12-08T09:00:00Z to 2025-12-08T10:00:00Z

Find error spans: where _status_code = "error"
from 2025-12-08T09:00:00Z to 2025-12-08T10:00:00Z
```

#### `uptrace_get_trace`

Get all spans for a specific trace ID.

**Parameters:**
- `trace_id` (required): Trace ID to retrieve

**Example:**
```
Get trace with ID 301015e15d95f1ea12af767ebf0ffcca
```

#### `uptrace_search_groups`

Search and aggregate spans by groups.

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

#### `uptrace_search_services`

Search for services that have reported spans.

**Parameters:**
- `hours` (optional): Number of hours to look back (default: 24)

**Example:**
```
Search for all services from the last 48 hours
```

### Logs

#### `uptrace_search_logs`

Search logs by text, severity, service name, or custom UQL query.

**Parameters:**
- `hours` (optional): Number of hours to look back (default: 3)
- `search_text` (optional): Text to search for in log messages (case-insensitive)
- `severity` (optional): Filter by log severity (DEBUG, INFO, WARN, ERROR, FATAL)
- `service_name` (optional): Filter by service name
- `query` (optional): Additional UQL query string for advanced filtering
- `limit` (optional): Maximum number of logs to return (default: 100)

**Examples:**
```
Search logs containing "error" from the last 3 hours
Search ERROR level logs from service "aktar" in the last 6 hours
```

### Documentation

#### `uptrace_get_query_syntax`

Get UQL (Uptrace Query Language) syntax documentation. Returns operators, functions, examples, and common patterns for querying spans, logs, and metrics.

**Parameters:**
- None

**Example:**
```
Get UQL query syntax documentation
```

### Logs

The client provides methods for querying logs (logs are represented as spans with `_system = "log:all"`):

- `query_logs()` - Query logs with filters by severity, service name, and custom UQL queries
- `get_error_logs()` - Get error logs (ERROR and FATAL severity levels)

**Example usage:**
```python
from datetime import datetime, timedelta
from uptrace_mcp.client import UptraceClient

client = UptraceClient(
    base_url="https://uptrace.xxx",
    project_id="3",
    api_token="your_token"
)

# Get error logs from the last hour
time_lt = datetime.utcnow()
time_gte = time_lt - timedelta(hours=1)

logs = client.get_error_logs(time_gte=time_gte, time_lt=time_lt, limit=100)

# Query logs with custom filters
logs = client.query_logs(
    time_gte=time_gte,
    time_lt=time_lt,
    severity="ERROR",
    service_name="my-service",
    query='where log_message contains "database"',
    limit=50
)
```

### Metrics

The client provides methods for querying metrics using PromQL-compatible syntax:

- `query_metrics()` - Query metrics with PromQL-compatible format
- `query_metrics_groups()` - Query and aggregate metrics by groups

**Example usage:**
```python
# Query metrics
result = client.query_metrics(
    time_gte=datetime.utcnow() - timedelta(hours=1),
    time_lt=datetime.utcnow(),
    metrics=["system_cpu_utilization as $cpu"],
    query=["avg($cpu) as cpu_avg"]
)

# Query metrics with grouping
result = client.query_metrics_groups(
    time_gte=datetime.utcnow() - timedelta(hours=1),
    time_lt=datetime.utcnow(),
    metrics=["uptrace_tracing_spans as $spans"],
    query=["sum($spans) as total_spans"],
    group_by=["service_name"]
)
```

### Additional Span Methods

The client also provides additional convenience methods for working with spans:

- `get_span_by_id()` - Get a specific span by its ID
- `get_spans_by_parent()` - Get child spans by parent span ID
- `get_spans_by_system()` - Filter spans by system type (http, db, rpc, etc.)
- `get_slow_spans()` - Get spans exceeding a duration threshold
- `get_query_syntax()` - Get comprehensive UQL syntax documentation

**Example:**
```python
# Get query syntax documentation
syntax = client.get_query_syntax()
print(syntax["operators"])
print(syntax["aggregation_functions"])
print(syntax["examples"])
```

## UQL Query Examples

Uptrace uses a SQL-like query language (UQL). You can get comprehensive syntax documentation using `client.get_query_syntax()`. Here are some examples:

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

### Log queries
```
where _system = "log:all" and log_severity in ("ERROR", "FATAL")
| group by service_name
| select service_name, count()
```

### Metrics queries
```
metrics:
  - system_cpu_utilization as $cpu
query:
  - avg($cpu) as cpu_avg
  - sum($cpu) by (service_name) as cpu_by_service
```

## Python Client API

The MCP server uses the `UptraceClient` class internally. You can also use it directly in your Python code:

```python
from datetime import datetime, timedelta
from uptrace_mcp.client import UptraceClient

client = UptraceClient(
    base_url="https://uptrace.xxx",
    project_id="3",
    api_token="your_token"
)

# Query spans
spans = client.get_spans(
    time_gte=datetime.utcnow() - timedelta(hours=1),
    time_lt=datetime.utcnow(),
    query='where _status_code = "error"',
    limit=100
)

# Query logs
logs = client.query_logs(
    time_gte=datetime.utcnow() - timedelta(hours=1),
    time_lt=datetime.utcnow(),
    severity="ERROR",
    limit=50
)

# Query metrics
metrics = client.query_metrics(
    time_gte=datetime.utcnow() - timedelta(hours=1),
    time_lt=datetime.utcnow(),
    metrics=["uptrace_tracing_spans as $spans"],
    query=["sum($spans) as total"]
)

# Get query syntax documentation
syntax = client.get_query_syntax()
```

See `examples/query_errors.py` for more examples.

## Development

### Running tests

```bash
uv run pytest
```

### Code formatting

```bash
uv run black src/
uv run ruff check src/
```

### Type checking

```bash
uv run mypy src/
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

### MCP Server Not Found in Cursor

If you see "No server info found" error in Cursor:

1. **Verify the configuration file path** - Make sure you're editing the correct MCP settings file:
   - macOS: `~/Library/Application Support/Cursor/User/globalStorage/saoudrizwan.claude-dev/settings/cline_mcp_settings.json`
   - Windows: `%APPDATA%\Cursor\User\globalStorage\saoudrizwan.claude-dev\settings\cline_mcp_settings.json`
   - Linux: `~/.config/Cursor/User/globalStorage/saoudrizwan.claude-dev/settings/cline_mcp_settings.json`

2. **Check file permissions** - Ensure the configuration file is valid JSON and readable

3. **Verify uv/Python path** - Test the command manually:
   ```bash
   cd /path/to/uptrace-mcp
   uv run uptrace-mcp --help
   ```

4. **Check environment variables** - Make sure all required variables are set in the `env` section, or a `--config` string is specified:
   - `UPTRACE_URL`
   - `UPTRACE_PROJECT_ID`
   - `UPTRACE_API_TOKEN`

6. **Restart Cursor** - After making changes, completely restart Cursor (not just reload)

7. **Check Cursor logs** - Look for error messages in Cursor's developer console or logs

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

### Testing the Server Manually

1. **Check configuration:**
   ```bash
   cd /path/to/uptrace-mcp
   python check_config.py
   ```

2. **Test server startup:**
   ```bash
   export UPTRACE_URL="https://uptrace.xxx"
   export UPTRACE_PROJECT_ID="3"
   export UPTRACE_API_TOKEN="your_token"
   uv run uptrace-mcp
   ```

   The server should start without errors. Press Ctrl+C to stop it.

3. **Verify MCP protocol:**
   The server communicates via stdio, so you won't see output when run directly.
   If it starts without errors, it's working correctly.

## API Documentation

For more information about Uptrace API and UQL syntax, see:
- [Uptrace Query Language](https://uptrace.dev/features/querying/spans)
- [Uptrace API](https://uptrace.dev/features/json-api)

## License

MIT

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.
