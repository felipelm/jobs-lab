from typing import Protocol

from redis.asyncio import Redis

DEFAULT_JOB_QUEUE_NAME = "jobs"


class JobQueue(Protocol):
    async def enqueue_job_id(self, job_id: str) -> None: ...

    async def dequeue_job_id(self, timeout_seconds: float) -> str | None: ...

    async def depth(self) -> int: ...


class RedisJobQueue:
    def __init__(
        self,
        redis: Redis,
        queue_name: str = DEFAULT_JOB_QUEUE_NAME,
    ) -> None:
        self._redis = redis
        self._queue_name = queue_name

    async def enqueue_job_id(self, job_id: str) -> None:
        await self._redis.rpush(self._queue_name, job_id)

    async def depth(self) -> int:
        return await self._redis.llen(self._queue_name)

    async def dequeue_job_id(self, timeout_seconds: float) -> str | None:
        result = await self._redis.blpop(
            self._queue_name,
            timeout=timeout_seconds,
        )
        if result is None:
            return None

        _, job_id = result
        if isinstance(job_id, bytes):
            return job_id.decode()

        return job_id


def create_redis_client(redis_url: str) -> Redis:
    return Redis.from_url(redis_url, decode_responses=True)
