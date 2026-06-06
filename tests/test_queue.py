import asyncio
from typing import Any

from packages.common.queue import RedisJobQueue


class FakeRedis:
    def __init__(self) -> None:
        self.values: list[str | bytes] = []
        self.rpush_calls: list[tuple[str, str]] = []
        self.blpop_timeouts: list[float] = []

    async def rpush(self, key: str, value: str) -> None:
        self.rpush_calls.append((key, value))
        self.values.append(value)

    async def blpop(self, key: str, timeout: float) -> tuple[str, Any] | None:
        self.blpop_timeouts.append(timeout)
        if not self.values:
            return None
        return key, self.values.pop(0)


def test_redis_job_queue_enqueues_and_dequeues_job_id() -> None:
    redis = FakeRedis()
    queue = RedisJobQueue(redis=redis, queue_name="test-jobs")

    asyncio.run(queue.enqueue_job_id("job-1"))
    job_id = asyncio.run(queue.dequeue_job_id(timeout_seconds=3))

    assert job_id == "job-1"
    assert redis.rpush_calls == [("test-jobs", "job-1")]
    assert redis.blpop_timeouts == [3]


def test_redis_job_queue_decodes_bytes_job_id() -> None:
    redis = FakeRedis()
    redis.values.append(b"job-1")
    queue = RedisJobQueue(redis=redis, queue_name="test-jobs")

    job_id = asyncio.run(queue.dequeue_job_id(timeout_seconds=1))

    assert job_id == "job-1"


def test_redis_job_queue_returns_none_when_queue_is_empty() -> None:
    redis = FakeRedis()
    queue = RedisJobQueue(redis=redis, queue_name="test-jobs")

    job_id = asyncio.run(queue.dequeue_job_id(timeout_seconds=1))

    assert job_id is None

