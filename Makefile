VENV ?= .venv
PYTHON ?= $(VENV)/bin/python
API_IMAGE ?= jobs-lab-api
DOCKER_DATABASE_URL ?= postgresql+asyncpg://postgres:postgres@host.docker.internal:5432/jobs_lab
COMPOSE_FILE ?= deploy/docker-compose/compose.yml
COMPOSE ?= docker compose -f $(COMPOSE_FILE)

.PHONY: install test lint run-api run-worker docker-build-api docker-run-api compose-up compose-down migrate

$(PYTHON):
	python3 -m venv $(VENV)

install: $(PYTHON)
	$(PYTHON) -m pip install -e ".[dev]"

test: $(PYTHON)
	$(PYTHON) -m pytest

lint: $(PYTHON)
	$(PYTHON) -m ruff check .

run-api: $(PYTHON)
	$(PYTHON) -m uvicorn apps.api.main:app --reload

run-worker: $(PYTHON)
	$(PYTHON) -m apps.worker.main

docker-build-api:
	docker build -f apps/api/Dockerfile -t $(API_IMAGE) .

docker-run-api:
	docker run --rm -p 8000:8000 -e DATABASE_URL="$(DOCKER_DATABASE_URL)" $(API_IMAGE)

compose-up:
	$(COMPOSE) up --build -d

compose-down:
	$(COMPOSE) down

migrate:
	$(COMPOSE) run --rm api alembic upgrade head
