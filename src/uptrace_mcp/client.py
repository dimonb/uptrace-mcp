"""Uptrace API client."""

import logging
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional
from urllib.parse import urljoin, urlencode

import requests
from pydantic import ValidationError

from .models import Span, SpansResponse, TraceResponse

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
            base_url: Base URL of Uptrace instance (e.g., https://uptrace.finlab.team)
            project_id: Project ID
            api_token: API authentication token
        """
        self.base_url = base_url.rstrip("/")
        self.project_id = project_id
        self.api_token = api_token
        self.session = requests.Session()
        self.session.headers.update({"Authorization": f"Bearer {api_token}"})

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

    def get_trace(self, trace_id: str) -> List[Span]:
        """
        Get all spans for a specific trace.

        Args:
            trace_id: Trace ID

        Returns:
            List of spans in the trace

        Raises:
            UptraceClientError: If request fails
        """
        # Get spans for the last 24 hours filtered by trace_id
        time_lt = datetime.utcnow()
        time_gte = time_lt - timedelta(hours=24)

        response = self.get_spans(
            time_gte=time_gte,
            time_lt=time_lt,
            query=f'where _trace_id = "{trace_id}"',
            limit=1000,
        )

        return response.spans

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
            time_lt = datetime.utcnow()
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

    def close(self) -> None:
        """Close the HTTP session."""
        self.session.close()

    def __enter__(self) -> "UptraceClient":
        """Context manager entry."""
        return self

    def __exit__(self, *args: Any) -> None:
        """Context manager exit."""
        self.close()
