"""Data models for Uptrace API."""

from datetime import datetime
from typing import Any, Dict, List, Optional, Union

from pydantic import BaseModel, ConfigDict, Field


class SpanEvent(BaseModel):
    """Span event model."""

    name: str
    time: float
    attrs: Dict[str, Any] = Field(default_factory=dict)


class Span(BaseModel):
    """Span model representing a distributed trace span."""

    id: str
    parent_id: Optional[str] = Field(None, alias="parentId")
    trace_id: str = Field(alias="traceId")
    project_id: int = Field(alias="projectId")
    group_id: str = Field(alias="groupId")
    type: str
    system: str
    kind: str
    name: str
    display_name: str = Field(alias="displayName")
    time: float
    duration: float
    status_code: str = Field(alias="statusCode")
    status_message: Optional[str] = Field(None, alias="statusMessage")
    attrs: Dict[str, Any] = Field(default_factory=dict)
    events: List[SpanEvent] = Field(default_factory=list)
    links: List[Dict[str, Any]] = Field(default_factory=list)

    model_config = ConfigDict(populate_by_name=True)


class SpansResponse(BaseModel):
    """Response model for spans query."""

    count: int
    spans: List[Span]
    has_more: Optional[bool] = Field(None, alias="hasMore")

    model_config = ConfigDict(populate_by_name=True)


class QueryFilter(BaseModel):
    """Query filter model."""

    disabled: bool = False
    error: str = ""
    id: str
    query: str
    type: str


class TraceResponse(BaseModel):
    """Response model for trace query."""

    trace_id: str = Field(alias="traceId")
    spans: List[Span]

    model_config = ConfigDict(populate_by_name=True)


class ServiceInfo(BaseModel):
    """Service information model."""

    name: str
    version: Optional[str] = None
    environment: Optional[str] = None
    span_count: Optional[int] = None


class LogEntry(BaseModel):
    """Log entry model (logs are represented as spans with _system = 'log:all')."""

    id: str
    trace_id: Optional[str] = Field(None, alias="traceId")
    time: float
    attrs: Dict[str, Any] = Field(default_factory=dict)
    log_severity: Optional[str] = Field(None, alias="log_severity")
    log_message: Optional[str] = Field(None, alias="log_message")
    service_name: Optional[str] = Field(None, alias="service_name")

    @property
    def severity(self) -> Optional[str]:
        """Get log severity from attributes."""
        return self.attrs.get("log_severity") or self.log_severity

    @property
    def message(self) -> Optional[str]:
        """Get log message from attributes."""
        return self.attrs.get("log_message") or self.log_message

    model_config = ConfigDict(populate_by_name=True)


class LogsResponse(BaseModel):
    """Response model for logs query."""

    count: int
    logs: List[LogEntry]
    has_more: Optional[bool] = Field(None, alias="hasMore")

    model_config = ConfigDict(populate_by_name=True)


class MetricQuery(BaseModel):
    """Metric query model."""

    metrics: List[str]
    query: List[str]

    model_config = ConfigDict(populate_by_name=True)


class MetricResult(BaseModel):
    """Metric query result model."""

    metric: str
    value: float
    labels: Dict[str, str] = Field(default_factory=dict)
    timestamp: Optional[float] = None

    model_config = ConfigDict(populate_by_name=True)


class MetricsResponse(BaseModel):
    """Response model for metrics query."""

    results: List[MetricResult]
    metadata: Optional[Dict[str, Any]] = None

    model_config = ConfigDict(populate_by_name=True)


class Monitor(BaseModel):
    """Monitor model."""

    id: Union[str, int]
    name: str
    type: str
    params: Dict[str, Any]
    notify_everyone_by_email: Optional[bool] = Field(None, alias="notifyEveryoneByEmail")
    team_ids: Optional[List[int]] = Field(None, alias="teamIds")
    channel_ids: Optional[List[int]] = Field(None, alias="channelIds")
    repeat_interval: Optional[Any] = Field(None, alias="repeatInterval")

    model_config = ConfigDict(populate_by_name=True)


class Dashboard(BaseModel):
    """Dashboard model."""

    id: str
    name: str
    description: Optional[str] = None
    folder_id: Optional[int] = Field(None, alias="folderId")
    data: Dict[str, Any] = Field(default_factory=dict)
    created_at: Optional[datetime] = Field(None, alias="createdAt")
    updated_at: Optional[datetime] = Field(None, alias="updatedAt")

    model_config = ConfigDict(populate_by_name=True)


class Alert(BaseModel):
    """Alert incident model."""

    id: Union[str, int]
    project_id: Union[str, int] = Field(alias="projectId")
    monitor_id: Union[str, int] = Field(alias="monitorId")
    name: str
    type: str
    attrs: Dict[str, Any] = Field(default_factory=dict)
    created_at: float = Field(alias="createdAt")
    updated_at: float = Field(alias="updatedAt")
    status: Optional[str] = None
    events: List[Dict[str, Any]] = Field(default_factory=list)

    model_config = ConfigDict(populate_by_name=True)
