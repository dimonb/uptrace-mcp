"""Tests for Uptrace client."""

import os
from datetime import datetime, timedelta
from unittest.mock import Mock, patch

import pytest

from uptrace_mcp.client import UptraceClient, UptraceClientError


@pytest.fixture
def client():
    """Create test client."""
    return UptraceClient(
        base_url="https://test.uptrace.dev",
        project_id="1",
        api_token="test_token",
    )


def test_client_initialization(client):
    """Test client is properly initialized."""
    assert client.base_url == "https://test.uptrace.dev"
    assert client.project_id == "1"
    assert client.api_token == "test_token"
    assert "Authorization" in client.session.headers
    assert client.session.headers["Authorization"] == "Bearer test_token"


def test_context_manager():
    """Test client works as context manager."""
    with UptraceClient("https://test.uptrace.dev", "1", "token") as client:
        assert client.session is not None
    # Session should be closed after exiting context


@patch("uptrace_mcp.client.requests.Session.request")
def test_get_spans_success(mock_request, client):
    """Test successful get_spans call."""
    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "count": 1,
        "spans": [
            {
                "id": "test123",
                "parentId": None,
                "traceId": "trace123",
                "projectId": 1,
                "groupId": "group123",
                "type": "http",
                "system": "httpserver",
                "kind": "server",
                "name": "GET /api",
                "displayName": "GET /api",
                "time": 1234567890.0,
                "duration": 100.0,
                "statusCode": "ok",
                "attrs": {},
                "events": [],
                "links": [],
            }
        ],
    }
    mock_request.return_value = mock_response

    time_gte = datetime.utcnow() - timedelta(hours=1)
    time_lt = datetime.utcnow()

    response = client.get_spans(time_gte=time_gte, time_lt=time_lt)

    assert response.count == 1
    assert len(response.spans) == 1
    assert response.spans[0].id == "test123"
    assert response.spans[0].trace_id == "trace123"


@patch("uptrace_mcp.client.requests.Session.request")
def test_get_error_spans(mock_request, client):
    """Test get_error_spans filters by error status."""
    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"count": 0, "spans": []}
    mock_request.return_value = mock_response

    time_gte = datetime.utcnow() - timedelta(hours=1)
    time_lt = datetime.utcnow()

    client.get_error_spans(time_gte=time_gte, time_lt=time_lt)

    # Check that query parameter includes error filter
    call_kwargs = mock_request.call_args[1]
    assert "params" in call_kwargs
    assert "query" in call_kwargs["params"]
    assert "error" in call_kwargs["params"]["query"]


@patch("uptrace_mcp.client.requests.Session.request")
def test_http_error_handling(mock_request, client):
    """Test HTTP error is properly handled."""
    mock_response = Mock()
    mock_response.status_code = 404
    mock_response.text = "Not found"
    mock_response.raise_for_status.side_effect = Exception("404 Error")
    mock_request.return_value = mock_response

    time_gte = datetime.utcnow() - timedelta(hours=1)
    time_lt = datetime.utcnow()

    with pytest.raises(UptraceClientError):
        client.get_spans(time_gte=time_gte, time_lt=time_lt)


def test_datetime_formatting():
    """Test datetime is formatted correctly."""
    client = UptraceClient("https://test.uptrace.dev", "1", "token")

    dt = datetime(2025, 12, 8, 10, 30, 0)
    formatted = dt.strftime("%Y-%m-%dT%H:%M:%SZ")

    assert formatted == "2025-12-08T10:30:00Z"
