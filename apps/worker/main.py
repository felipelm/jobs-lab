import asyncio
import logging
import signal
from contextlib import suppress

from sqlalchemy.exc import SQLAlchemyError

from packages.common.config import get_settings
from packages.common.database import SessionLocal
from packages.common.models import JobRecord
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


async def process_one(repository: WorkerJobRepository) -> JobRecord | None:
    job = await repository.claim_queued()
    if job is None:
        return None

    try:
        await execute_job(job)
    except Exception:
        logger.exception("Job failed", extra={"job_id": job.id, "job_type": job.type})
        return await repository.mark_failed(job.id)

    return await repository.mark_succeeded(job.id)


async def run_worker() -> None:
    settings = get_settings()
    stop_event = asyncio.Event()
    _install_shutdown_handlers(stop_event)

    logger.info("Worker started")
    while not stop_event.is_set():
        processed_job = await _process_next_job()
        if processed_job is None:
            await _wait_for_next_poll(stop_event, settings.worker_poll_interval_seconds)

    logger.info("Worker stopped")


async def _process_next_job() -> JobRecord | None:
    try:
        async with SessionLocal() as session:
            repository = SqlAlchemyJobRepository(session)
            return await process_one(repository)
    except SQLAlchemyError:
        logger.exception("Worker poll failed")
        return None


async def _wait_for_next_poll(stop_event: asyncio.Event, poll_interval: float) -> None:
    with suppress(TimeoutError):
        await asyncio.wait_for(stop_event.wait(), timeout=poll_interval)


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

