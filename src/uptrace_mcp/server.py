"""MCP server for Uptrace observability platform."""

import logging
import os
import sys
from datetime import datetime, timedelta
from typing import Any, Dict, Optional

from dotenv import load_dotenv
from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import (
    Tool,
    TextContent,
    INTERNAL_ERROR,
    INVALID_PARAMS,
)

from .client import UptraceClient, UptraceClientError

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


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
        raise ValueError(f"Invalid datetime format: {value}. Use ISO format (YYYY-MM-DDTHH:MM:SSZ)") from e


def format_span_summary(span: Any) -> str:
    """
    Format span into a readable summary.

    Args:
        span: Span object

    Returns:
        Formatted string summary
    """
    attrs = span.attrs or {}
    service = attrs.get("service_name", "unknown")
    duration_ms = round(span.duration / 1000, 2) if span.duration else 0

    lines = [
        f"### Span: {span.display_name}",
        f"- **Trace ID**: {span.trace_id}",
        f"- **Span ID**: {span.id}",
        f"- **Service**: {service}",
        f"- **Status**: {span.status_code}",
        f"- **Duration**: {duration_ms}ms",
        f"- **Type**: {span.type} ({span.kind})",
    ]

    if span.status_message:
        lines.append(f"- **Error**: {span.status_message}")

    # Add HTTP details if available
    if "http_method" in attrs:
        http_info = f"{attrs['http_method']} {attrs.get('http_target', attrs.get('http_url', ''))}"
        lines.append(f"- **HTTP**: {http_info}")
        if "http_status_code" in attrs:
            lines.append(f"- **HTTP Status**: {attrs['http_status_code']}")

    # Add error details if present
    if span.events:
        for event in span.events:
            if "exception" in event.name.lower():
                exc_msg = event.attrs.get("exception_message", "N/A")
                exc_type = event.attrs.get("exception_type", "N/A")
                lines.append(f"- **Exception**: {exc_type}: {exc_msg}")

    return "\n".join(lines)


def create_uptrace_client() -> UptraceClient:
    """
    Create Uptrace client from environment variables.

    Returns:
        Configured UptraceClient instance

    Raises:
        ValueError: If required environment variables are missing
    """
    base_url = os.getenv("UPTRACE_URL")
    project_id = os.getenv("UPTRACE_PROJECT_ID")
    api_token = os.getenv("UPTRACE_API_TOKEN")

    if not base_url:
        raise ValueError("UPTRACE_URL environment variable is required")
    if not project_id:
        raise ValueError("UPTRACE_PROJECT_ID environment variable is required")
    if not api_token:
        raise ValueError("UPTRACE_API_TOKEN environment variable is required")

    logger.info(f"Initializing Uptrace client for {base_url} (project: {project_id})")
    return UptraceClient(base_url=base_url, project_id=project_id, api_token=api_token)


# Create MCP server
app = Server("uptrace-mcp")


@app.list_tools()
async def list_tools() -> list[Tool]:
    """List available MCP tools."""
    return [
        Tool(
            name="get_error_spans",
            description="Get spans with error status within a time range. Returns detailed error information including traces, services, and error messages.",
            inputSchema={
                "type": "object",
                "properties": {
                    "hours": {
                        "type": "integer",
                        "description": "Number of hours to look back (default: 3)",
                        "default": 3,
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Maximum number of spans to return (default: 100)",
                        "default": 100,
                    },
                },
            },
        ),
        Tool(
            name="get_spans",
            description="Query spans with custom filters using Uptrace Query Language (UQL). Supports WHERE clauses, filters, and aggregations.",
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
                        "description": "UQL query string (e.g., 'where service_name = \"aktar\"')",
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Maximum number of spans to return (default: 100)",
                        "default": 100,
                    },
                },
                "required": ["time_gte", "time_lt"],
            },
        ),
        Tool(
            name="get_trace",
            description="Get all spans for a specific trace ID. Useful for debugging and understanding request flows.",
            inputSchema={
                "type": "object",
                "properties": {
                    "trace_id": {
                        "type": "string",
                        "description": "Trace ID to retrieve",
                    },
                },
                "required": ["trace_id"],
            },
        ),
        Tool(
            name="query_groups",
            description="Query and aggregate spans by groups. Supports GROUP BY operations and aggregations like count(), avg(), p99(), etc.",
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
            name="get_services",
            description="Get list of services that have reported spans. Useful for discovering available services in the system.",
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
    ]


@app.call_tool()
async def call_tool(name: str, arguments: Any) -> list[TextContent]:
    """Handle tool calls."""
    try:
        client = create_uptrace_client()

        if name == "get_error_spans":
            hours = arguments.get("hours", 3)
            limit = arguments.get("limit", 100)

            time_lt = datetime.utcnow()
            time_gte = time_lt - timedelta(hours=hours)

            logger.info(f"Fetching error spans for last {hours} hours (limit: {limit})")
            response = client.get_error_spans(time_gte=time_gte, time_lt=time_lt, limit=limit)

            if not response.spans:
                return [
                    TextContent(
                        type="text",
                        text=f"No error spans found in the last {hours} hours.",
                    )
                ]

            # Format response
            lines = [
                f"# Error Spans Report",
                f"**Time Range**: {time_gte.isoformat()} - {time_lt.isoformat()}",
                f"**Total Errors**: {response.count}",
                f"**Returned**: {len(response.spans)}",
                "",
            ]

            # Group by service
            by_service: Dict[str, int] = {}
            for span in response.spans:
                service = span.attrs.get("service_name", "unknown")
                by_service[service] = by_service.get(service, 0) + 1

            lines.append("## Errors by Service")
            for service, count in sorted(by_service.items(), key=lambda x: x[1], reverse=True):
                lines.append(f"- **{service}**: {count}")
            lines.append("")

            # List spans
            lines.append("## Error Details")
            lines.append("")
            for span in response.spans[:20]:  # Limit to first 20 for readability
                lines.append(format_span_summary(span))
                lines.append("")

            if len(response.spans) > 20:
                lines.append(f"*... and {len(response.spans) - 20} more errors*")

            return [TextContent(type="text", text="\n".join(lines))]

        elif name == "get_spans":
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

            logger.info(f"Querying spans: {query} (limit: {limit})")
            response = client.get_spans(
                time_gte=time_gte, time_lt=time_lt, query=query, limit=limit
            )

            lines = [
                f"# Spans Query Results",
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

        elif name == "get_trace":
            trace_id = arguments.get("trace_id")
            if not trace_id:
                return [TextContent(type="text", text="Error: trace_id is required")]

            logger.info(f"Fetching trace: {trace_id}")
            spans = client.get_trace(trace_id)

            if not spans:
                return [
                    TextContent(type="text", text=f"No spans found for trace ID: {trace_id}")
                ]

            lines = [
                f"# Trace: {trace_id}",
                f"**Total Spans**: {len(spans)}",
                "",
            ]

            # Build tree structure
            spans_by_id = {span.id: span for span in spans}
            root_spans = [s for s in spans if not s.parent_id or s.parent_id == "0"]

            def format_tree(span: Any, indent: int = 0) -> None:
                prefix = "  " * indent + ("└─ " if indent > 0 else "")
                duration_ms = round(span.duration / 1000, 2) if span.duration else 0
                status = "❌" if span.status_code == "error" else "✓"
                lines.append(
                    f"{prefix}{status} {span.display_name} ({duration_ms}ms) [{span.id}]"
                )

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

        elif name == "query_groups":
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

        elif name == "get_services":
            hours = arguments.get("hours", 24)
            time_lt = datetime.utcnow()
            time_gte = time_lt - timedelta(hours=hours)

            logger.info(f"Fetching services for last {hours} hours")
            services = client.get_services(time_gte=time_gte, time_lt=time_lt)

            lines = [
                f"# Services",
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


def main() -> None:
    """Run the MCP server."""
    import asyncio

    logger.info("Starting Uptrace MCP server")

    # Verify environment variables
    try:
        create_uptrace_client()
    except ValueError as e:
        logger.error(f"Configuration error: {e}")
        sys.exit(1)

    # Run server
    asyncio.run(stdio_server(app))


if __name__ == "__main__":
    main()
