# PROJECT_STATE.md — Authoritative project status

> **Session startup protocol:** read this file first, then `NEXT_SESSION.md`,
> then skim `IMPLEMENTATION_PLAN.md` / `FEATURE_MATRIX.md`. The repository is
> the source of truth wherever documentation and code disagree.

- **Checkpoint:** 2026-10-13, end of session 1 (see `SESSION_LOG.md`)
- **Purpose / scope:** a local-first, subscription-free retirement and
  financial planning platform (household modeling → deterministic projection
  engine → tax engine → Monte Carlo → optimizers), running locally with an
  eventual move to a production server.
- **Current development phase:** Phase 0 (Discovery & project foundation)
  complete; Phase 1 next.

## Completion estimates

| Area | Estimate | Notes |
| --- | --- | --- |
| Phase 0 — foundation | 95% | INFRA-004 (Docker build) unverified |
| Phase 1 — MVP planning app | 3% | data model not started |
| Phase 2 — retirement income | 0% | not started |
| Phase 3 — tax engine | 0% | not started (NJ prioritized) |
| Phase 4 — risk & simulation | 0% | not started |
| Phase 5 — optimizers | 0% | not started |
| Phase 6 — advanced UX / AI assistant | 0% | not started |
| Phase 7 — hardening & release | 0% | not started |
| **Overall** | **~7%** | |

## Task status

- **Last successfully completed task:** INFRA-003 — smallest runnable
  application with database connection, health check, tests, and a
  reproducible startup workflow (verified live in session 1).
- **Current task:** none in progress; session closed cleanly per the
  shutdown protocol.
- **Single most useful next task:** **DATA-001** — financial domain model
  (household, accounts, income, expenses) with migrations and CRUD,
  establishing the Phase 1 vertical slice. See `NEXT_SESSION.md`.

## Implemented and verified (tests run, results observed)

- Git repository, directory structure, and all 12 continuity documents.
- Backend: FastAPI app factory, settings (pydantic-settings), SQLAlchemy
  engine, `GET /api/health` (200 ok / 503 degraded), root info endpoint,
  OpenAPI docs at `/api/docs`.
- Alembic pipeline: baseline revision `0001`; `alembic upgrade head` applied
  to both the live DB (`retirement`) and the test DB (`retirement_test`).
- Local PostgreSQL 16: role `retire_app` (login + CREATEDB for tests),
  database `retirement` owned by that role.
- Backend test suite: **9 passed** (`make test-backend`).
- Frontend: Vite + React 19 + TS skeleton with a real health view;
  **3 tests passed**, `tsc --noEmit` clean, `vite build` succeeds.
- Lint: `ruff check backend` clean; frontend typecheck clean (`make lint`
  exit 0).
- Live end-to-end: API started on `127.0.0.1:8010`, `/api/health` returned
  HTTP 200 with `database.connected=true` (latency ≈1.9 ms), Vite dev server
  on `127.0.0.1:5173` served the UI and proxied `/api/health` to the API
  successfully; both stopped cleanly afterwards.

## Implemented but not fully verified

- `docker-compose.yml`, `Dockerfile.backend`, `frontend/Dockerfile`,
  `nginx.conf` — written for the production target but **never built**
  (no Docker on this machine). Tracked as INFRA-004.
- Offline-at-runtime claim: no external runtime resources are referenced by
  the code, but a full offline run has not been tested end-to-end.

## Features partially implemented

- **Frontend dashboard:** only the service-health card exists and renders
  real API data; net worth, cash-flow, portfolio, and scenario views await
  CALC-001/UI-001.
- **Dependency locking:** versions are fully pinned (backend
  `requirements.lock.txt`, frontend `package-lock.json`), but runtime and
  dev Python dependencies share one lockfile (KI-005).
- **Security posture:** localhost binding, CORS allowlist, secret hygiene,
  and parameterized SQL are in place; authentication, HTTPS, rate
  limiting, and dependency auditing are not (SECURITY.md, AUTH-001).
- **Backup/export:** procedure documented in OPERATIONS.md §5 but not yet
  exercised (DATA-004 / KI-004).

## Not started

All of Phases 1–7: domain model, projection engine, tax engine, Social
Security, healthcare, withdrawals, Monte Carlo, optimizers, dashboard,
import/export/backup, authentication (required by the multi-user decision
D-002), reports, and the optional AI assistant.

## Known bugs / blockers / technical debt

- **KI-001:** port 8000 is occupied on this machine by an unrelated service
  (`python3 main.py --host 127.0.0.1 --port 8000`, pid 1074); the app uses
  `APP_PORT=8010` in `.env`.
- **KI-002:** deprecation warning from Starlette's `TestClient` (`httpx`
  → `httpx2`); cosmetic, revisit at next dependency update.
- **KI-003:** Docker artifacts untested (INFRA-004).
- **KI-004:** backup/restore procedures documented but not yet exercised.
- **KI-005:** `requirements.lock.txt` mixes runtime and dev dependencies.
- **KI-006:** no test-coverage measurement configured yet.
- Tooling note: `sudo` requires an interactive password on this machine;
  system installs were performed through `pkexec` (see `OPERATIONS.md`).
  `python3.12-venv` is unavailable, so **uv** manages the virtualenv.

## Operational status

- **Application startup status:** verified start/stop in session 1; servers
  are **currently stopped** (nothing is left running).
- **Database migration status:** `0001_baseline` applied to `retirement`
  (live) and recreated per test session in `retirement_test`.
- **Latest build & test results (2026-10-13):** `make lint` = 0 errors;
  `make test` = 9 backend + 3 frontend passed; `vite build` succeeded.
- **Last known-good commit:** `b5f1744` — Phase 0 baseline (52 files,
  2026-10-13). The follow-up commit that records this line touches docs
  only, so code identity with `b5f1744` is preserved.
- **Branch:** `main` (single root commit + docs follow-up).
