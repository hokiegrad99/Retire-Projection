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
  touched by tests.
- `DATABASE_URL` is redirected before any app module loads, so the app's
  engine always binds to the test database during tests.
- No user financial data exists yet (Phase 0 has no domain tables).

## 3. Current suites (observed results, 2026-10-13)

| Suite | Count | Result | What it covers |
| --- | --- | --- | --- |
| `tests/test_app.py` | 5 | pass | localhost binding default, CORS list parsing, root endpoint, OpenAPI schema, Swagger UI |
| `tests/test_health.py` | 3 | pass | 200 + healthy body, migration revision visible after upgrade, no credential leakage |
| `tests/test_migrations.py` | 1 | pass | Alembic upgrade lands revision `0001` |
| `frontend/src/App.test.tsx` | 3 | pass | loading state, renders real health data, actionable error when API unreachable |
| **Total** | **12** | **all pass** | |

`make lint` must be clean (currently 0 findings).

Known warning: Starlette `TestClient` emits a deprecation notice about
`httpx` (KI-002) — cosmetic, tracked.

## 4. Reference validation plan (financial correctness)

No financial code exists yet. When CALC/TAX/SS work begins, add one file per
domain under `backend/tests/reference/` containing: source (IRS/state
publication + year), input fixture, expected output, tolerance, and the
actual result once executed. Rules:

- A tax/benefit module cannot be marked validated on "plausible-looking
  numbers" alone (spec §20).
- Regression scenarios: version-controlled plan JSON with expected annual
  outputs and explicit tolerances; expected changes must be explained in
  `SESSION_LOG.md` before the baseline is updated.
- Property/invariant tests to add with the engine: contributions+withdrawals
  reconcile to balances; assets−liabilities = net worth; scenario mutation
  never alters baseline; identical seed ⇒ identical simulation; depleted
  accounts never fund spending silently; taxes never double-counted.

## 5. Coverage

Coverage measurement is **not yet configured** (KI-006). Plan: add
`pytest-cov` + Vitest coverage reporting in QA-001 and record the baseline
numbers here. Do not claim coverage percentages until measured.

## 6. Manual / end-to-end verification

Procedure used in session 1 (repeat after significant changes):

1. `make lint && make test` → exit 0.
2. `make backend` → then:
   `curl http://127.0.0.1:8010/api/health` (or open in browser) → 200,
   `"status":"ok"`, `"database":{"connected":true}`.
3. `make frontend` → open `http://127.0.0.1:5173/` → health card renders
   with `ok / connected / 0001`; check `/api/health` through port 5173
   proves the proxy path.
4. Stop both; confirm ports 8010/5173 are released (`ss -ltn`).
5. Restart the API and confirm data still there (Phase 1+ acceptance).

## 7. End-to-end browser tests

Not yet set up (Playwright decision pending, QA-001). Vitest + Testing
Library covers component behavior for now.
