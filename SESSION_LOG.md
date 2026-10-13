# SESSION_LOG.md — Per-session work record

Append-only: one section per session, newest at the bottom.

---

## Session 1 — 2026-10-13 — Project foundation (Phase 0)

**Session objective:** analyse the requirements, resolve the
architecture-critical questions with the user, and complete Phase 0:
repository, continuity documents, chosen stack, runnable database-connected
application, health check, automated tests, reproducible startup workflow —
with honest, observed results.

**Files created or modified**

- Repo scaffolding: `.gitignore`, `.env.example`, `.env` (local, not
  committed), `Makefile`, `README.md`, `.dockerignore`.
- Backend: `backend/pyproject.toml`, `backend/requirements.lock.txt`,
  `backend/app/{__init__,version,config,db,main}.py`,
  `backend/app/routers/{__init__,health}.py`,
  `backend/alembic.ini`, `backend/alembic/{env.py,versions/0001_baseline.py,…}`,
  `backend/tests/{conftest,test_health,test_app,test_migrations}.py`.
- Frontend: `frontend/package.json`, `package-lock.json`, `tsconfig.json`,
  `vite.config.ts`, `vitest.setup.ts`, `index.html`,
  `frontend/src/{main.tsx,App.tsx,App.test.tsx,index.css,vite-env.d.ts}`,
  `frontend/src/api/health.ts`.
- Deployment (unverified): `Dockerfile.backend`, `frontend/Dockerfile`,
  `frontend/nginx.conf`, `docker-compose.yml`.
- Documentation: all 12 continuity documents + this log.

**Tasks completed:** INFRA-001 (repo + environment), INFRA-002 (tracking
documents), INFRA-003 (runnable app + DB + health check + tests +
reproducible workflow). Decisions D-001…D-010 recorded.

**Commands and tests executed (actual results)**

- Environment inspection: Docker **not installed**; Python 3.12.3; Node
  24.16.0 / npm 11.13.0; git 2.43; `python3.12-venv` missing (ensurepip
  unavailable); `sudo` requires a password.
- `uv 0.13.0` installed; `uv venv .venv --python python3 --seed`;
  `uv pip install -e "backend[dev]"` → 37 locked packages.
- System installs via `pkexec apt-get install -y postgresql` → PostgreSQL
  **16+257build1.1** set up successfully.
- DB provisioning script run as root: role `retire_app` (password set,
  CREATEDB), database `retirement` created; login verified as `retire_app`.
- `make migrate` → Alembic `Running upgrade → 0001`; verified
  `SELECT version_num FROM alembic_version` = `0001` on the live DB.
- `make test-backend` → **9 passed** (config/app wiring, health incl.
  migration revision and credential-leak check, migration pipeline).
  Earlier red run was recorded honestly: before PostgreSQL existed, the 4
  DB tests failed with the actionable fixture message (expected).
- `npm install` (102 packages); `npx tsc --noEmit` → clean; `npm test` →
  **3 passed** (initially 1 failed on an incorrect assertion about copy
  wording — assertion fixed to match the UI text, not the code changed);
  `npm run build` → built in ~400 ms (221.67 kB JS / 69.35 kB gzip).
- `make lint` → ruff initially reported 4 findings (2 import-sort, 1 `UP017`,
  1 line-too-long) — fixed with `ruff --fix` + one manual line split; now
  **All checks passed**, `LINT_RC=0`.
- Live E2E: API on `127.0.0.1:8010` (port 8000 was already occupied —
  uvicorn logged `address already in use`), `/api/health` → HTTP 200
  `{"status":"ok",…,"database":{"connected":true,"latency_ms":1.85,…}}`;
  root `/` → HTTP 200; Vite dev server on `127.0.0.1:5173` served the UI
  (root div present) and its `/api` proxy returned the same healthy body;
  both processes stopped cleanly and the ports were released.

**Outstanding problems**

- INFRA-004: Docker/compose artifacts untested (no Docker on this host).
- KI-002: Starlette TestClient deprecation warning (`httpx` → `httpx2`).
- Backup/restore, coverage, dependency-vulnerability scanning not yet set
  up (tracked in plan/known issues).

**Next recommended action:** start session 2 with `make lint && make test`,
then begin **DATA-001** (financial domain model) per `NEXT_SESSION.md`.

**Session 1 addendum — final completion check (same session)**

- Spec-conformance gaps found and closed: `PROJECT_STATE.md` gained the
  spec-required "Features partially implemented" category; the requirements'
  variant document spellings are now documented in `README.md`.
- Bug found by executing the documented commands: `make setup` failed
  (`uv venv` exit 2 when `.venv` already exists). Fixed in the Makefile to
  skip creation when the venv is present; verified `make setup` returns 0
  on consecutive runs (idempotent).
- Re-verified after the fix: `make check` exit 0 (ruff clean, tsc clean,
  9 backend + 3 frontend tests passed), `docker-compose.yml` parses as
  valid YAML via PyYAML, all 12 continuity documents present and non-empty,
  `make lock` regenerated the lockfile with zero drift, and `make test`
  was re-run after `make setup` rewrote the environment (still green).

---

## Session 2 — 2026-10-13 — Phase 1 begins: DATA-001 financial domain model

**Session objective:** implement DATA-001 (domain model, migrations,
validation, tests) as the first Phase 1 task, with honest verification.

**Files created or modified**

- Models: `backend/app/models/{__init__,enums,people,assets,flows}.py`
  (8 tables: household, plan, person, account, account_allocation,
  liability, income_stream, expense).
- Schemas: `backend/app/schemas/{__init__,finance}.py` — 8 request
  schemas + cross-field validators.
- Migration: `backend/alembic/versions/0002_financial_domain_model.py`
  (autogenerated, hand-reviewed, enum-drop added to downgrade);
  `backend/alembic/env.py` now imports `app.models` for autogenerate.
- Tests: `backend/tests/{test_schemas_finance,test_models_finance}.py`
  (new), `test_migrations.py` (rewritten: head-agnostic + round trip),
  `test_health.py` (head-agnostic), `conftest.py` (added `expected_head`
  and `db_session` fixtures).
- Config/quality: `backend/pyproject.toml` (version 0.2.0, per-file
  E501 exception for generated revisions), `app/version.py` (0.2.0).
- Docs: PROJECT_STATE, NEXT_SESSION, IMPLEMENTATION_PLAN (DATA-001 done,
  DATA-012 added), FEATURE_MATRIX (domain rows → partial w/ tests),
  ARCHITECTURE §3/§10 rewritten for the real schema, DECISIONS
  D-011…D-014, TESTING §3, CHANGELOG 0.2.0, README status.

**Tasks completed:** DATA-001 fully (acceptance met: migrations apply,
validation rejects bad inputs, unit tests pass).

**Commands and tests executed (actual results)**

- Startup `make check` → exit 0 (baseline, 9+3 tests).
- First mapper-configuration probe failed on a typo in my one-liner
  (`models.Base` instead of `app.db.Base`); corrected probe → 8 tables
  registered cleanly. A real back-population conflict on
  `IncomeStream.owner_person` was caught during review *before* any test
  run and fixed (one-way relationship).
- Ruff round 1: **59 findings** — 14×UP042 (converted all enums to
  `StrEnum`, D-014), 6×F821 (self-referential annotations; fixed with
  `from __future__ import annotations`), 3×E501 (split strings), plus
  generated-revision noise. Ruff round 2: 52 → after `--fix` and the
  E741 rename (`l` → `liab`): only the 51 generated-DDL long lines
  remained → resolved by the documented per-file exception (D-013),
  not by touching the check for hand-written code.
- Design review removed the `baseline can't have a parent` constraint
  (breaks promotion-with-lineage) before the migration was generated;
  the single-baseline partial index remains the enforced invariant.
- `alembic revision --autogenerate` → inspected full DDL (8 tables,
  cascades, CHECKs, partial index) → renamed revision to `0002` →
  `make migrate` → live DB reports `0002 (head)` with all 8 tables.
- **Final `make check` → exit 0:** ruff clean, tsc clean, **46 backend
  tests** (5 app + 3 health + 2 migrations + 11 models + 25 schemas),
  **3 frontend tests**.
- Live E2E: API on `127.0.0.1:8010` → `/api/health` HTTP 200 with
  `"version":"0.1.0"` at that moment (subsequently bumped to 0.2.0 and
  re-checked by the suite), `migration_revision:"0002"`,
  `database.connected:true`; clean shutdown, port released.

**Outstanding problems**

- No new defects. Old ones unchanged (KI-001…KI-008; INFRA-004 blocked).
- API/UI over the model still absent (that is DATA-002, the next task).

**Next recommended action:** start session 3 with `make lint && make
test`, then **DATA-002 — CRUD API** per `NEXT_SESSION.md`.

---

## Session 3 — 2026-10-13 — DATA-002: CRUD API over the domain model

**Session objective:** expose the DATA-001 domain through a tested,
OpenAPI-documented REST API with baseline protection and safe deletes.

**Files created or modified**

- Routers: `backend/app/routers/{households,plans,people,accounts,
  liabilities,income_streams,expenses}.py` (38 endpoints); registered in
  `app/main.py`.
- Services: `backend/app/services/{__init__,crud}.py` — get_or_404,
  create/patch/delete helpers, merged-record validation, ownership guards,
  baseline promotion.
- Schemas: `app/schemas/finance.py` +7 Read models, +7 Patch models,
  extracted `validate_allocation_set`.
- Infra: `app/db.py` gained `get_db`/`DbSession` (Annotated dependency).
- Tests: `backend/tests/test_api_crud.py` (25 tests).
- Config/docs: version 0.3.0; ARCHITECTURE §5/§10, DECISIONS D-015…D-017,
  PROJECT_STATE, NEXT_SESSION, IMPLEMENTATION_PLAN, FEATURE_MATRIX,
  TESTING, CHANGELOG, README updated.

**Tasks completed:** DATA-002 fully (acceptance: CRUD + OpenAPI + explicit
validation errors + baseline protection + §13 invariant test).

**Commands and tests executed (actual results, including red states)**

- Startup `make check` → exit 0 (46+3).
- First wiring probe failed: my `main.py` import edit had dropped `health`
  (NameError) — fixed. Route-count probe then showed only 5 routes,
  which turned out to be a *counting artifact*: newer Starlette wraps
  included routers lazily (`_IncludedRouter`); direct inspection showed
  8 routers registered with all routes (health 1, households 7, people 5,
  …).
- Ruff round 1: 35×B008 (`Depends()` in parameter defaults) + 4×UP047 →
  fixed at the cause: `Annotated[Session, Depends(get_db)]` alias
  (`DbSession`) and PEP 695 type parameters; the sed migration then
  exposed a real SyntaxError in two delete handlers (dependency param
  after a defaulted query param) — reordered.
- New API tests first run: 24/26; two genuine bugs found:
  1. runtime PATCH `ValidationError`/`ValueError` escaped as **500**
     (FastAPI only auto-converts body-parse errors) → service layer now
     converts to **422** with the standard detail shape;
  2. allocation-set replacement hit `UniqueViolation` on
     `uq_account_allocation_class` (insert-before-delete ordering) →
     two-phase flush fix (D-017).
- Also fixed two E501s in the new test file (split lines).
- **Final `make check` → exit 0:** ruff clean, tsc clean, **71 backend
  tests** (25 api_crud + 25 schemas + 11 models + 5 app + 3 health +
  2 migrations), **3 frontend tests**.
- Live E2E smoke (HTTP against the running API): health 200 (v0.3.0,
  revision 0002) → create household→baseline→person→account(allocations)
  → 400 without confirm → 204 with confirm → lists empty again (live DB
  left exactly as found); port 8010 released.

**Outstanding problems**

- No new defects after the fixes. KI-001…KI-008 unchanged; INFRA-004
  still blocked. No pagination/optimistic locking yet (documented in
  ARCHITECTURE §10; revisit with PERF-001/AUTH-001).

**Next recommended action:** start session 4 with `make lint && make
test`, then **DATA-003 — scenario duplication/archive/comparison** per
`NEXT_SESSION.md`.
