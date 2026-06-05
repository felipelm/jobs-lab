VENV ?= .venv
PYTHON ?= $(VENV)/bin/python

.PHONY: install test lint run-api run-worker

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
