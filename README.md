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
intentionally does not include Redis, Kubernetes, Helm charts, or OpenTelemetry
yet.

## Architecture

The first version keeps the runtime deliberately small:

- `apps/api` exposes `/healthz`, `/readyz`, and a Postgres-backed jobs API.
- `apps/worker` contains a standalone process that can execute one example job.
- `packages/common` owns shared request/response models, configuration, and
  pure job helpers used by both apps.
- `migrations` owns the Alembic schema migration for the `jobs` table.
- `tests` verifies the public API behavior and worker behavior.

The API uses SQLAlchemy async with `asyncpg`. `DATABASE_URL` configures the
database connection. A future lesson can add a queue, scheduler, or observability
layer without reshaping the repository.

## API

- `POST /jobs` creates a queued job with an `id`, `type`, `payload`, `status`,
  `created_at`, and `updated_at`.
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
`DOCKER_DATABASE_URL` if your Postgres connection string is different.

Docker Compose local development:

```sh
make compose-up
make migrate
```

Then open `http://localhost:8000/healthz` or `http://localhost:8000/readyz`.
The Compose API service uses:

```text
DATABASE_URL=postgresql+asyncpg://jobs_lab:jobs_lab@postgres:5432/jobs_lab
```

Stop the local stack with:

```sh
make compose-down
```

Postgres data is stored in the `postgres-data` Docker volume.
