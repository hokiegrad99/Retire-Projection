# NEXT_SESSION.md — Resume here

## 1. Reload the project state (in order)

1. Read `PROJECT_STATE.md` (authoritative status).
2. Read this file.
3. Skim `IMPLEMENTATION_PLAN.md` (task IDs) and `FEATURE_MATRIX.md`.
4. Check the repository: `git log --oneline -5 && git status`.
   If docs and code disagree, **the code wins**.
5. Run startup checks: `make lint && make test` (expect 9 backend + 3
   frontend tests green; PostgreSQL must be running).

Current branch: `main`. Development phase: **Phase 0 complete → Phase 1**.

## 2. Exact task to continue

**DATA-001 — Financial domain model (Phase 1, first task).**

Design and implement the normalized schema for households, people,
accounts/asset classes (with tax treatment), liabilities, income streams,
and expenses/budgets, plus a protected baseline plan and independent
scenarios (ties to DATA-003). For DATA-001 itself, the minimum vertical
slice is: household + people + accounts.

## 3. Relevant files and functions

- `backend/app/db.py` — `Base` (declarative, empty) is where models hang off.
- `backend/app/config.py` — settings; `PROJECT_ROOT` points at the repo root.
- `backend/alembic/versions/0001_baseline.py` — current schema head.
- `backend/tests/conftest.py` — `database` / `migrated_database` fixtures
  (they drop & recreate the `retirement_test` database).
- Create new models under `backend/app/` (suggest `backend/app/models/`),
  then `cd backend && ../.venv/bin/alembic revision --autogenerate -m "..."`.

## 4. Prerequisites and commands

```bash
export PATH="$HOME/.local/bin:$HOME/.cargo/bin:$PATH"   # uv on PATH
make test        # lint-free, all green before you start
make migrate     # bring DATABASE_URL schema to head
make migrate-revision MSG="add household"   # after writing models
```

## 5. Expected result and acceptance tests

- New migration applies to both `retirement` and `retirement_test`.
- New unit tests cover validation rules (dates, amounts, enums) and pass.
- `GET /api/health` still reports the new `migration_revision` on the live DB.
- No changes to baseline/scenario protection semantics (none exist yet —
  document the choice in `DECISIONS.md` when introduced).

## 6. Known pitfalls and unresolved decisions

- **Port:** use `APP_PORT=8010` (`.env`); port 8000 is permanently occupied
  by another process (KI-001).
- **sudo is interactive** on this machine; system installs go through
  `pkexec` (see `OPERATIONS.md` → "System administration"). Do not attempt
  password entry.
- **`.env` is gitignored**; file-editing tools may refuse it — use
  `write_file` (which created it) or shell redirection. Never commit it.
- Tests must keep using `retirement_test`; never point tests at `retirement`.
- Unresolved decisions to raise only if they materially block work:
  scenario-inheritance model (copy-on-write vs. diff patches) — decide when
  DATA-003 starts; see DECISIONS D-010.
