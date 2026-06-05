from datetime import datetime
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field


class JobStatus(StrEnum):
    QUEUED = "queued"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"


class JobCreateRequest(BaseModel):
    type: str = Field(min_length=1, max_length=64)
    payload: dict[str, Any] = Field(default_factory=dict)


class JobRecord(BaseModel):
    id: str
    type: str
    payload: dict[str, Any]
    status: JobStatus
    created_at: datetime
    updated_at: datetime


class JobResult(BaseModel):
    job: JobRecord
    output: dict[str, Any] = Field(default_factory=dict)


class HealthResponse(BaseModel):
    service: str
    status: str
    environment: str


class ReadinessResponse(BaseModel):
    service: str
    status: str
    ready: bool
