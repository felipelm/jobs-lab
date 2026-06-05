from datetime import UTC, datetime
from uuid import uuid4

from packages.common.models import JobCreateRequest, JobRecord, JobResult, JobStatus


def create_job(request: JobCreateRequest) -> JobRecord:
    now = datetime.now(UTC)
    return JobRecord(
        id=str(uuid4()),
        type=request.type,
        payload=request.payload,
        status=JobStatus.QUEUED,
        created_at=now,
        updated_at=now,
    )


def run_job(job: JobRecord) -> JobResult:
    completed_job = job.model_copy(
        update={
            "status": JobStatus.SUCCEEDED,
            "updated_at": datetime.now(UTC),
        }
    )
    return JobResult(
        job=completed_job,
        output={"echo": job.payload},
    )
