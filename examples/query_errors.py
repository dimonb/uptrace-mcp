#!/usr/bin/env python3
"""Example: Query error spans from Uptrace."""

import os
from datetime import datetime, timedelta

from dotenv import load_dotenv

from uptrace_mcp.client import UptraceClient

# Load environment variables
load_dotenv()


def main():
    """Query and display error spans."""
    # Initialize client
    client = UptraceClient(
        base_url=os.getenv("UPTRACE_URL", "https://uptrace.xxx"),
        project_id=os.getenv("UPTRACE_PROJECT_ID", "3"),
        api_token=os.getenv("UPTRACE_API_TOKEN", ""),
    )

    # Query errors from last 3 hours
    time_lt = datetime.utcnow()
    time_gte = time_lt - timedelta(hours=3)

    print(f"Querying errors from {time_gte} to {time_lt}...")

    response = client.get_error_spans(time_gte=time_gte, time_lt=time_lt, limit=10)

    print(f"\nFound {response.count} error spans")
    print(f"Showing first {len(response.spans)} spans:\n")

    for span in response.spans:
        service = span.attrs.get("service_name", "unknown")
        duration_ms = round(span.duration / 1000, 2)

        print(f"❌ {span.display_name}")
        print(f"   Service: {service}")
        print(f"   Duration: {duration_ms}ms")
        print(f"   Trace ID: {span.trace_id}")

        if span.status_message:
            print(f"   Error: {span.status_message}")

        print()

    client.close()


if __name__ == "__main__":
    main()
