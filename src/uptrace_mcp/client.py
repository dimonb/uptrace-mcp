"""Uptrace API client."""

import logging
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional
from urllib.parse import urljoin

import requests
from pydantic import ValidationError

from .models import LogEntry, LogsResponse, Span, SpansResponse

logger = logging.getLogger(__name__)


class UptraceClientError(Exception):
    """Base exception for Uptrace client errors."""

    pass


class UptraceClient:
    """Client for interacting with Uptrace API."""

    def __init__(self, base_url: str, project_id: str, api_token: str):
        """
        Initialize Uptrace client.

        Args:
            base_url: Base URL of Uptrace instance (e.g., https://uptrace.xxx)
            project_id: Project ID
            api_token: API authentication token
        """
        # Strip whitespace and trailing slashes
        self.base_url = base_url.strip().rstrip("/")
        self.project_id = str(project_id).strip()
        self.api_token = api_token.strip()
        self.session = requests.Session()
        self.session.headers.update({"Authorization": f"Bearer {self.api_token}"})

    def _make_request(
        self, method: str, path: str, params: Optional[Dict[str, Any]] = None, **kwargs: Any
    ) -> Dict[str, Any]:
        """
        Make HTTP request to Uptrace API.

        Args:
            method: HTTP method
            path: API endpoint path
            params: Query parameters
            **kwargs: Additional arguments for requests

        Returns:
            JSON response as dictionary

        Raises:
            UptraceClientError: If request fails
        """
        url = urljoin(self.base_url, path)

        try:
            response = self.session.request(method, url, params=params, **kwargs)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.HTTPError as e:
            logger.error(f"HTTP error: {e.response.status_code} - {e.response.text}")
            raise UptraceClientError(
                f"HTTP {e.response.status_code}: {e.response.text}"
            ) from e
        except requests.exceptions.RequestException as e:
            logger.error(f"Request failed: {e}")
            raise UptraceClientError(f"Request failed: {e}") from e
        except ValueError as e:
            logger.error(f"Invalid JSON response: {e}")
            raise UptraceClientError(f"Invalid JSON response: {e}") from e

    def get_spans(
        self,
        time_gte: datetime,
        time_lt: datetime,
        query: Optional[str] = None,
        limit: int = 100,
    ) -> SpansResponse:
        """
        Get spans within time range with optional query filter.

        Args:
            time_gte: Start time (inclusive)
            time_lt: End time (exclusive)
            query: UQL query string (e.g., 'where _status_code = "error"')
            limit: Maximum number of spans to return

        Returns:
            SpansResponse with spans and metadata

        Raises:
            UptraceClientError: If request fails
        """
        path = f"/internal/v1/tracing/{self.project_id}/spans"

        params: Dict[str, Any] = {
            "time_gte": time_gte.strftime("%Y-%m-%dT%H:%M:%SZ"),
            "time_lt": time_lt.strftime("%Y-%m-%dT%H:%M:%SZ"),
            "limit": limit,
        }

        if query:
            params["query"] = query

        try:
            data = self._make_request("GET", path, params=params)
            return SpansResponse(**data)
        except ValidationError as e:
            logger.error(f"Failed to parse spans response: {e}")
            raise UptraceClientError(f"Failed to parse response: {e}") from e

    def get_error_spans(
        self,
        time_gte: datetime,
        time_lt: datetime,
        limit: int = 100,
    ) -> SpansResponse:
        """
        Get spans with error status within time range.

        Args:
            time_gte: Start time (inclusive)
            time_lt: End time (exclusive)
            limit: Maximum number of spans to return

        Returns:
            SpansResponse with error spans

        Raises:
            UptraceClientError: If request fails
        """
        return self.get_spans(
            time_gte=time_gte,
            time_lt=time_lt,
            query='where _status_code = "error"',
            limit=limit,
        )

    def get_trace(
        self, trace_id: str, time_gte: Optional[datetime] = None, time_lt: Optional[datetime] = None
    ) -> List[Span]:
        """
        Get all spans for a specific trace.

        Args:
            trace_id: Trace ID
            time_gte: Start time (defaults to 24h ago)
            time_lt: End time (defaults to now)

        Returns:
            List of spans in the trace

        Raises:
            UptraceClientError: If request fails
        """
        if time_lt is None:
            time_lt = datetime.now(timezone.utc)
        if time_gte is None:
            time_gte = time_lt - timedelta(hours=24)

        response = self.get_spans(
            time_gte=time_gte,
            time_lt=time_lt,
            query=f'where _trace_id = "{trace_id}"',
            limit=1000,
        )

        return response.spans

    def get_span_by_id(
        self, span_id: str, time_gte: Optional[datetime] = None, time_lt: Optional[datetime] = None
    ) -> Optional[Span]:
        """
        Get a specific span by its ID.

        Args:
            span_id: Span ID
            time_gte: Start time (defaults to 24h ago)
            time_lt: End time (defaults to now)

        Returns:
            Span if found, None otherwise

        Raises:
            UptraceClientError: If request fails
        """
        if time_lt is None:
            time_lt = datetime.now(timezone.utc)
        if time_gte is None:
            time_gte = time_lt - timedelta(hours=24)

        response = self.get_spans(
            time_gte=time_gte,
            time_lt=time_lt,
            query=f'where _id = "{span_id}"',
            limit=1,
        )

        return response.spans[0] if response.spans else None

    def get_spans_by_parent(
        self,
        parent_id: str,
        time_gte: Optional[datetime] = None,
        time_lt: Optional[datetime] = None,
        limit: int = 100,
    ) -> SpansResponse:
        """
        Get spans by parent span ID.

        Args:
            parent_id: Parent span ID
            time_gte: Start time (defaults to 24h ago)
            time_lt: End time (defaults to now)
            limit: Maximum number of spans to return

        Returns:
            SpansResponse with child spans

        Raises:
            UptraceClientError: If request fails
        """
        if time_lt is None:
            time_lt = datetime.now(timezone.utc)
        if time_gte is None:
            time_gte = time_lt - timedelta(hours=24)

        return self.get_spans(
            time_gte=time_gte,
            time_lt=time_lt,
            query=f'where _parent_id = "{parent_id}"',
            limit=limit,
        )

    def get_spans_by_system(
        self,
        system: str,
        time_gte: datetime,
        time_lt: datetime,
        query: Optional[str] = None,
        limit: int = 100,
    ) -> SpansResponse:
        """
        Get spans filtered by system type.

        Args:
            system: System type (e.g., "http", "db", "rpc")
            time_gte: Start time (inclusive)
            time_lt: End time (exclusive)
            query: Additional UQL query string
            limit: Maximum number of spans to return

        Returns:
            SpansResponse with filtered spans

        Raises:
            UptraceClientError: If request fails
        """
        system_query = f'where _system = "{system}"'
        if query:
            full_query = f"{system_query} | {query}"
        else:
            full_query = system_query

        return self.get_spans(
            time_gte=time_gte,
            time_lt=time_lt,
            query=full_query,
            limit=limit,
        )

    def get_slow_spans(
        self,
        time_gte: datetime,
        time_lt: datetime,
        min_duration_ms: float = 1000.0,
        query: Optional[str] = None,
        limit: int = 100,
    ) -> SpansResponse:
        """
        Get spans with duration exceeding threshold.

        Args:
            time_gte: Start time (inclusive)
            time_lt: End time (exclusive)
            min_duration_ms: Minimum duration in milliseconds
            query: Additional UQL query string
            limit: Maximum number of spans to return

        Returns:
            SpansResponse with slow spans

        Raises:
            UptraceClientError: If request fails
        """
        duration_query = f'where _dur_ms > {min_duration_ms}ms'
        if query:
            full_query = f"{duration_query} | {query}"
        else:
            full_query = duration_query

        return self.get_spans(
            time_gte=time_gte,
            time_lt=time_lt,
            query=full_query,
            limit=limit,
        )

    def query_spans_groups(
        self,
        time_gte: datetime,
        time_lt: datetime,
        query: str,
        limit: int = 100,
    ) -> Dict[str, Any]:
        """
        Query span groups with aggregation.

        Args:
            time_gte: Start time (inclusive)
            time_lt: End time (exclusive)
            query: UQL query with grouping (e.g., 'group by service_name')
            limit: Maximum number of groups to return

        Returns:
            Dictionary with groups data

        Raises:
            UptraceClientError: If request fails
        """
        path = f"/internal/v1/tracing/{self.project_id}/groups"

        params: Dict[str, Any] = {
            "time_gte": time_gte.strftime("%Y-%m-%dT%H:%M:%SZ"),
            "time_lt": time_lt.strftime("%Y-%m-%dT%H:%M:%SZ"),
            "query": query,
            "limit": limit,
        }

        return self._make_request("GET", path, params=params)

    def get_services(
        self,
        time_gte: Optional[datetime] = None,
        time_lt: Optional[datetime] = None,
    ) -> List[str]:
        """
        Get list of services.

        Args:
            time_gte: Start time (defaults to 24h ago)
            time_lt: End time (defaults to now)

        Returns:
            List of service names

        Raises:
            UptraceClientError: If request fails
        """
        if time_lt is None:
            time_lt = datetime.now(timezone.utc)
        if time_gte is None:
            time_gte = time_lt - timedelta(hours=24)

        try:
            result = self.query_spans_groups(
                time_gte=time_gte,
                time_lt=time_lt,
                query="group by service_name | count()",
                limit=1000,
            )

            # Extract service names from groups
            services = []
            if "groups" in result:
                for group in result["groups"]:
                    if "service_name" in group:
                        services.append(group["service_name"])

            return sorted(services)
        except Exception as e:
            logger.error(f"Failed to get services: {e}")
            return []

    def query_logs(
        self,
        time_gte: datetime,
        time_lt: datetime,
        query: Optional[str] = None,
        severity: Optional[str] = None,
        service_name: Optional[str] = None,
        limit: int = 100,
    ) -> LogsResponse:
        """
        Query logs within time range with optional filters.

        Args:
            time_gte: Start time (inclusive)
            time_lt: End time (exclusive)
            query: UQL query string (e.g., 'where log_message contains "error"')
            severity: Filter by log severity (e.g., "ERROR", "WARN", "INFO")
            service_name: Filter by service name
            limit: Maximum number of logs to return

        Returns:
            LogsResponse with logs and metadata

        Raises:
            UptraceClientError: If request fails
        """
        # Build UQL query for logs
        log_query_parts = ['where _system = "log:all"']

        if severity:
            log_query_parts.append(f'where log_severity = "{severity}"')

        if service_name:
            log_query_parts.append(f'where service_name = "{service_name}"')

        if query:
            # If user provided query, append it (they should handle log-specific filters)
            log_query_parts.append(query)

        full_query = " | ".join(log_query_parts)

        # Use spans API to query logs (logs are represented as spans)
        spans_response = self.get_spans(
            time_gte=time_gte,
            time_lt=time_lt,
            query=full_query,
            limit=limit,
        )

        # Convert spans to log entries
        logs = []
        for span in spans_response.spans:
            log_entry = LogEntry(
                id=span.id,
                trace_id=span.trace_id,
                time=span.time,
                attrs=span.attrs,
                log_severity=span.attrs.get("log_severity"),
                log_message=span.attrs.get("log_message"),
                service_name=span.attrs.get("service_name"),
            )
            logs.append(log_entry)

        return LogsResponse(
            count=spans_response.count,
            logs=logs,
            has_more=spans_response.has_more,
        )

    def get_error_logs(
        self,
        time_gte: datetime,
        time_lt: datetime,
        limit: int = 100,
    ) -> LogsResponse:
        """
        Get error logs (ERROR and FATAL severity) within time range.

        Args:
            time_gte: Start time (inclusive)
            time_lt: End time (exclusive)
            limit: Maximum number of logs to return

        Returns:
            LogsResponse with error logs

        Raises:
            UptraceClientError: If request fails
        """
        return self.query_logs(
            time_gte=time_gte,
            time_lt=time_lt,
            query='where log_severity in ("ERROR", "FATAL")',
            limit=limit,
        )

    def query_metrics(
        self,
        time_gte: datetime,
        time_lt: datetime,
        metrics: List[str],
        query: List[str],
        limit: Optional[int] = None,
    ) -> Dict[str, Any]:
        """
        Query metrics using PromQL-compatible format via groups API.

        Metrics are queried through the groups API with UQL queries that include metric definitions.

        Args:
            time_gte: Start time (inclusive)
            time_lt: End time (exclusive)
            metrics: List of metric definitions with aliases (e.g., ["system_cpu_utilization as $cpu"])
            query: List of query expressions (e.g., ["sum($cpu) by (service_name)"])
            limit: Maximum number of results to return

        Returns:
            Dictionary with metric query results

        Raises:
            UptraceClientError: If request fails

        Example:
            ```python
            result = client.query_metrics(
                time_gte=datetime.now(timezone.utc) - timedelta(hours=1),
                time_lt=datetime.now(timezone.utc),
                metrics=["system_cpu_utilization as $cpu"],
                query=["avg($cpu) as cpu_avg"]
            )
            ```
        """
        # Build UQL query from metrics and query expressions
        # Metrics are referenced in query expressions using their aliases
        # The actual metric definitions are handled by Uptrace internally
        # We combine query expressions into a UQL query
        query_parts = query.copy()
        
        # Log metrics for debugging (they're used in query but not directly in API call)
        if metrics:
            logger.debug("Querying metrics: %s", metrics)
        
        uql_query = " | ".join(query_parts)

        # Use groups API to query metrics
        return self.query_spans_groups(
            time_gte=time_gte,
            time_lt=time_lt,
            query=uql_query,
            limit=limit or 100,
        )

    def query_metrics_groups(
        self,
        time_gte: datetime,
        time_lt: datetime,
        metrics: List[str],
        query: List[str],
        group_by: Optional[List[str]] = None,
        limit: int = 100,
    ) -> Dict[str, Any]:
        """
        Query and aggregate metrics by groups.

        Args:
            time_gte: Start time (inclusive)
            time_lt: End time (exclusive)
            metrics: List of metric definitions with aliases
            query: List of query expressions with aggregations
            group_by: List of attributes to group by
            limit: Maximum number of groups to return

        Returns:
            Dictionary with grouped metric results

        Raises:
            UptraceClientError: If request fails

        Example:
            ```python
            result = client.query_metrics_groups(
                time_gte=datetime.now(timezone.utc) - timedelta(hours=1),
                time_lt=datetime.now(timezone.utc),
                metrics=["uptrace_tracing_spans as $spans"],
                query=["sum($spans) as total_spans"],
                group_by=["service_name"]
            )
            ```
        """
        # Build query with grouping
        query_parts = query.copy()
        if group_by:
            group_by_str = ", ".join(group_by)
            query_parts.append(f"group by {group_by_str}")

        return self.query_metrics(
            time_gte=time_gte,
            time_lt=time_lt,
            metrics=metrics,
            query=query_parts,
            limit=limit,
        )

    def get_query_syntax(self) -> Dict[str, Any]:
        """
        Get UQL (Uptrace Query Language) syntax documentation.

        Returns:
            Dictionary with syntax documentation including operators, functions, and examples
        """
        return {
            "language": "UQL (Uptrace Query Language)",
            "description": "SQL-like language for filtering and aggregating spans, logs, and metrics",
            "basic_structure": "WHERE условие | GROUP BY поля | SELECT поля, агрегации",
            "operators": {
                "strings": {
                    "=": "точное совпадение",
                    "!=": "не равно",
                    "in (...)": "вхождение в список",
                    'like "pattern%"': "паттерн (case-insensitive)",
                    'contains "substring"': "содержит подстроку",
                    '~ "regex"': "регулярное выражение",
                    "exists": "проверка наличия атрибута",
                },
                "numbers": {
                    "=": "равно",
                    "!=": "не равно",
                    "<": "меньше",
                    "<=": "меньше или равно",
                    ">": "больше",
                    ">=": "больше или равно",
                    "exists": "проверка наличия атрибута",
                },
                "booleans": {
                    "=": "равно",
                    "!=": "не равно",
                },
            },
            "units": {
                "time": ["1ms", "5s", "10m", "1h"],
                "size": ["1KB", "100MB", "1GB"],
                "examples": [
                    "where _dur_ms > 100ms",
                    "where response_size > 1MB",
                ],
            },
            "aggregation_functions": {
                "count()": "Количество спанов",
                "p50()": "50-й перцентиль",
                "p75()": "75-й перцентиль",
                "p90()": "90-й перцентиль",
                "p95()": "95-й перцентиль",
                "p99()": "99-й перцентиль",
                "avg()": "Среднее значение",
                "min()": "Минимум",
                "max()": "Максимум",
                "sum()": "Сумма",
                "uniq()": "Количество уникальных значений",
            },
            "transformation_functions": {
                "strings": {
                    "lower(attr)": "в нижний регистр",
                    "upper(attr)": "в верхний регистр",
                    "extract(haystack, pattern)": "извлечь по regex",
                    "replace(attr, old, new)": "заменить подстроку",
                },
                "temporal": {
                    "toStartOfDay(timestamp)": "начало дня",
                    "toStartOfHour(timestamp)": "начало часа",
                    "toStartOfMinute(timestamp)": "начало минуты",
                },
                "rate": {
                    "perSec(value)": "в секунду",
                    "perMin(value)": "в минуту",
                },
            },
            "examples": {
                "error_spans": 'where _status_code = "error" | group by service_name, _name | select service_name, _name, count(), p50(_dur_ms)',
                "slow_http": 'where _system = "http" and _dur_ms > 1000ms | group by http_route | select http_route, count(), p99(_dur_ms), avg(_dur_ms)',
                "error_logs": 'where _system = "log:all" and log_severity in ("ERROR", "FATAL") | group by service_name | select service_name, count()',
                "service_metrics": "group by service_name | select service_name, count(), avg(_dur_ms), p99(_dur_ms)",
            },
            "common_attributes": {
                "system": "_system",
                "status_code": "_status_code",
                "duration_ms": "_dur_ms",
                "trace_id": "_trace_id",
                "span_id": "_id",
                "parent_id": "_parent_id",
                "time": "_time",
                "service_name": "service_name",
                "log_severity": "log_severity",
                "log_message": "log_message",
            },
            "promql_compatibility": {
                "description": "Metrics can be queried using PromQL-compatible syntax",
                "metric_aliases": "All metrics require aliases with $ prefix",
                "example": {
                    "metrics": ["postgresql_commits as $commits", "postgresql_rollbacks as $rollbacks"],
                    "query": ["sum($commits) as total_commits", "sum($rollbacks) as total_rollbacks"],
                },
            },
        }

    def close(self) -> None:
        """Close the HTTP session."""
        self.session.close()

    def __enter__(self) -> "UptraceClient":
        """Context manager entry."""
        return self

    def __exit__(self, *args: Any) -> None:
        """Context manager exit."""
        self.close()
