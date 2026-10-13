# DECISIONS.md — Append-only decision log

Entries are never rewritten; later decisions supersede earlier ones by
appending a new entry that references the old ID.

---

## D-001 — 2026-10-13 — Database: PostgreSQL from day one

- **Alternatives:** SQLite now with a later migration path; SQLite forever.
- **Rationale:** the app must eventually move to a production server;
  starting on Postgres removes a costly schema/data migration later, and the
  spec explicitly names Postgres for server deployment. SQLAlchemy/Alembic
  keep the door open either way.
- **Consequences:** a database server must run locally; tests provision a
  dedicated `retirement_test` database; connection details live in `.env`.

## D-002 — 2026-10-13 — Security model: multi-user over LAN/Internet

- **Alternatives:** localhost/single trusted user only; auth added later.
- **Rationale:** user decision — the production deployment will serve
  multiple users across a network, so authentication, sessions, CSRF
  protection, and HTTPS are architectural, not bolt-ons.
- **Consequences:** AUTH work (login, password hashing, session storage,
  HTTPS guidance) is scheduled inside Phase 1/2 rather than Phase 7; CORS is
  already settings-driven.

## D-003 — 2026-10-13 — First state tax module: New Jersey

- **Alternatives:** defer with a generic placeholder; no-income-tax state.
- **Rationale:** user's configured state, per spec section 8 ("prioritize
  the user's configured state first").
- **Consequences:** Phase 3 builds and reference-tests the NJ rules first;
  the state-rule interface must be general enough for relocation modeling
  later.

## D-004 — 2026-10-13 — Native development, Docker only for production

- **Alternatives:** install Docker locally; skip Docker entirely.
- **Rationale:** no Docker on the development machine and the user prefers
  native runs; the spec allows a documented non-Docker development option.
- **Consequences:** `Dockerfile`s and `docker-compose.yml` are written but
  unverified (INFRA-004 / KI-003); they must be built and tested before any
  deployment.

## D-005 — 2026-10-13 — Python tooling: uv (not python3-venv)

- **Alternatives:** `apt install python3.12-venv` (needs interactive sudo);
  `--break-system-packages` pip (rejected: fragile, system-polluting).
- **Rationale:** `ensurepip` is missing on this host and sudo requires a
  password the agent cannot enter; uv creates and manages the virtualenv
  without root and provides lockfile generation.
- **Consequences:** `Makefile` and `OPERATIONS.md` are uv-based; anyone
  reproducing the setup installs uv first.

## D-006 — 2026-10-13 — App port 8010 on this machine

- **Alternatives:** kill the squatter on 8000 (rejected: not ours to touch);
  change the code default.
- **Rationale:** `127.0.0.1:8000` is permanently occupied by an unrelated
  process (`python3 main.py --host 127.0.0.1 --port 8000`, pid 1074).
- **Consequences:** `.env` sets `APP_PORT=8010`; the Vite proxy reads the
  same value; compose publishes `127.0.0.1:8010`; code default stays 8000.

## D-007 — 2026-10-13 — Stack as specified: React+TS / FastAPI / SQLAlchemy / Alembic / pytest

- **Alternatives:** Django, Node-only backend, Prisma, plain SQL.
- **Rationale:** spec section 5 prescribes these unless the environment
  objects; the environment does not, and each is mature, well-tested, and
  matches the "libraries over custom implementations" rule.
- **Consequences:** modular monolith; calculation engine will live in pure
  Python modules importable without the web layer.

## D-008 — 2026-10-13 — Test databases: drop/recreate per run, app role gets CREATEDB

- **Alternatives:** fixtures inside the live DB; a separate superuser DSN
  for tests.
- **Rationale:** tests must never touch real financial data; granting
  CREATEDB to the local app role is the simplest correct isolation.
- **Consequences:** the production role must NOT have CREATEDB (note in
  SECURITY.md); test DB is recreated every session, so migrations are
  exercised from scratch each run.

## D-009 — 2026-10-13 — Health endpoint contract

- **Decision:** `GET /api/health` → 200 when the DB answers, else 503; body
  carries `status`, `version`, `service`, `database.{connected,latency_ms,
  migration_revision}`, `timestamp` — and never credentials. Alembic URL is
  injected from settings instead of `alembic.ini`.
- **Consequences:** Docker health checks and E2E probes share one contract;
  the frontend health view tests assert against the same shape.

## D-010 — 2026-10-13 — Open (deferred) decisions

- Scenario storage model: full copies vs. overlay/diff from baseline —
  decide when DATA-003 starts (materially affects schema and comparison UX).
- Splitting runtime vs. dev lockfiles (follow-up of KI-005).
- Coverage tooling and thresholds (KI-006).
