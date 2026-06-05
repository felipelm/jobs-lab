from datetime import UTC, datetime
from uuid import uuid4

from packages.common.models import JobCreateRequest, JobRecord, JobResult, JobStatus


def create_job(request: JobCreateRequest) -> JobRecord:
    return JobRecord(
        id=str(uuid4()),
        kind=request.kind,
        payload=request.payload,
        status=JobStatus.QUEUED,
        created_at=datetime.now(UTC),
    )


def run_job(job: JobRecord) -> JobResult:
    completed_job = job.model_copy(update={"status": JobStatus.SUCCEEDED})
    return JobResult(
        job=completed_job,
        output={"echo": job.payload},
    )

