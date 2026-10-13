# FEATURE_MATRIX.md — Requested feature → task / status / tests

Status legend: `done` · `partial` · `not started` · `blocked`.
Test column: automated test names, or the manual procedure used.

## Foundation & continuity (spec §2, §4, §5)

| Feature | Task | Pri | Status | Source | Tests | Notes / limitations |
| --- | --- | --- | --- | --- | ---| --- |
| Runs locally, no cloud required | INFRA-003 | P0 | done | Makefile, .env | E2E probe (session 1) | Runtime offline-capable; setup still needs network for `uv`/`npm install` |
| Local database under user control | D-001, INFRA-003 | P0 | done | `app/db.py`, Postgres 16 | `test_health_requires_database` | Role/db creation documented in OPERATIONS.md |
| Docker Compose packaging | INFRA-004 | P1 | **blocked** | `docker-compose.yml`, Dockerfiles | — | Written, never built (no Docker here) |
| Non-Docker dev option | INFRA-001 | P1 | done | Makefile + docs | `make lint`, `make test` | Primary path on this machine |
| Persistent data + migrations | INFRA-003 | P0 | partial | Alembic `0001` | `test_baseline_migration_applies` | No financial tables yet (DATA-001) |
| Health check + useful errors | INFRA-003 | P0 | done | `app/routers/health.py` | `test_health_*` (3) | 200/503 contract, D-009 |
| Auto-generated API docs | INFRA-003 | P2 | done | FastAPI `/api/docs` | `test_openapi_document_is_served`, `test_swagger_docs_are_served` | Served locally |
| Continuity documents (12) | INFRA-002 | P0 | done | repo root | Manual (protocol in PROJECT_STATE) | Maintained via session protocol |
| Lockfiles / reproducible deps | INFRA-001 | P0 | partial | `requirements.lock.txt`, `package-lock.json` | `npm ci` path in Dockerfile | Single lock mixes dev deps (KI-005) |
| Configurable host/port, localhost default | INFRA-003 | P0 | done | `.env`, `config.py` | `test_settings_bind_to_localhost_by_default` | Port 8010 on this machine (D-006) |

## Financial domain model (spec §6)

| Feature | Task | Pri | Status | Source | Tests | Notes |
| --- | --- | --- | --- | --- | --- | --- |
| Household / people / dependents | DATA-001 / DATA-002 | P0 | partial | models, schemas, `routers/households.py`, `routers/people.py`, `services/crud.py` | `test_schemas_finance.py`, `test_models_finance.py`, `test_api_crud.py` | Full CRUD API live; UI pending; goals/employment periods → DATA-012 |
| Accounts & assets (all types), tax treatment, allocation | DATA-001 / DATA-002 | P0 | partial | models, `routers/accounts.py` | `test_api_crud.py` (allocations, owner guard, 2×422) | 24 account types, allocation sets summing to 1; withdrawal rules wait for CALC (D-012) |
| Liabilities (mortgage…cards), amortization terms | DATA-001 / DATA-002 | P0 | partial | models, `routers/liabilities.py` | `test_api_crud.py` (payoff date order via API) | Amortization math in CALC-013 |
| Income streams (salary…windfalls) | DATA-001 / DATA-002 | P0 | partial | models, `routers/income_streams.py` | `test_api_crud.py` (survivor 422, owner-change guard) | Survivor rules on stream level; plan-level beneficiaries → DATA-012 |
| Expenses & budgets (phases, inflation by category) | DATA-001 / DATA-002 | P0 | partial | models, `routers/expenses.py` | `test_api_crud.py` (merged-record re-validation) | One age-adjustment per row (split rows for multi-step); relocation/renovation use `other` + detail |
| Multiple plans/scenarios, protected baseline | DATA-001 / DATA-002 / DATA-003 | P0 | partial | `plan` table, partial unique index, `routers/plans.py` | `test_api_crud.py` (409, promotion, confirm-guarded delete, §13 invariant) | Protection + promotion live; duplication/archive/compare = DATA-003 |
| Import/export/backup/restore | DATA-004 | P1 | not started | — | — | Restore must be tested (BACKUP-001) |

## Calculation, taxes, income (spec §7–13)

| Feature | Task | Pri | Status | Notes |
| --- | --- | --- | --- | --- |
| Deterministic projection engine | CALC-001 | P0 | not started | Documented annual sequence required |
| Federal tax engine, effective-dated rules | TAX-001/003 | P0 | not started | Reference cases mandatory |
| New Jersey state tax + relocation | TAX-002 | P0 | not started | D-003 |
| Roth conversions, RMDs | TAX-004, CALC-011 | P1 | not started | Real engine only, no AI math |
| Social Security claiming strategies | CALC-010 | P0 | not started | |
| Pensions & annuities | DATA-010 | P1 | not started | |
| Healthcare / Medicare / IRMAA / LTC | CALC-012 | P0 | not started | Effective-dated assumptions |
| Debt amortization, real-estate events | CALC-013 | P1 | not started | Home equity not spendable by default |
| Withdrawal strategies | OPT-005 | P1 | not started | Heuristic vs optimized must be distinguished |

## Risk, optimization, UX (spec §12–19)

| Feature | Task | Pri | Status | Notes |
| --- | --- | --- | --- | --- |
| Monte Carlo (seeded, reproducible) | SIM-001 | P0 | not started | Success criterion always displayed |
| Stress tests / sensitivity / backtest | SIM-002/003 | P1 | not started | |
| Scenario comparison UI | DATA-003, UI-010 | P0 | not started | |
| Optimizers (Roth, SS, date, spending) | OPT-001…005 | P1 | not started | Engine-computed only |
| Dashboard & charts (all from real results) | UI-001 | P1 | partial | Health/status card only; no financial charts yet |
| Data-entry modules | UI-002 | P1 | not started | |
| Reports (print/PDF) | UI-011 | P2 | not started | |
| Authentication for network access | AUTH-001 | P0 | not started | Required by D-002 before exposure |
| Optional plan-aware AI assistant | AI-001 | P2 | not started | Opt-in, tool-calling only, after Phase 4 |

## Security (spec §18)

| Feature | Task | Status | Evidence |
| --- | --- | --- | --- |
| Local-only default binding | INFRA-003 | done | `test_settings_bind_to_localhost_by_default`, `.env` |
| No secrets in logs/code | INFRA-003 | done | `test_health_never_leaks_credentials`; `.gitignore` excludes `.env` |
| Parameterized DB access | INFRA-003 | done | SQLAlchemy `text()` params / ORM only |
| Authentication / sessions / CSRF | AUTH-001 | not started | Before any non-localhost exposure |
| HTTPS guidance | SEC-001 | partial | SECURITY.md documents requirement; no reverse proxy yet |
| Dependency vulnerability checks | SEC-001 | not started | Planned: `pip-audit` / `npm audit` in `make check` |
| Threat model documentation | SEC-001 | partial | SECURITY.md exists; validate in Phase 7 |
