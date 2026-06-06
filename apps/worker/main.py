import asyncio
import logging
import random
import signal
import time
from contextlib import suppress

from redis.exceptions import RedisError
from sqlalchemy.exc import SQLAlchemyError

from apps.worker.telemetry import configure_tracing, get_metrics, get_tracer
from packages.common.config import get_settings
from packages.common.database import SessionLocal
from packages.common.models import JobRecord, JobStatus
from packages.common.queue import JobQueue, RedisJobQueue, create_redis_client
from packages.common.repository import SqlAlchemyJobRepository, WorkerJobRepository
from packages.common.trace_context import extract_context

logger = logging.getLogger(__name__)


async def execute_job(job: JobRecord) -> None:
    if job.type == "always_fail":
        raise RuntimeError("Job configured to always fail")

    if job.type == "random_fail":
        probability = job.payload.get("probability", 0.5)
        if not isinstance(probability, int | float):
            raise ValueError(
                "Random fail job payload field 'probability' must be a number"
            )
        if probability < 0 or probability > 1:
            raise ValueError("Random fail probability must be between 0 and 1")
        if random.random() < probability:
            raise RuntimeError("Job failed randomly")
        return

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
    tracer = get_tracer()
    worker_metrics = get_metrics()

    with tracer.start_as_current_span("dequeue") as span:
        try:
            job_id = await queue.dequeue_job_id(timeout_seconds=dequeue_timeout_seconds)
        except Exception as exc:
            span.record_exception(exc)
            raise

        if job_id is not None:
            span.set_attribute("job.id", job_id)

        await _observe_queue_depth(queue, span)

    if job_id is None:
        return None

    with tracer.start_as_current_span("load_job") as span:
        span.set_attribute("job.id", job_id)
        try:
            job = await repository.get(job_id)
        except Exception as exc:
            span.record_exception(exc)
            raise

        if job is not None:
            _set_job_attributes(span, job)

    if job is None:
        logger.warning("Dequeued job id was not found", extra={"job_id": job_id})
        return None

    if job.status not in {JobStatus.QUEUED, JobStatus.RETRYING}:
        logger.info(
            "Dequeued job is not processable",
            extra={"job_id": job.id, "job_status": job.status},
        )
        return job

    parent_context = extract_context(job.trace_context)
    with tracer.start_as_current_span("process_job", context=parent_context) as span:
        _set_job_attributes(span, job)
        try:
            running_job = await repository.mark_running(job.id)
        except Exception as exc:
            span.record_exception(exc)
            raise

        if running_job is None:
            logger.warning(
                "Dequeued job could not be marked running",
                extra={"job_id": job.id},
            )
            return None

        _set_job_attributes(span, running_job)

        started_at = time.perf_counter()
        try:
            await execute_job(running_job)
        except Exception as exc:
            worker_metrics.job_processing_duration_seconds.record(
                time.perf_counter() - started_at,
                _metric_attributes(running_job),
            )
            span.record_exception(exc)
            logger.exception(
                "Job failed",
                extra={"job_id": running_job.id, "job_type": running_job.type},
            )
            if running_job.attempts < running_job.max_attempts:
                return await _retry_job(repository, queue, running_job, exc)

            return await _fail_job(repository, running_job, exc)

        worker_metrics.job_processing_duration_seconds.record(
            time.perf_counter() - started_at,
            _metric_attributes(running_job),
        )
        return await _succeed_job(repository, running_job)


async def run_worker() -> None:
    settings = get_settings()
    configure_tracing(
        enabled=settings.otel_enabled,
        otlp_endpoint=settings.otel_exporter_otlp_endpoint,
    )
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


async def _retry_job(
    repository: WorkerJobRepository,
    queue: JobQueue,
    job: JobRecord,
    exc: Exception,
) -> JobRecord | None:
    tracer = get_tracer()
    with tracer.start_as_current_span("retry") as span:
        _set_job_attributes(span, job)
        span.record_exception(exc)
        try:
            retrying_job = await repository.mark_retrying(job.id, str(exc))
            if retrying_job is not None:
                _set_job_attributes(span, retrying_job)
                await queue.enqueue_job_id(job.id)
                await _observe_queue_depth(queue, span)
                get_metrics().jobs_retried_total.add(
                    1,
                    _metric_attributes(retrying_job),
                )
            return retrying_job
        except Exception as state_exc:
            span.record_exception(state_exc)
            raise


async def _succeed_job(
    repository: WorkerJobRepository,
    job: JobRecord,
) -> JobRecord | None:
    tracer = get_tracer()
    with tracer.start_as_current_span("success") as span:
        _set_job_attributes(span, job)
        try:
            succeeded_job = await repository.mark_succeeded(job.id)
            if succeeded_job is not None:
                _set_job_attributes(span, succeeded_job)
                get_metrics().jobs_succeeded_total.add(
                    1,
                    _metric_attributes(succeeded_job),
                )
            return succeeded_job
        except Exception as exc:
            span.record_exception(exc)
            raise


async def _fail_job(
    repository: WorkerJobRepository,
    job: JobRecord,
    exc: Exception,
) -> JobRecord | None:
    tracer = get_tracer()
    with tracer.start_as_current_span("failure") as span:
        _set_job_attributes(span, job)
        span.record_exception(exc)
        try:
            failed_job = await repository.mark_failed(job.id, str(exc))
            if failed_job is not None:
                _set_job_attributes(span, failed_job)
                get_metrics().jobs_failed_total.add(
                    1,
                    _metric_attributes(failed_job),
                )
            return failed_job
        except Exception as state_exc:
            span.record_exception(state_exc)
            raise


def _set_job_attributes(span, job: JobRecord) -> None:
    span.set_attribute("job.id", job.id)
    span.set_attribute("job.type", job.type)
    span.set_attribute("job.attempt", job.attempts)
    span.set_attribute("job.status", job.status.value)


def _metric_attributes(job: JobRecord) -> dict[str, str]:
    return {"job.type": job.type}


async def _observe_queue_depth(queue: JobQueue, span) -> None:
    try:
        queue_depth = await queue.depth()
    except Exception as exc:
        span.record_exception(exc)
        return

    get_metrics().queue_depth.set(queue_depth)


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
