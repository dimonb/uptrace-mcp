"""Data models for Uptrace API."""

from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


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

    class Config:
        populate_by_name = True


class SpansResponse(BaseModel):
    """Response model for spans query."""

    count: int
    spans: List[Span]
    has_more: Optional[bool] = Field(None, alias="hasMore")

    class Config:
        populate_by_name = True


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

    class Config:
        populate_by_name = True


class ServiceInfo(BaseModel):
    """Service information model."""

    name: str
    version: Optional[str] = None
    environment: Optional[str] = None
    span_count: Optional[int] = None
