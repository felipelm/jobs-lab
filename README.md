# Jobs Lab

A minimal Python monorepo for learning how FastAPI services hand work to
background workers.

## Structure

```text
jobs-lab/
  apps/
    api/        FastAPI HTTP service
    worker/     Worker process entrypoint
  packages/
    common/     Shared config, models, and job helpers
  deploy/
    docker-compose/
    k8s/
    helm/
  docs/
  tests/
```

The Kubernetes and Helm deploy directories are placeholders only. This repo
intentionally does not include Kubernetes, Helm charts, or an OpenTelemetry
Collector yet.

## Architecture

The first version keeps the runtime deliberately small:

- `apps/api` exposes `/healthz`, `/readyz`, and a Postgres-backed jobs API.
- `apps/api` enqueues created job IDs into Redis.
- `apps/worker` blocks on Redis for job IDs, loads jobs from Postgres, and
  executes supported job types.
- `packages/common` owns shared request/response models, configuration, and
  pure job helpers used by both apps.
- `migrations` owns the Alembic schema migration for the `jobs` table.
- `tests` verifies the public API behavior and worker behavior.

The API and worker use SQLAlchemy async with `asyncpg`. `DATABASE_URL` configures
the database connection, and `REDIS_URL` configures the queue connection. A
future lesson can add a scheduler or an OpenTelemetry Collector without
reshaping the repository.

## API

- `POST /jobs` creates a queued job with an `id`, `type`, `payload`, `status`,
  `attempts`, `max_attempts`, `error`, `created_at`, and `updated_at`.
- `GET /jobs` returns all jobs currently held by the API process.
- `GET /jobs/{job_id}` returns one job or `404`.
- `GET /healthz` returns process health.
- `GET /readyz` checks database connectivity and returns readiness.

## Commands

```sh
make install
make test
make lint
```

Additional local run commands:

```sh
make run-api
make run-worker
```

Database commands:

```sh
export DATABASE_URL="postgresql+asyncpg://postgres:postgres@localhost:5432/jobs_lab"
export REDIS_URL="redis://localhost:6379/0"
.venv/bin/alembic upgrade head
make run-api
```

Docker API commands:

```sh
make docker-build-api
make docker-run-api
```

The API container listens on `0.0.0.0:8000` inside the container and is exposed
on `http://localhost:8000` by the Makefile run target. Override
`DOCKER_DATABASE_URL`, `DOCKER_REDIS_URL`, or `OTEL_ENABLED` if needed.

Docker Compose local development:

```sh
make compose-up
make migrate
```

Then open `http://localhost:8000/healthz` or `http://localhost:8000/readyz`.
The Compose API and worker services use:

```text
DATABASE_URL=postgresql+asyncpg://jobs_lab:jobs_lab@postgres:5432/jobs_lab
REDIS_URL=redis://redis:6379/0
```

Create a sleep job for the worker:

```sh
curl -X POST http://localhost:8000/jobs \
  -H "Content-Type: application/json" \
  -d '{"type":"sleep","payload":{"seconds":2},"max_attempts":3}'
```

Simulate failures:

```sh
curl -X POST http://localhost:8000/jobs \
  -H "Content-Type: application/json" \
  -d '{"type":"always_fail","payload":{},"max_attempts":3}'

curl -X POST http://localhost:8000/jobs \
  -H "Content-Type: application/json" \
  -d '{"type":"random_fail","payload":{"probability":0.5},"max_attempts":3}'
```

Stop the local stack with:

```sh
make compose-down
```

Postgres data is stored in the `postgres-data` Docker volume.

OpenTelemetry tracing:

```sh
make compose-up
make migrate
```

The Compose stack enables API tracing by default and starts:

- `otel-collector`, listening for OTLP on `localhost:4317` and `localhost:4318`
- `jaeger`, with the UI at `http://localhost:16686`

The API exports OTLP traces to the Collector:

```text
OTEL_ENABLED=true
OTEL_EXPORTER_OTLP_ENDPOINT=http://otel-collector:4317
```

The Collector exports traces to Jaeger. To generate a trace:

```sh
curl -X POST http://localhost:8000/jobs \
  -H "Content-Type: application/json" \
  -d '{"type":"sleep","payload":{"seconds":2},"max_attempts":3}'
```

Then open `http://localhost:16686` and search for the `jobs-api` service. Worker
`process_job` spans restore the API request trace context stored in Postgres, so
API and worker processing appear in the same distributed trace. Worker spans
include `dequeue`, `load_job`, `process_job`, `retry`, `success`, and `failure`,
with `job.id`, `job.type`, `job.attempt`, and `job.status` attributes. Outside
Compose, `OTEL_ENABLED=true` without `OTEL_EXPORTER_OTLP_ENDPOINT` still uses
console span export for the API.

See `docs/gotchas.md` for trace-context caveats.
