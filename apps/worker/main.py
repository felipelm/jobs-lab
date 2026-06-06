import asyncio
import logging
import signal
from contextlib import suppress

from redis.exceptions import RedisError
from sqlalchemy.exc import SQLAlchemyError

from packages.common.config import get_settings
from packages.common.database import SessionLocal
from packages.common.models import JobRecord, JobStatus
from packages.common.queue import JobQueue, RedisJobQueue, create_redis_client
from packages.common.repository import SqlAlchemyJobRepository, WorkerJobRepository

logger = logging.getLogger(__name__)


async def execute_job(job: JobRecord) -> None:
    if job.type != "sleep":
        raise ValueError(f"Unsupported job type: {job.type}")

    seconds = job.payload.get("seconds", 1)
    if not isinstance(seconds, int | float):
        raise ValueError("Sleep job payload field 'seconds' must be a number")

    if seconds < 0:
        raise ValueError("Sleep job payload field 'seconds' must be non-negative")

    await asyncio.sleep(seconds)


async def process_one(
    repository: WorkerJobRepository,
    queue: JobQueue,
    dequeue_timeout_seconds: float,
) -> JobRecord | None:
    job_id = await queue.dequeue_job_id(timeout_seconds=dequeue_timeout_seconds)
    if job_id is None:
        return None

    job = await repository.get(job_id)
    if job is None:
        logger.warning("Dequeued job id was not found", extra={"job_id": job_id})
        return None

    if job.status != JobStatus.QUEUED:
        logger.info(
            "Dequeued job is not queued",
            extra={"job_id": job.id, "job_status": job.status},
        )
        return job

    running_job = await repository.mark_running(job.id)
    if running_job is None:
        logger.warning(
            "Dequeued job could not be marked running",
            extra={"job_id": job.id},
        )
        return None

    try:
        await execute_job(running_job)
    except Exception:
        logger.exception(
            "Job failed",
            extra={"job_id": running_job.id, "job_type": running_job.type},
        )
        return await repository.mark_failed(running_job.id)

    return await repository.mark_succeeded(running_job.id)


async def run_worker() -> None:
    settings = get_settings()
    stop_event = asyncio.Event()
    _install_shutdown_handlers(stop_event)
    redis = create_redis_client(settings.redis_url)
    queue = RedisJobQueue(redis)

    logger.info("Worker started")
    try:
        while not stop_event.is_set():
            await _process_next_job(
                queue=queue,
                dequeue_timeout_seconds=settings.worker_poll_interval_seconds,
            )
    finally:
        await redis.aclose()

    logger.info("Worker stopped")


async def _process_next_job(
    queue: JobQueue,
    dequeue_timeout_seconds: float,
) -> JobRecord | None:
    try:
        async with SessionLocal() as session:
            repository = SqlAlchemyJobRepository(session)
            return await process_one(
                repository=repository,
                queue=queue,
                dequeue_timeout_seconds=dequeue_timeout_seconds,
            )
    except SQLAlchemyError:
        logger.exception("Worker poll failed")
        return None
    except RedisError:
        logger.exception("Worker queue pop failed")
        return None


def _install_shutdown_handlers(stop_event: asyncio.Event) -> None:
    loop = asyncio.get_running_loop()

    for shutdown_signal in (signal.SIGINT, signal.SIGTERM):
        with suppress(NotImplementedError, RuntimeError, ValueError):
            loop.add_signal_handler(shutdown_signal, stop_event.set)


def main() -> None:
    logging.basicConfig(level=logging.INFO)
    asyncio.run(run_worker())


if __name__ == "__main__":
    main()
