"""MCP server for Uptrace observability platform."""

import logging
import argparse
import os
import sys
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional

import yaml
from dotenv import load_dotenv
from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import (
    Tool,
    TextContent,
)

from .client import UptraceClient, UptraceClientError

# Load environment variables
load_dotenv()

# Configure logging
# Set MCP server logging to WARNING to reduce noise in Cursor logs
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# Reduce verbosity of MCP server internal logging
mcp_logger = logging.getLogger("mcp.server")
mcp_logger.setLevel(logging.WARNING)


def parse_datetime(value: str) -> datetime:
    """
    Parse datetime from ISO format string.

    Args:
        value: ISO format datetime string

    Returns:
        Parsed datetime object

    Raises:
        ValueError: If datetime string is invalid
    """
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as e:
        raise ValueError(
            f"Invalid datetime format: {value}. Use ISO format (YYYY-MM-DDTHH:MM:SSZ)"
        ) from e


def format_span_summary(span: Any) -> str:
    """
    Format span into a readable summary.

    Args:
        span: Span object

    Returns:
        Formatted string summary
    """
    attrs = span.attrs or {}
    duration_ms = round(span.duration / 1000, 2) if span.duration else 0

    lines = [
        f"### Span: {span.display_name}",
        f"- **Trace ID**: {span.trace_id}",
        f"- **Span ID**: {span.id}",
        f"- **Status**: {span.status_code}",
        f"- **Duration**: {duration_ms}ms",
        f"- **Type**: {span.type} ({span.kind})",
    ]

    if span.status_message:
        lines.append(f"- **Error**: {span.status_message}")

    # Add all attributes
    if attrs:
        lines.append("")
        lines.append("#### Attributes:")
        import json

        for key in sorted(attrs.keys()):
            value = attrs[key]
            try:
                if isinstance(value, (dict, list)):
                    value_str = json.dumps(value, ensure_ascii=False, indent=2)
                else:
                    value_str = str(value)
                lines.append(f"- **{key}**: ```json\n{value_str}\n```")
            except (TypeError, ValueError):
                value_str = str(value)
                lines.append(f"- **{key}**: `{value_str}`")

    return "\n".join(lines)


def create_uptrace_client(config_path: Optional[str] = None) -> UptraceClient:
    """
    Create Uptrace client from environment variables or a YAML configuration file.

    Args:
        config_path: Optional path to a YAML configuration file. If provided, values
                     from the file will override environment variables.

    Returns:
        Configured UptraceClient instance

    Raises:
        ValueError: If required configuration is missing
    """
    # Start with environment variables
    base_url = os.getenv("UPTRACE_URL", "").strip()
    project_id = os.getenv("UPTRACE_PROJECT_ID", "").strip()
    api_token = os.getenv("UPTRACE_API_TOKEN", "").strip()

    # Override with YAML config if provided
    if config_path:
        if not os.path.exists(config_path):
            raise ValueError(f"Configuration file not found: {config_path}")

        try:
            with open(config_path, "r") as f:
                config = yaml.safe_load(f)

            uptrace_config = config.get("uptrace", {})
            if "api_url" in uptrace_config:
                base_url = str(uptrace_config["api_url"]).strip()
            if "project_id" in uptrace_config:
                project_id = str(uptrace_config["project_id"]).strip()
            if "api_token" in uptrace_config:
                api_token = str(uptrace_config["api_token"]).strip()
        except yaml.YAMLError as e:
            raise ValueError(f"Invalid YAML in configuration file: {e}")
        except Exception as e:
            raise ValueError(f"Error reading configuration file: {e}")

    if not base_url:
        raise ValueError(
            "UPTRACE_URL environment variable or uptrace.api_url in config is required"
        )
    if not project_id:
        raise ValueError(
            "UPTRACE_PROJECT_ID environment variable or uptrace.project_id in config is required"
        )
    if not api_token:
        raise ValueError(
            "UPTRACE_API_TOKEN environment variable or uptrace.api_token in config is required"
        )

    logger.info("Initializing Uptrace client for %s (project: %s)", base_url, project_id)
    return UptraceClient(base_url=base_url, project_id=project_id, api_token=api_token)


# Global client to handle tool calls
_uptrace_client: Optional[UptraceClient] = None

# Create MCP server
app = Server("uptrace-mcp")


@app.list_tools()  # type: ignore
async def list_tools() -> list[Tool]:
    """List available MCP tools."""
    return [
        Tool(
            name="uptrace_search_spans",
            description="Search spans with custom filters using Uptrace Query Language (UQL). Supports WHERE clauses, filters, and aggregations. Use 'where _status_code = \"error\"' to find error spans.",
            inputSchema={
                "type": "object",
                "properties": {
                    "time_gte": {
                        "type": "string",
                        "description": "Start time in ISO format (YYYY-MM-DDTHH:MM:SSZ)",
                    },
                    "time_lt": {
                        "type": "string",
                        "description": "End time in ISO format (YYYY-MM-DDTHH:MM:SSZ)",
                    },
                    "query": {
                        "type": "string",
                        "description": "UQL query string (e.g., 'where service_name = \"aktar\"' or 'where _status_code = \"error\"')",
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Maximum number of spans to return (default: 100)",
                        "default": 100,
                    },
                    "format": {
                        "type": "string",
                        "enum": ["text", "json"],
                        "description": "Output format: 'text' for human-readable format, 'json' for structured JSON with all attributes",
                        "default": "text",
                    },
                },
                "required": ["time_gte", "time_lt"],
            },
        ),
        Tool(
            name="uptrace_get_trace",
            description="Get all spans for a specific trace ID. Useful for debugging and understanding request flows.",
            inputSchema={
                "type": "object",
                "properties": {
                    "trace_id": {
                        "type": "string",
                        "description": "Trace ID to retrieve",
                    },
                    "format": {
                        "type": "string",
                        "enum": ["text", "json"],
                        "description": "Output format: 'text' for human-readable format, 'json' for structured JSON with all attributes",
                        "default": "text",
                    },
                },
                "required": ["trace_id"],
            },
        ),
        Tool(
            name="uptrace_search_groups",
            description="Search and aggregate spans by groups. Supports GROUP BY operations and aggregations like count(), avg(), p99(), etc.",
            inputSchema={
                "type": "object",
                "properties": {
                    "time_gte": {
                        "type": "string",
                        "description": "Start time in ISO format (YYYY-MM-DDTHH:MM:SSZ)",
                    },
                    "time_lt": {
                        "type": "string",
                        "description": "End time in ISO format (YYYY-MM-DDTHH:MM:SSZ)",
                    },
                    "query": {
                        "type": "string",
                        "description": "UQL query with grouping (e.g., 'group by service_name | count()')",
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Maximum number of groups to return (default: 100)",
                        "default": 100,
                    },
                },
                "required": ["time_gte", "time_lt", "query"],
            },
        ),
        Tool(
            name="uptrace_search_services",
            description="Search for services that have reported spans. Useful for discovering available services in the system.",
            inputSchema={
                "type": "object",
                "properties": {
                    "hours": {
                        "type": "integer",
                        "description": "Number of hours to look back (default: 24)",
                        "default": 24,
                    },
                },
            },
        ),
        Tool(
            name="uptrace_search_logs",
            description="Search logs by text, severity, service name, or custom UQL query. Logs are represented as spans with _system = 'log:all'.",
            inputSchema={
                "type": "object",
                "properties": {
                    "hours": {
                        "type": "integer",
                        "description": "Number of hours to look back (default: 3)",
                        "default": 3,
                    },
                    "search_text": {
                        "type": "string",
                        "description": "Text to search for in log messages (case-insensitive)",
                    },
                    "severity": {
                        "type": "string",
                        "description": "Filter by log severity (e.g., 'ERROR', 'WARN', 'INFO', 'DEBUG')",
                        "enum": ["DEBUG", "INFO", "WARN", "ERROR", "FATAL"],
                    },
                    "service_name": {
                        "type": "string",
                        "description": "Filter by service name",
                    },
                    "query": {
                        "type": "string",
                        "description": "Additional UQL query string for advanced filtering",
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Maximum number of logs to return (default: 100)",
                        "default": 100,
                    },
                },
            },
        ),
        Tool(
            name="uptrace_get_query_syntax",
            description="Get UQL (Uptrace Query Language) syntax documentation. Returns operators, functions, examples, and common patterns for querying spans, logs, and metrics.",
            inputSchema={
                "type": "object",
                "properties": {},
            },
        ),
        Tool(
            name="uptrace_get_alert",
            description="Get details of a specific alert incident by ID.",
            inputSchema={
                "type": "object",
                "properties": {
                    "alert_id": {
                        "type": "string",
                        "description": "ID of the alert incident to retrieve",
                    },
                },
                "required": ["alert_id"],
            },
        ),
        Tool(
            name="uptrace_list_monitors",
            description="List all alerting monitors. Returns monitor IDs, names, types, and configuration.",
            inputSchema={
                "type": "object",
                "properties": {},
            },
        ),
        Tool(
            name="uptrace_get_monitor",
            description="Get details of a specific monitor by ID.",
            inputSchema={
                "type": "object",
                "properties": {
                    "monitor_id": {
                        "type": "string",
                        "description": "ID of the monitor to retrieve",
                    },
                },
                "required": ["monitor_id"],
            },
        ),
        Tool(
            name="uptrace_list_dashboards",
            description="List all dashboards. Returns dashboard IDs and names.",
            inputSchema={
                "type": "object",
                "properties": {},
            },
        ),
        Tool(
            name="uptrace_query_metrics",
            description="Query metrics using UQL/PromQL-compatible syntax. Use this to retrieve metric values like CPU usage, request rates, etc.",
            inputSchema={
                "type": "object",
                "properties": {
                    "time_gte": {
                        "type": "string",
                        "description": "Start time in ISO format (YYYY-MM-DDTHH:MM:SSZ)",
                    },
                    "time_lt": {
                        "type": "string",
                        "description": "End time in ISO format (YYYY-MM-DDTHH:MM:SSZ)",
                    },
                    "metrics": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "List of metric definitions with aliases (e.g., ['system_cpu_utilization as $cpu'])",
                    },
                    "query": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "List of query expressions (e.g., ['avg($cpu) as cpu_avg'])",
                    },
                    "group_by": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Optional list of attributes to group by",
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Maximum number of results (default: 100)",
                        "default": 100,
                    },
                },
                "required": ["time_gte", "time_lt", "metrics", "query"],
            },
        ),
    ]


@app.call_tool()  # type: ignore
async def call_tool(name: str, arguments: Any) -> list[TextContent]:
    """Handle tool calls."""
    try:
        global _uptrace_client
        if _uptrace_client is None:
            # Fallback for environments where the client wasn't initialized
            _uptrace_client = create_uptrace_client()

        client = _uptrace_client

        if name == "uptrace_search_spans":
            try:
                time_gte = parse_datetime(arguments["time_gte"])
                time_lt = parse_datetime(arguments["time_lt"])
            except (KeyError, ValueError) as e:
                return [
                    TextContent(
                        type="text",
                        text=f"Error: {str(e)}",
                    )
                ]

            query = arguments.get("query")
            limit = arguments.get("limit", 100)
            output_format = arguments.get("format", "text")  # "text" or "json"

            logger.info(f"Querying spans: {query} (limit: {limit}, format: {output_format})")
            response = client.get_spans(
                time_gte=time_gte, time_lt=time_lt, query=query, limit=limit
            )

            # Return JSON format if requested
            if output_format == "json":
                import json

                # Convert spans to dict with all attributes
                spans_data = []
                for span in response.spans:
                    span_dict = {
                        "id": span.id,
                        "parent_id": span.parent_id,
                        "trace_id": span.trace_id,
                        "project_id": span.project_id,
                        "group_id": span.group_id,
                        "type": span.type,
                        "system": span.system,
                        "kind": span.kind,
                        "name": span.name,
                        "display_name": span.display_name,
                        "time": span.time,
                        "duration": span.duration,
                        "status_code": span.status_code,
                        "status_message": span.status_message,
                        "attrs": span.attrs or {},
                        "events": [
                            {"name": event.name, "time": event.time, "attrs": event.attrs or {}}
                            for event in span.events
                        ],
                        "links": span.links or [],
                    }
                    spans_data.append(span_dict)

                result = {
                    "query": query or None,
                    "total": response.count,
                    "returned": len(response.spans),
                    "has_more": response.has_more,
                    "spans": spans_data,
                }

                return [
                    TextContent(
                        type="text",
                        text=json.dumps(result, indent=2, ensure_ascii=False, default=str),
                    )
                ]

            # Return text format (default)
            lines = [
                "# Spans Query Results",
                f"**Query**: {query or 'none'}",
                f"**Total**: {response.count}",
                f"**Returned**: {len(response.spans)}",
                "",
            ]

            if response.spans:
                for span in response.spans[:20]:
                    lines.append(format_span_summary(span))
                    lines.append("")

                if len(response.spans) > 20:
                    lines.append(f"*... and {len(response.spans) - 20} more spans*")
            else:
                lines.append("No spans found matching the query.")

            return [TextContent(type="text", text="\n".join(lines))]

        elif name == "uptrace_get_trace":
            trace_id = arguments.get("trace_id")
            output_format = arguments.get("format", "text")  # "text" or "json"

            if not trace_id:
                return [TextContent(type="text", text="Error: trace_id is required")]

            logger.info(f"Fetching trace: {trace_id}")
            spans = client.get_trace(trace_id)

            if not spans:
                return [TextContent(type="text", text=f"No spans found for trace ID: {trace_id}")]

            # Return JSON format if requested
            if output_format == "json":
                import json

                # Convert spans to dict with all attributes
                spans_data = []
                for span in spans:
                    span_dict = {
                        "id": span.id,
                        "parent_id": span.parent_id,
                        "trace_id": span.trace_id,
                        "project_id": span.project_id,
                        "group_id": span.group_id,
                        "type": span.type,
                        "system": span.system,
                        "kind": span.kind,
                        "name": span.name,
                        "display_name": span.display_name,
                        "time": span.time,
                        "duration": span.duration,
                        "status_code": span.status_code,
                        "status_message": span.status_message,
                        "attrs": span.attrs or {},
                        "events": [
                            {"name": event.name, "time": event.time, "attrs": event.attrs or {}}
                            for event in span.events
                        ],
                        "links": span.links or [],
                    }
                    spans_data.append(span_dict)

                result = {"trace_id": trace_id, "total_spans": len(spans), "spans": spans_data}

                return [
                    TextContent(
                        type="text",
                        text=json.dumps(result, indent=2, ensure_ascii=False, default=str),
                    )
                ]

            # Return text format (default)
            lines = [
                f"# Trace: {trace_id}",
                f"**Total Spans**: {len(spans)}",
                "",
            ]

            # Build tree structure
            root_spans = [s for s in spans if not s.parent_id or s.parent_id == "0"]

            def format_tree(span: Any, indent: int = 0) -> None:
                prefix = "  " * indent + ("└─ " if indent > 0 else "")
                duration_ms = round(span.duration / 1000, 2) if span.duration else 0
                status = "❌" if span.status_code == "error" else "✓"
                lines.append(f"{prefix}{status} {span.display_name} ({duration_ms}ms) [{span.id}]")

                # Find children
                children = [s for s in spans if s.parent_id == span.id]
                for child in children:
                    format_tree(child, indent + 1)

            lines.append("## Span Tree")
            for root in root_spans:
                format_tree(root)

            lines.append("")
            lines.append("## Span Details")
            for span in spans:
                lines.append("")
                lines.append(format_span_summary(span))

            return [TextContent(type="text", text="\n".join(lines))]

        elif name == "uptrace_search_groups":
            try:
                time_gte = parse_datetime(arguments["time_gte"])
                time_lt = parse_datetime(arguments["time_lt"])
            except (KeyError, ValueError) as e:
                return [TextContent(type="text", text=f"Error: {str(e)}")]

            query = arguments.get("query")
            limit = arguments.get("limit", 100)

            if not query:
                return [TextContent(type="text", text="Error: query is required")]

            logger.info(f"Querying groups: {query}")
            result = client.query_spans_groups(
                time_gte=time_gte, time_lt=time_lt, query=query, limit=limit
            )

            import json

            return [
                TextContent(
                    type="text",
                    text=f"# Groups Query Results\n\n```json\n{json.dumps(result, indent=2)}\n```",
                )
            ]

        elif name == "uptrace_search_services":
            hours = arguments.get("hours", 24)
            time_lt = datetime.now(timezone.utc)
            time_gte = time_lt - timedelta(hours=hours)

            logger.info(f"Fetching services for last {hours} hours")
            services = client.get_services(time_gte=time_gte, time_lt=time_lt)

            lines = [
                "# Services",
                f"**Time Range**: Last {hours} hours",
                f"**Total Services**: {len(services)}",
                "",
            ]

            if services:
                lines.append("## Service List")
                for service in services:
                    lines.append(f"- {service}")
            else:
                lines.append("No services found.")

            return [TextContent(type="text", text="\n".join(lines))]

        elif name == "uptrace_search_logs":
            hours = arguments.get("hours", 3)
            search_text = arguments.get("search_text")
            severity = arguments.get("severity")
            service_name = arguments.get("service_name")
            query = arguments.get("query")
            limit = arguments.get("limit", 100)

            time_lt = datetime.now(timezone.utc)
            time_gte = time_lt - timedelta(hours=hours)

            logger.info(
                "Searching logs: text=%s, severity=%s, service=%s (limit: %s)",
                search_text,
                severity,
                service_name,
                limit,
            )

            # Build UQL query for log search
            log_query_parts = []
            if search_text:
                # Search in event attribute (which contains log message)
                log_query_parts.append(f'where event contains "{search_text}"')
            if severity:
                log_query_parts.append(f'where log_severity = "{severity}"')
            if service_name:
                log_query_parts.append(f'where service_name = "{service_name}"')
            if query:
                log_query_parts.append(query)

            # Use spans API to query logs (logs are represented as spans)
            full_query = 'where _system = "log:all"'
            if log_query_parts:
                full_query += " | " + " | ".join(log_query_parts)

            response = client.get_spans(
                time_gte=time_gte,
                time_lt=time_lt,
                query=full_query,
                limit=limit,
            )

            lines = [
                "# Logs Search Results",
                f"**Time Range**: {time_gte.isoformat()} - {time_lt.isoformat()}",
                f"**Total Logs**: {response.count}",
                f"**Returned**: {len(response.spans)}",
                "",
            ]

            if search_text:
                lines.append(f"**Search Text**: `{search_text}`")
            if severity:
                lines.append(f"**Severity**: {severity}")
            if service_name:
                lines.append(f"**Service**: {service_name}")
            lines.append("")

            if response.spans:
                # Group by severity
                by_severity: Dict[str, int] = {}
                by_service: Dict[str, int] = {}
                for span in response.spans:
                    sev = span.attrs.get("log_severity", "UNKNOWN")
                    service = span.attrs.get("service_name", "unknown")
                    by_severity[sev] = by_severity.get(sev, 0) + 1
                    by_service[service] = by_service.get(service, 0) + 1

                if by_severity:
                    lines.append("## Logs by Severity")
                    for sev, count in sorted(by_severity.items(), key=lambda x: x[1], reverse=True):
                        lines.append(f"- **{sev}**: {count}")
                    lines.append("")

                if by_service:
                    lines.append("## Logs by Service")
                    for service, count in sorted(
                        by_service.items(), key=lambda x: x[1], reverse=True
                    ):
                        lines.append(f"- **{service}**: {count}")
                    lines.append("")

                lines.append("## Log Entries")
                lines.append("")
                for span in response.spans[:20]:  # Limit to first 20 for readability
                    attrs = span.attrs or {}
                    log_severity = attrs.get("log_severity", "UNKNOWN")
                    event = attrs.get("event", "")
                    service = attrs.get("service_name", "unknown")

                    # Get log message from various possible attributes
                    # Check multiple possible attribute names for log message
                    log_message = (
                        event
                        or attrs.get("log_message", "")
                        or attrs.get("log.message", "")
                        or attrs.get("message", "")
                        or attrs.get("msg", "")
                        or attrs.get("body", "")
                        or attrs.get("text", "")
                        or ""
                    )

                    # Also check span name/display_name as it might contain the message
                    if not log_message:
                        if span.display_name and span.display_name != span.name:
                            log_message = span.display_name
                        elif span.name and span.name not in ["log", "info", "error", "warn"]:
                            log_message = span.name

                    lines.append(f"### {log_severity} - {service}")
                    lines.append(f"- **Trace ID**: {span.trace_id}")
                    lines.append(f"- **Link**: https://uptrace.finlab.team/traces/{span.trace_id}")

                    if log_message:
                        # Truncate long messages
                        message_preview = (
                            log_message[:500] + "..." if len(log_message) > 500 else log_message
                        )
                        lines.append(f"- **Message**: {message_preview}")
                    elif event:
                        # Fallback to event if log_message not available
                        event_preview = event[:500] + "..." if len(event) > 500 else event
                        lines.append(f"- **Event**: {event_preview}")

                    # Show additional useful attributes
                    if attrs.get("code_file_path"):
                        lines.append(f"- **File**: {attrs['code_file_path']}")
                    if attrs.get("code_function_name"):
                        lines.append(f"- **Function**: {attrs['code_function_name']}")
                    if attrs.get("code_line_number"):
                        lines.append(f"- **Line**: {attrs['code_line_number']}")

                    # Show exception details if available
                    if span.events:
                        for event_obj in span.events:
                            if (
                                "exception" in event_obj.name.lower()
                                or "error" in event_obj.name.lower()
                            ):
                                exc_attrs = event_obj.attrs or {}
                                exc_type = exc_attrs.get(
                                    "exception_type", exc_attrs.get("exception.type", "")
                                )
                                exc_msg = exc_attrs.get(
                                    "exception_message", exc_attrs.get("exception.message", "")
                                )
                                if exc_type or exc_msg:
                                    lines.append(f"- **Exception**: {exc_type}: {exc_msg}")

                    # Show status message if available
                    if span.status_message:
                        lines.append(f"- **Status Message**: {span.status_message}")

                    # Check span events for log messages
                    if not log_message and span.events:
                        for event_obj in span.events:
                            event_attrs = event_obj.attrs or {}
                            # Check common log message attributes in events
                            event_msg = (
                                event_attrs.get("message", "")
                                or event_attrs.get("log_message", "")
                                or event_attrs.get("msg", "")
                                or event_attrs.get("body", "")
                                or event_obj.name
                            )
                            if event_msg and event_msg not in [
                                "log",
                                "info",
                                "error",
                                "warn",
                                "debug",
                            ]:
                                log_message = event_msg
                                break

                    # Show all attributes for debugging if message still not found
                    if not log_message and not event:
                        # Show first few non-standard attributes for debugging
                        shown_attrs = 0
                        skip_keys = {
                            "service_name",
                            "log_severity",
                            "code_file_path",
                            "code_function_name",
                            "code_line_number",
                            "event",
                            "_id",
                            "_trace_id",
                            "_span_id",
                            "_parent_id",
                            "_system",
                            "_name",
                            "_duration",
                            "_time",
                        }
                        for key, value in sorted(attrs.items()):
                            if shown_attrs >= 5:
                                break
                            if key not in skip_keys:
                                val_str = str(value)
                                if len(val_str) > 0:
                                    preview = (
                                        val_str[:150] + "..." if len(val_str) > 150 else val_str
                                    )
                                    lines.append(f"- **{key}**: {preview}")
                                    shown_attrs += 1

                    # Also show display_name and name if they might contain the message
                    if not log_message:
                        if span.display_name and span.display_name not in [
                            "log",
                            "info",
                            "error",
                            "warn",
                            "debug",
                            "fatal",
                        ]:
                            lines.append(f"- **display_name**: {span.display_name[:200]}")
                        if (
                            span.name
                            and span.name not in ["log", "info", "error", "warn", "debug", "fatal"]
                            and span.name != span.display_name
                        ):
                            lines.append(f"- **name**: {span.name[:200]}")

                    lines.append("")

                if len(response.spans) > 20:
                    lines.append(f"*... and {len(response.spans) - 20} more log entries*")
            else:
                lines.append("No logs found matching the search criteria.")

            return [TextContent(type="text", text="\n".join(lines))]

        elif name == "uptrace_get_query_syntax":
            logger.info("Fetching UQL query syntax documentation")
            syntax_doc = client.get_query_syntax()

            import json

            lines = [
                "# UQL (Uptrace Query Language) Syntax Documentation",
                "",
                f"**Language**: {syntax_doc.get('language', 'UQL')}",
                f"**Description**: {syntax_doc.get('description', '')}",
                "",
            ]

            if "basic_structure" in syntax_doc:
                lines.append("## Basic Structure")
                lines.append(f"```\n{syntax_doc['basic_structure']}\n```")
                lines.append("")

            if "operators" in syntax_doc:
                lines.append("## Operators")
                for category, ops in syntax_doc["operators"].items():
                    lines.append(f"### {category.title()}")
                    for op, desc in ops.items():
                        lines.append(f"- `{op}`: {desc}")
                    lines.append("")

            if "functions" in syntax_doc:
                lines.append("## Functions")
                for func, desc in syntax_doc["functions"].items():
                    lines.append(f"- `{func}`: {desc}")
                lines.append("")

            if "examples" in syntax_doc:
                lines.append("## Examples")
                for example in syntax_doc["examples"]:
                    lines.append(f"```\n{example}\n```")
                    lines.append("")

            if "common_patterns" in syntax_doc:
                lines.append("## Common Patterns")
                for pattern, desc in syntax_doc["common_patterns"].items():
                    lines.append(f"### {pattern}")
                    lines.append(f"{desc}")
                    lines.append("")

            return [TextContent(type="text", text="\n".join(lines))]

        elif name == "uptrace_get_alert":
            alert_id = arguments.get("alert_id")
            if not alert_id:
                return [TextContent(type="text", text="Error: alert_id is required")]

            logger.info(f"Fetching alert: {alert_id}")
            alert = client.get_alert(alert_id)

            import json

            lines = [
                f"# Alert: {alert.name}",
                f"- **ID**: {alert.id}",
                f"- **Type**: {alert.type}",
                f"- **Status**: {alert.status or 'Unknown'}",
                f"- **Created At**: {datetime.fromtimestamp(alert.created_at/1000, tz=timezone.utc).isoformat()}",
                f"- **Monitor ID**: {alert.monitor_id}",
                "",
                "## Attributes",
                f"```json\n{json.dumps(alert.attrs, indent=2)}\n```",
                "",
            ]

            if alert.events:
                lines.append("## Events")
                for event in alert.events:
                    ts = datetime.fromtimestamp(
                        event.get("createdAt", 0) / 1000, tz=timezone.utc
                    ).isoformat()
                    name = event.get("name", "Unknown")
                    lines.append(f"- **{ts}**: {name} ({event.get('status', '')})")

            return [TextContent(type="text", text="\n".join(lines))]

        elif name == "uptrace_list_monitors":
            logger.info("Listing monitors")
            monitors = client.get_monitors()

            lines = [
                "# Monitors",
                f"**Total Monitors**: {len(monitors)}",
                "",
            ]

            if monitors:
                lines.append("## Monitor List")
                for monitor in monitors:
                    lines.append(f"- **{monitor.name}** ({monitor.type}) [ID: {monitor.id}]")
            else:
                lines.append("No monitors found.")

            return [TextContent(type="text", text="\n".join(lines))]

        elif name == "uptrace_get_monitor":
            monitor_id = arguments.get("monitor_id")
            if not monitor_id:
                return [TextContent(type="text", text="Error: monitor_id is required")]

            logger.info(f"Fetching monitor: {monitor_id}")
            monitor = client.get_monitor(monitor_id)

            import json

            lines = [
                f"# Monitor: {monitor.name}",
                f"- **ID**: {monitor.id}",
                f"- **Type**: {monitor.type}",
                f"- **Notify Everyone**: {monitor.notify_everyone_by_email}",
                "",
                "## Parameters",
                f"```json\n{json.dumps(monitor.params, indent=2)}\n```",
            ]

            if monitor.team_ids:
                lines.append(f"- **Team IDs**: {monitor.team_ids}")
            if monitor.channel_ids:
                lines.append(f"- **Channel IDs**: {monitor.channel_ids}")
            if monitor.repeat_interval:
                lines.append(f"- **Repeat Interval**: {monitor.repeat_interval}")

            return [TextContent(type="text", text="\n".join(lines))]

        elif name == "uptrace_list_dashboards":
            logger.info("Listing dashboards")
            dashboards = client.get_dashboards()

            lines = [
                "# Dashboards",
                f"**Total Dashboards**: {len(dashboards)}",
                "",
            ]

            if dashboards:
                lines.append("## Dashboard List")
                for dashboard in dashboards:
                    lines.append(f"- **{dashboard.name}** [ID: {dashboard.id}]")
                    if dashboard.description:
                        lines.append(f"  {dashboard.description}")
            else:
                lines.append("No dashboards found.")

            return [TextContent(type="text", text="\n".join(lines))]

        elif name == "uptrace_query_metrics":
            try:
                time_gte = parse_datetime(arguments["time_gte"])
                time_lt = parse_datetime(arguments["time_lt"])
            except (KeyError, ValueError) as e:
                return [TextContent(type="text", text=f"Error: {str(e)}")]

            metrics = arguments.get("metrics")
            query = arguments.get("query")
            group_by = arguments.get("group_by")
            limit = arguments.get("limit", 100)

            logger.info(f"Querying metrics: {metrics}")

            if group_by:
                result = client.query_metrics_groups(
                    time_gte=time_gte,
                    time_lt=time_lt,
                    metrics=metrics,
                    query=query,
                    group_by=group_by,
                    limit=limit,
                )
            else:
                result = client.query_metrics(
                    time_gte=time_gte, time_lt=time_lt, metrics=metrics, query=query, limit=limit
                )

            import json

            return [
                TextContent(
                    type="text",
                    text=f"# Metrics Query Results\n\n```json\n{json.dumps(result, indent=2)}\n```",
                )
            ]

        else:
            return [TextContent(type="text", text=f"Unknown tool: {name}")]

    except UptraceClientError as e:
        logger.error(f"Uptrace client error: {e}")
        return [TextContent(type="text", text=f"Uptrace API error: {str(e)}")]
    except ValueError as e:
        logger.error(f"Configuration error: {e}")
        return [TextContent(type="text", text=f"Configuration error: {str(e)}")]
    except Exception as e:
        logger.error(f"Unexpected error: {e}", exc_info=True)
        return [TextContent(type="text", text=f"Unexpected error: {str(e)}")]


async def _run_server() -> None:
    """Run the MCP server async context manager."""
    async with stdio_server() as (read_stream, write_stream):
        await app.run(read_stream, write_stream, app.create_initialization_options())


def main() -> None:
    """Run the MCP server."""
    import asyncio

    parser = argparse.ArgumentParser(description="Uptrace MCP Server")
    parser.add_argument(
        "--config",
        "-c",
        type=str,
        help="Path to YAML configuration file. Overrides environment variables.",
    )

    args = parser.parse_args()

    logger.info("Starting Uptrace MCP server")

    # Verify environment variables / config loading
    try:
        global _uptrace_client
        _uptrace_client = create_uptrace_client(args.config)
    except ValueError as e:
        logger.error("Configuration error: %s", e)
        logger.error(
            "Please set UPTRACE_URL, UPTRACE_PROJECT_ID, and UPTRACE_API_TOKEN environment variables"
        )
        logger.error(
            "Or provide a YAML config file with --config: uptrace: { api_url: '...', project_id: '...', api_token: '...'}"
        )
        sys.exit(1)

    # Run server
    try:
        asyncio.run(_run_server())
    except KeyboardInterrupt:
        logger.info("Server stopped by user")
    except Exception as e:
        logger.error("Server error: %s", e, exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
