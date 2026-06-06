from collections.abc import AsyncIterator
from typing import Annotated

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from packages.common.config import get_settings
from packages.common.database import get_session
from packages.common.queue import JobQueue, RedisJobQueue, create_redis_client
from packages.common.repository import JobRepository, SqlAlchemyJobRepository


def get_job_repository(
    session: Annotated[AsyncSession, Depends(get_session)],
) -> JobRepository:
    return SqlAlchemyJobRepository(session)


async def get_job_queue() -> AsyncIterator[JobQueue]:
    redis = create_redis_client(get_settings().redis_url)
    try:
        yield RedisJobQueue(redis)
    finally:
        await redis.aclose()
