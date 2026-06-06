import asyncio
from datetime import UTC, datetime
from uuid import uuid4

from apps.worker.main import process_one
from packages.common.models import JobRecord, JobStatus


class FakeWorkerRepository:
    def __init__(self, jobs: list[JobRecord]) -> None:
        self.jobs = {job.id: job for job in jobs}
        self.transitions: list[JobStatus] = []

    async def claim_queued(self) -> JobRecord | None:
        for job in self.jobs.values():
            if job.status == JobStatus.QUEUED:
                running_job = job.model_copy(
                    update={
                        "status": JobStatus.RUNNING,
                        "updated_at": datetime.now(UTC),
                    }
                )
                self.jobs[job.id] = running_job
                self.transitions.append(JobStatus.RUNNING)
                return running_job

        return None

    async def mark_succeeded(self, job_id: str) -> JobRecord | None:
        return self._mark_status(job_id, JobStatus.SUCCEEDED)

    async def mark_failed(self, job_id: str) -> JobRecord | None:
        return self._mark_status(job_id, JobStatus.FAILED)

    def _mark_status(self, job_id: str, status: JobStatus) -> JobRecord | None:
        job = self.jobs.get(job_id)
        if job is None:
            return None

        updated_job = job.model_copy(
            update={
                "status": status,
                "updated_at": datetime.now(UTC),
            }
        )
        self.jobs[job_id] = updated_job
        self.transitions.append(status)
        return updated_job


def test_process_one_marks_sleep_job_succeeded() -> None:
    job = create_test_job(type="sleep", payload={"seconds": 0})
    repository = FakeWorkerRepository([job])

    result = asyncio.run(process_one(repository))

    assert result is not None
    assert result.status == JobStatus.SUCCEEDED
    assert repository.transitions == [JobStatus.RUNNING, JobStatus.SUCCEEDED]
    assert repository.jobs[job.id].status == JobStatus.SUCCEEDED


def test_process_one_marks_job_failed_on_exception() -> None:
    job = create_test_job(type="sleep", payload={"seconds": -1})
    repository = FakeWorkerRepository([job])

    result = asyncio.run(process_one(repository))

    assert result is not None
    assert result.status == JobStatus.FAILED
    assert repository.transitions == [JobStatus.RUNNING, JobStatus.FAILED]
    assert repository.jobs[job.id].status == JobStatus.FAILED


def test_process_one_returns_none_when_no_job_is_queued() -> None:
    job = create_test_job(
        type="sleep",
        payload={"seconds": 0},
        status=JobStatus.RUNNING,
    )
    repository = FakeWorkerRepository([job])

    result = asyncio.run(process_one(repository))

    assert result is None
    assert repository.transitions == []


def create_test_job(
    type: str,
    payload: dict[str, object],
    status: JobStatus = JobStatus.QUEUED,
) -> JobRecord:
    now = datetime.now(UTC)
    return JobRecord(
        id=str(uuid4()),
        type=type,
        payload=payload,
        status=status,
        created_at=now,
        updated_at=now,
    )
