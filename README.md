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

- `apps/api` exposes HTTP endpoints for health checks and job submission.
- `apps/worker` contains a standalone process that can execute one example job.
- `packages/common` owns shared request/response models, configuration, and
  pure job helpers used by both apps.
- `tests` verifies the public API behavior and worker behavior.

The current job handoff is only a local model-level boundary. A future lesson can
replace that boundary with a queue, database, scheduler, or observability layer
without reshaping the repository.

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

