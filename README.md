# Retire Projection

A local-first retirement and financial planning platform: household modeling,
year-by-year deterministic projections, tax-aware planning, scenario
comparison, Monte Carlo simulation, and strategy optimizers. You own the data;
everything runs on your machine with no cloud services and no subscription.

> **Status: Phase 0 complete** (project foundation: repository, continuity
> documents, database, health-checked API, tested frontend skeleton).
> The financial features arrive in Phases 1–7 — see `IMPLEMENTATION_PLAN.md`.

## Documentation index

| Document | Purpose |
| --- | --- |
| `PROJECT_STATE.md` | Authoritative current status — **read this first** |
| `NEXT_SESSION.md` | Where to resume in a new AI/human session |
| `IMPLEMENTATION_PLAN.md` | Phased roadmap with task IDs and acceptance criteria |
| `ARCHITECTURE.md` | Stack, components, data/calculation flow, boundaries |
| `DECISIONS.md` | Append-only architecture decision log |
| `FEATURE_MATRIX.md` | Every requested feature → task ID, status, tests |
| `SESSION_LOG.md` | Per-session work record |
| `TESTING.md` | Test commands, reference cases, coverage |
| `OPERATIONS.md` | Install, run, back up, restore, deploy |
| `SECURITY.md` | Threat model and security limitations |
| `KNOWN_ISSUES.md` | Confirmed defects and workarounds |
| `CHANGELOG.md` | User-visible changes |

## Quick start (development)

Prerequisites: `uv` (Python toolchain), Node.js 20+, PostgreSQL running
locally. Full details in `OPERATIONS.md`.

```bash
cp .env.example .env        # then set your DATABASE_URL password
make setup                  # venv + backend (editable) + npm install
make migrate                # apply database migrations
make test                   # backend + frontend test suites
make backend                # API on http://127.0.0.1:8010 (APP_PORT in .env; health: /api/health)
make frontend               # UI on http://127.0.0.1:5173
```

The app binds to localhost by default and requires no internet access at
runtime. Note: port 8000 is already in use by another local service on this
machine, so `.env` sets `APP_PORT=8010` (see KNOWN_ISSUES KI-001).
`docker-compose.yml` describes the production deployment target but
has not yet been verified (INFRA-004).
