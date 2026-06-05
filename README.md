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

The deploy directories are placeholders only. This repo intentionally does not
include Redis, Postgres, Docker, Kubernetes, Helm charts, or OpenTelemetry yet.

## Architecture

The first version keeps the runtime deliberately small:

- `apps/api` exposes `/healthz`, `/readyz`, and an in-memory jobs API.
- `apps/worker` contains a standalone process that can execute one example job.
- `packages/common` owns shared request/response models, configuration, and
  pure job helpers used by both apps.
- `tests` verifies the public API behavior and worker behavior.

The current job store is process-local memory. A future lesson can replace that
boundary with a queue, database, scheduler, or observability layer without
reshaping the repository.

## API

- `POST /jobs` creates a queued job with an `id`, `type`, `payload`, `status`,
  `created_at`, and `updated_at`.
- `GET /jobs` returns all jobs currently held by the API process.
- `GET /jobs/{job_id}` returns one job or `404`.
- `GET /healthz` returns process health.
- `GET /readyz` returns readiness.

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
