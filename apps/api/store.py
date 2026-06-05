from threading import Lock

from packages.common.models import JobRecord


class InMemoryJobStore:
    def __init__(self) -> None:
        self._jobs: dict[str, JobRecord] = {}
        self._lock = Lock()

    def add(self, job: JobRecord) -> JobRecord:
        with self._lock:
            self._jobs[job.id] = job
        return job

    def list(self) -> list[JobRecord]:
        with self._lock:
            return list(self._jobs.values())

    def get(self, job_id: str) -> JobRecord | None:
        with self._lock:
            return self._jobs.get(job_id)

