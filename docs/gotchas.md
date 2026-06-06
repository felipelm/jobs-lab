# Gotchas

## OpenTelemetry Context Through Jobs

The API stores W3C trace context in the `jobs.trace_context` JSON column when it
creates a job. The worker restores that context before starting `process_job`, so
API and worker processing appear in the same distributed trace.

This is intentionally persisted in Postgres, not Redis. Redis only carries the
job ID, so retries use the same stored trace context and old raw Redis messages
still work.

Jobs created before the `0003_add_job_trace_context` migration have an empty
trace context. Those worker spans will still have `job.id` attributes, but they
will not join the original API trace.

Idle Redis dequeue attempts can still create worker `dequeue` spans. Those spans
do not have a `job.id` because no job was received.

