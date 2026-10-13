# Retire Projection — common development commands.
# Requires: uv (https://docs.astral.sh/uv/), Node.js 20+, PostgreSQL running locally.
#
#   make setup    one-time environment setup (venv + deps + frontend install)
#   make test     run every test suite (backend pytest + frontend vitest)
#   make backend  start the API server on 127.0.0.1:8000
#   make frontend start the Vite dev server on 127.0.0.1:5173

.DEFAULT_GOAL := help

VENV := .venv
PY := $(VENV)/bin/python
UV ?= uv

.PHONY: help setup lock backend frontend test test-backend test-frontend lint check migrate migrate-revision

help: ## List available targets
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-20s\033[0m %s\n", $$1, $$2}'

setup: ## Create the venv (if missing), install backend (editable) + frontend deps
	@test -x $(VENV)/bin/python || $(UV) venv $(VENV) --python python3 --seed
	$(UV) pip install --python $(PY) -e "backend[dev]"
	cd frontend && npm install

lock: ## Regenerate backend/requirements.lock.txt from the live venv
	$(UV) pip freeze --python $(PY) | grep -v -E '^(-e|file://)' | sort > backend/requirements.lock.txt

backend: ## Run the API server (binds 127.0.0.1:8000 per .env)
	$(PY) -m app.main

frontend: ## Run the Vite dev server (127.0.0.1:5173, proxies /api to :8000)
	cd frontend && npm run dev

test: test-backend test-frontend ## Run all test suites

test-backend: ## Run pytest
	cd backend && ../$(VENV)/bin/python -m pytest

test-frontend: ## Run vitest
	cd frontend && npm test

lint: ## Static checks: ruff (backend) + tsc (frontend)
	$(VENV)/bin/ruff check backend
	cd frontend && npx tsc --noEmit

migrate: ## Apply pending Alembic migrations to DATABASE_URL
	cd backend && ../$(VENV)/bin/alembic upgrade head

migrate-revision: ## Create a new revision, e.g. make migrate-revision MSG="add accounts"
	cd backend && ../$(VENV)/bin/alembic revision --autogenerate -m "$(MSG)"

check: lint test ## Everything worth running before a commit
