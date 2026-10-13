# NEXT_SESSION.md — Resume here

## 1. Reload the project state (in order)

1. Read `PROJECT_STATE.md` (authoritative status).
2. Read this file.
3. Skim `IMPLEMENTATION_PLAN.md` (task IDs) and `FEATURE_MATRIX.md`.
4. Check the repository: `git log --oneline -5 && git status`.
   If docs and code disagree, **the code wins**.
5. Run startup checks: `make lint && make test` (expect **46 backend +
   3 frontend** tests green; PostgreSQL must be running).

Current branch: `main`. Development phase: **Phase 1 — DATA-001 done,
DATA-002 next.**

## 2. Exact task to continue

**DATA-002 — CRUD API for all domain objects (Phase 1, P0).**

Expose REST endpoints for: households, plans (incl. scenario duplication),
people, accounts (with allocations), liabilities, income streams, expenses —
over the existing Pydantic `*Create` schemas in `backend/app/schemas/finance.py`.

## 3. Relevant files and functions

- `backend/app/schemas/finance.py` — request schemas + all cross-field
  validation rules already exist; **reuse, don't duplicate, them**.
- `backend/app/models/` — `household/plan/person/account/...` ORM models;
  cascades and constraints documented in `ARCHITECTURE.md` §3.
- `backend/app/routers/health.py` — the router pattern to copy (prefix
  `/api`, tags, response shape conventions).
- `backend/app/main.py` — `create_app()` is where routers get registered.
- `backend/tests/conftest.py` — fixtures: `client`, `database`,
  `migrated_database`, `db_session` (truncates after each test),
  `expected_head`.
- `backend/alembic/versions/0002_financial_domain_model.py` — schema head.

## 4. Prerequisites and commands

```bash
export PATH="$HOME/.local/bin:$HOME/.cargo/bin:$PATH"   # uv on PATH
make test        # 46 + 3 green before you start
# after adding routes:
make check
cd backend && ../.venv/bin/python -m pytest tests/test_api_*.py -v
```

## 5. Expected result and acceptance tests

- Every entity has list/create/get/update/delete with OpenAPI docs at
  `/api/docs`; invalid payloads return 422 with field-level detail.
- Baseline protection: a request that would create a second baseline in a
  household returns a clear 409/400 (or is explicitly a promotion flow —
  decide and document in DECISIONS).
- Editing a scenario plan provably does not touch the baseline (invariant
  test — spec §13).
- All existing tests still pass; new API tests cover happy path + one
  validation failure per endpoint family.

## 6. Known pitfalls and unresolved decisions

- **Port:** use `APP_PORT=8010` (`.env`); 8000 is occupied (KI-001).
- **sudo is interactive**; system installs go through `pkexec`.
- `.env` is gitignored; edit via `write_file` if shell edits are needed.
  Never commit it; never log `DATABASE_URL`.
- Scenario duplication (DATA-003) will need a copy routine — design
  DATA-002's plan endpoints so duplication can be added without breaking
  them (parent_plan_id lineage exists; see DECISIONS D-011).
- Deferred schema work lives in DATA-012 (goals, employment periods,
  survivor/beneficiary) — do **not** invent tables ad hoc.
- Unresolved: state-vs-JSON error format preferences; pick RFC-7807-style
  `{"detail": ...}` (FastAPI default) and record it.
