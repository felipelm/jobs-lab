from datetime import datetime
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field


class JobStatus(StrEnum):
    QUEUED = "queued"
    RUNNING = "running"
    RETRYING = "retrying"
    SUCCEEDED = "succeeded"
    FAILED = "failed"


class JobCreateRequest(BaseModel):
    type: str = Field(min_length=1, max_length=64)
    payload: dict[str, Any] = Field(default_factory=dict)
    max_attempts: int = Field(default=3, ge=1, le=100)


class JobRecord(BaseModel):
    id: str
    type: str
    payload: dict[str, Any]
    status: JobStatus
    attempts: int
    max_attempts: int
    error: str | None
    trace_context: dict[str, str] = Field(default_factory=dict, exclude=True)
    created_at: datetime
    updated_at: datetime


class HealthResponse(BaseModel):
    service: str
    status: str
    environment: str


class ReadinessResponse(BaseModel):
    service: str
    status: str
    ready: bool
