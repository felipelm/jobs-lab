import asyncio
from datetime import UTC, datetime
from uuid import uuid4

from apps.worker.main import process_one
from packages.common.models import JobRecord, JobStatus


class FakeWorkerRepository:
    def __init__(self, jobs: list[JobRecord]) -> None:
        self.jobs = {job.id: job for job in jobs}
        self.transitions: list[JobStatus] = []

    async def get(self, job_id: str) -> JobRecord | None:
        return self.jobs.get(job_id)

    async def mark_running(self, job_id: str) -> JobRecord | None:
        return self._mark_status(job_id, JobStatus.RUNNING)

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


class FakeJobQueue:
    def __init__(self, job_ids: list[str]) -> None:
        self.job_ids = job_ids
        self.dequeue_timeouts: list[float] = []

    async def enqueue_job_id(self, job_id: str) -> None:
        self.job_ids.append(job_id)

    async def dequeue_job_id(self, timeout_seconds: float) -> str | None:
        self.dequeue_timeouts.append(timeout_seconds)
        if not self.job_ids:
            return None
        return self.job_ids.pop(0)


def test_process_one_marks_sleep_job_succeeded() -> None:
    job = create_test_job(type="sleep", payload={"seconds": 0})
    repository = FakeWorkerRepository([job])
    queue = FakeJobQueue([job.id])

    result = asyncio.run(
        process_one(
            repository=repository,
            queue=queue,
            dequeue_timeout_seconds=1,
        )
    )

    assert result is not None
    assert result.status == JobStatus.SUCCEEDED
    assert repository.transitions == [JobStatus.RUNNING, JobStatus.SUCCEEDED]
    assert repository.jobs[job.id].status == JobStatus.SUCCEEDED
    assert queue.dequeue_timeouts == [1]


def test_process_one_marks_job_failed_on_exception() -> None:
    job = create_test_job(type="sleep", payload={"seconds": -1})
    repository = FakeWorkerRepository([job])
    queue = FakeJobQueue([job.id])

    result = asyncio.run(
        process_one(
            repository=repository,
            queue=queue,
            dequeue_timeout_seconds=1,
        )
    )

    assert result is not None
    assert result.status == JobStatus.FAILED
    assert repository.transitions == [JobStatus.RUNNING, JobStatus.FAILED]
    assert repository.jobs[job.id].status == JobStatus.FAILED


def test_process_one_returns_none_when_queue_is_empty() -> None:
    job = create_test_job(type="sleep", payload={"seconds": 0})
    repository = FakeWorkerRepository([job])
    queue = FakeJobQueue([])

    result = asyncio.run(
        process_one(
            repository=repository,
            queue=queue,
            dequeue_timeout_seconds=1,
        )
    )

    assert result is None
    assert repository.transitions == []


def test_process_one_skips_non_queued_job() -> None:
    job = create_test_job(
        type="sleep",
        payload={"seconds": 0},
        status=JobStatus.RUNNING,
    )
    repository = FakeWorkerRepository([job])
    queue = FakeJobQueue([job.id])

    result = asyncio.run(
        process_one(
            repository=repository,
            queue=queue,
            dequeue_timeout_seconds=1,
        )
    )

    assert result == job
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

