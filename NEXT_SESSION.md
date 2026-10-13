# NEXT_SESSION.md — Resume here

## 1. Reload the project state (in order)

1. Read `PROJECT_STATE.md` (authoritative status).
2. Read this file.
3. Skim `IMPLEMENTATION_PLAN.md` (task IDs) and `FEATURE_MATRIX.md`.
4. Check the repository: `git log --oneline -5 && git status`.
   If docs and code disagree, **the code wins**.
5. Run startup checks: `make lint && make test` (expect **71 backend +
   3 frontend** tests green; PostgreSQL must be running).

Current branch: `main`. Development phase: **Phase 1 — DATA-001 +
DATA-002 done, DATA-003 next.**

## 2. Exact task to continue

**DATA-003 — plans/scenarios management (Phase 1, P0):**

- **Duplicate** a plan (deep copy of all owned rows: people, accounts with
  allocations, liabilities, income streams, expenses) via
  `POST /api/plans/{plan_id}/duplicate` — sets `parent_plan_id` to the
  source (lineage), body allows a new `name` and `is_baseline: false`.
- Rename (already possible via `PATCH /api/plans/{id}` — verify + test).
- **Archive** a plan: add `archived_at` (or `is_archived`) to `plan` via
  migration `0003` + model/schema/API support; archived plans are excluded
  from default listings but remain readable.
- **Comparison** endpoint returning which fields differ between two plans
  (field-level diff of the *entities*, per spec §13 "identify which
  assumptions differ").

## 3. Relevant files and functions

- `backend/app/routers/plans.py` — plan item endpoints; add duplicate/
  archive here.
- `backend/app/services/crud.py` — service helpers; put the deep-copy
  routine in a new `app/services/scenarios.py` (keep crud.py generic).
- `backend/app/models/people.py` — `Plan` model (+ `parent_plan_id`).
- `backend/alembic/versions/0002_financial_domain_model.py` — schema head.
- `backend/tests/test_api_crud.py` — API test patterns to copy.

## 4. Prerequisites and commands

```bash
export PATH="$HOME/.local/bin:$HOME/.cargo/bin:$PATH"
make test                      # 71 + 3 green before you start
make migrate-revision MSG="data-003 plan archive flag"   # if schema changes
make check
```

## 5. Expected result and acceptance tests

- Duplicating a scenario copies **every** owned row; source untouched
  (invariant test comparing counts + balances); lineage set.
- Archived plans: hidden from `GET /api/households/{id}/plans` by default,
  visible with `?include_archived=true`, still individually readable.
- Comparison endpoint reports per-entity field diffs between two plans of
  the same household; mismatched households → 422.
- All existing tests still green.

## 6. Known pitfalls and unresolved decisions

- **Port:** `APP_PORT=8010` (8000 occupied, KI-001). **sudo** is
  interactive; system installs go via `pkexec`.
- `.env` is gitignored; never commit or log credentials.
- Deep-copy must also copy `account_allocation` rows and preserve Decimal
  precision; reuse service patterns, not ad-hoc SQL.
- Replacing allocation sets needs the two-phase flush pattern
  (`routers/accounts.py`) — remember it for any unique-constrained
  replace-set logic.
- Unresolved: archive semantics for the *baseline* plan (probably
  disallow archiving the current baseline — decide + document in
  DECISIONS).
