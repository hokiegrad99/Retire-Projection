# CHANGELOG.md

Notable user-visible changes, schema changes, and releases.
Format: newest first · dated entries · semantic-ish versions.

---

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
