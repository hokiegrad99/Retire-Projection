# CHANGELOG.md

Notable user-visible changes, schema changes, and releases.
Format: newest first · dated entries · semantic-ish versions.

---

## 0.3.0 — 2026-10-13 — CRUD API over the domain model (DATA-002, Phase 1)

- **API:** 38 REST endpoints (households, plans, people, accounts with
  allocations, liabilities, income streams, expenses) with OpenAPI docs;
  201/204/404/409/422 semantics and field-level validation details.
- **Baseline protection:** a second baseline cannot be created (409);
  promoting a scenario via `PATCH {"is_baseline": true}` demotes the old
  baseline and keeps lineage; deleting a household or the baseline plan
  requires `?confirm=true`.
- **Safety guards:** owner-person must belong to the plan (422); deleting a
  person who still owns accounts is refused (409); PATCH re-validates the
  merged record so partial updates cannot violate cross-field rules.
- **Tests:** +25 API tests (71 backend total, all green), including the
  spec §13 invariant that editing a scenario never touches the baseline;
  live HTTP smoke verified end-to-end.
- Bug fixes found by those tests: runtime PATCH validation now returns 422
  (was 500); allocation-set replacement uses a two-phase flush to satisfy
  the unique constraint.

## 0.2.0 — 2026-10-13 — Financial domain model (DATA-001, Phase 1)

- **Schema:** migration `0002` adds 8 tables — `household`, `plan`
  (baseline/scenario lineage + per-household single-baseline index),
  `person`, `account` (24 account types, tax treatment, rates),
  `account_allocation`, `liability`, `income_stream`, `expense` — with
  FK cascades and CHECK constraints throughout.
- **Validation:** Pydantic input schemas for every entity (`app/schemas/`):
  date ordering, non-negative money, rate ranges, survivor-rule pairing,
  one-time-flow rules, allocation sets summing to 1, adjustment pairs.
- **Tests:** 36 new (25 schema + 11 model/DB) plus a migration
  downgrade/re-upgrade round trip; total suite now 46 backend + 3 frontend,
  all passing; `E2E` health reports `migration_revision: 0002`.
- Decisions D-011…D-014 recorded (snapshot ownership, deferred schema
  elements → DATA-012, lint scope, enum representation).
- No API/UI changes yet — DATA-002 (CRUD API) is next.

## 0.1.0 — 2026-10-13 — Project foundation (Phase 0)

- Initial repository with the full continuity-documentation system
  (PROJECT_STATE, IMPLEMENTATION_PLAN, ARCHITECTURE, DECISIONS, SESSION_LOG,
  NEXT_SESSION, FEATURE_MATRIX, TESTING, CHANGELOG, OPERATIONS,
  SECURITY, KNOWN_ISSUES).
- Backend skeleton: FastAPI app with settings, SQLAlchemy engine, and
  `GET /api/health` (200/503 contract, migration revision reporting).
- Alembic migration pipeline with baseline revision `0001`
  (**schema:** `alembic_version` bookkeeping only; no financial tables yet).
- Local PostgreSQL 16 provisioned: database `retirement`, role `retire_app`.
- Frontend skeleton: React 19 + TypeScript (Vite 8) health dashboard that
  renders live service status; dev proxy configured from `.env`.
- Test suites: 9 backend (pytest) + 3 frontend (vitest); all passing.
  `make lint`, `make test`, `make migrate`, `make backend`, `make frontend`
  verified working on this machine.
- Production deployment artifacts (`docker-compose.yml`, Dockerfiles,
  nginx config) written but **not yet verified** (INFRA-004).
