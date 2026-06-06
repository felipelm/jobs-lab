from datetime import UTC, datetime
from uuid import uuid4

from packages.common.models import JobCreateRequest, JobRecord, JobStatus


def create_job(
    request: JobCreateRequest,
    trace_context: dict[str, str] | None = None,
) -> JobRecord:
    now = datetime.now(UTC)
    return JobRecord(
        id=str(uuid4()),
        type=request.type,
        payload=request.payload,
        status=JobStatus.QUEUED,
        attempts=0,
        max_attempts=request.max_attempts,
        error=None,
        trace_context=trace_context or {},
        created_at=now,
        updated_at=now,
    )
