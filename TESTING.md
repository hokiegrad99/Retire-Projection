# TESTING.md

## 1. Commands

```bash
make test            # everything (backend + frontend)
make test-backend    # pytest  (requires PostgreSQL running)
make test-frontend   # vitest
make lint            # ruff (backend) + tsc (frontend)
make check           # lint + test — run before every commit
```

Individual runs:

```bash
cd backend && ../.venv/bin/python -m pytest -v
cd frontend && npx vitest run
```

## 2. Test data and isolation

- Tests run **only** against the dedicated database `retirement_test`,
  which is dropped and recreated at the start of each suite
  (`backend/tests/conftest.py`). The live `retirement` database is never
  touched by tests (and is never downgraded).
- `DATABASE_URL` is redirected before any app module loads, so the app's
  engine always binds to the test database during tests.
- The `db_session` fixture truncates all eight domain tables after every
  test, so tests cannot leak rows into each other; API tests get the same
  isolation from an autouse fixture in `test_api_crud.py`.
- Migration assertions compare against the `expected_head` fixture (never
  a hardcoded revision id), so adding a revision never breaks unrelated
  tests.
- The schema exists (migration `0002`) but **no user financial data** has
  been entered — only synthetic test rows, which are destroyed per test.

## 3. Current suites (observed results, 2026-10-13, `make check` exit 0)

| Suite | Count | Result | What it covers |
| --- | --- | --- | --- |
| `tests/test_api_crud.py` | 25 | pass | DATA-002 API: CRUD happy paths, 422/404/409 semantics, confirm-guarded deletes, baseline promotion with lineage, merged-record PATCH validation, spec §13 scenario-isolation invariant, OpenAPI surface |
| `tests/test_app.py` | 5 | pass | localhost binding default, CORS list parsing, root endpoint, OpenAPI schema, Swagger UI |
| `tests/test_health.py` | 3 | pass | 200 + healthy body, migration revision reported after upgrade (compared against the `expected_head` fixture, never a hardcoded id), no credential leakage |
| `tests/test_migrations.py` | 2 | pass | head applies cleanly; **downgrade → re-upgrade round trip** (including native enum types) restores the full schema |
| `tests/test_models_finance.py` | 11 | pass | PostgreSQL backstops: FK cascades (household→plans, plan→children, person→accounts), negative-balance CHECK, per-household single-baseline index, allocation uniqueness, date-order and adjustment-pair CHECKs, enum-value rejection, full-graph persistence/relations |
| `tests/test_schemas_finance.py` | 25 | pass | DATA-001 input validation: dates, amounts, rates, enums, unknown fields, cross-field rules (survivor pairing, one-time flows, adjustment pairs, allocation sets summing to 1) |
| `frontend/src/App.test.tsx` | 3 | pass | loading state, renders real health data, actionable error when API unreachable |
| **Total** | **74** | **all pass** | (71 backend + 3 frontend) |

`make lint` must be clean (0 findings; the documented E501 exception for
generated Alembic revisions is DECISIONS D-013).

Known warning: Starlette `TestClient` emits a deprecation notice about
`httpx` (KI-002) — cosmetic, tracked.

## 4. Reference validation plan (financial correctness)

No financial **calculations** exist yet. When CALC/TAX/SS work begins, add
one file per domain under `backend/tests/reference/` containing: source
(IRS/state publication + year), input fixture, expected output, tolerance,
and the actual result once executed. Rules:

- A tax/benefit module cannot be marked validated on "plausible-looking
  numbers" alone (spec §20).
- Regression scenarios: version-controlled plan JSON with expected annual
  outputs and explicit tolerances; expected changes must be explained in
  `SESSION_LOG.md` before the baseline is updated.
- Property/invariant tests to add with the engine: contributions+withdrawals
  reconcile to balances; assets−liabilities = net worth; scenario mutation
  never alters baseline; identical seed ⇒ identical simulation; depleted
  accounts never fund spending silently; taxes never double-counted.
  (Schema-level pieces of these — cascades, baseline protection, constraint
  rejection — are already covered by `test_models_finance.py`.)

## 5. Coverage

Coverage measurement is **not yet configured** (KI-006). Plan: add
`pytest-cov` + Vitest coverage reporting in QA-001 and record the baseline
numbers here. Do not claim coverage percentages until measured.

## 6. Manual / end-to-end verification

Procedure used in sessions 1–2 (repeat after significant changes):

1. `make lint && make test` (or `make check`) → exit 0.
2. `make backend` → then:
   `curl http://127.0.0.1:8010/api/health` (or open in browser) → 200,
   `"status":"ok"`, `"database":{"connected":true}` and a
   `migration_revision` equal to the current head (session 2 observed
   `"0002"`).
3. `make frontend` → open `http://127.0.0.1:5173/` → health card renders
   with `ok / connected` and the current revision; check `/api/health`
   through port 5173 to prove the proxy path.
4. Stop both; confirm ports 8010/5173 are released (`ss -ltn`).
5. Restart the API and confirm saved data persists (Phase 1+ acceptance).

## 7. End-to-end browser tests

Not yet set up (Playwright decision pending, QA-001). Vitest + Testing
Library covers component behavior for now.
