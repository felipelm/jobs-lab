VENV ?= .venv
PYTHON ?= $(VENV)/bin/python
API_IMAGE ?= jobs-lab-api

.PHONY: install test lint run-api run-worker docker-build-api docker-run-api

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
	docker run --rm -p 8000:8000 $(API_IMAGE)
