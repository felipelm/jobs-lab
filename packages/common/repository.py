from datetime import UTC, datetime
from typing import Protocol

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from packages.common.jobs import create_job
from packages.common.models import JobCreateRequest, JobRecord, JobStatus
from packages.common.orm import JobORM


class JobRepository(Protocol):
    async def create(self, request: JobCreateRequest) -> JobRecord: ...

    async def list(self) -> list[JobRecord]: ...

    async def get(self, job_id: str) -> JobRecord | None: ...


class WorkerJobRepository(Protocol):
    async def get(self, job_id: str) -> JobRecord | None: ...

    async def mark_running(self, job_id: str) -> JobRecord | None: ...

    async def mark_succeeded(self, job_id: str) -> JobRecord | None: ...

    async def mark_failed(self, job_id: str) -> JobRecord | None: ...


class SqlAlchemyJobRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(self, request: JobCreateRequest) -> JobRecord:
        job = create_job(request)
        db_job = _to_orm(job)

        self._session.add(db_job)
        await self._session.commit()
        await self._session.refresh(db_job)

        return _to_record(db_job)

    async def list(self) -> list[JobRecord]:
        result = await self._session.execute(
            select(JobORM).order_by(JobORM.created_at, JobORM.id)
        )
        return [_to_record(job) for job in result.scalars()]

    async def get(self, job_id: str) -> JobRecord | None:
        db_job = await self._session.get(JobORM, job_id)
        if db_job is None:
            return None
        return _to_record(db_job)

    async def mark_running(self, job_id: str) -> JobRecord | None:
        return await self._mark_status(job_id, JobStatus.RUNNING)

    async def mark_succeeded(self, job_id: str) -> JobRecord | None:
        return await self._mark_status(job_id, JobStatus.SUCCEEDED)

    async def mark_failed(self, job_id: str) -> JobRecord | None:
        return await self._mark_status(job_id, JobStatus.FAILED)

    async def _mark_status(
        self,
        job_id: str,
        status: JobStatus,
    ) -> JobRecord | None:
        db_job = await self._session.get(JobORM, job_id)
        if db_job is None:
            await self._session.rollback()
            return None

        db_job.status = status.value
        db_job.updated_at = datetime.now(UTC)
        await self._session.commit()
        await self._session.refresh(db_job)

        return _to_record(db_job)


def _to_orm(job: JobRecord) -> JobORM:
    return JobORM(
        id=job.id,
        type=job.type,
        payload=job.payload,
        status=job.status.value,
        created_at=job.created_at,
        updated_at=job.updated_at,
    )


def _to_record(job: JobORM) -> JobRecord:
    return JobRecord(
        id=job.id,
        type=job.type,
        payload=job.payload,
        status=JobStatus(job.status),
        created_at=job.created_at,
        updated_at=job.updated_at,
    )
