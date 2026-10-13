# ARCHITECTURE.md

Last updated: 2026-10-13 (Phase 0). Amend this file in the same change that
alters the architecture, and record the rationale in `DECISIONS.md`.

## 1. Technology stack and rationale

| Layer | Choice | Why |
| --- | --- | --- |
| Frontend | React 19 + TypeScript, built by Vite 8 | Spec §5 preference; mature ecosystem; Vite bundles everything locally (offline-friendly) |
| UI tests | Vitest 5 + Testing Library (jsdom) | Vite-native runner, no extra framework |
| Backend | Python 3.12 + FastAPI + Pydantic 2 | Spec §5; automatic OpenAPI; strict validation |
| DB access | SQLAlchemy 2 (declarative) | Spec §5; ORM with explicit relationships; keeps SQL out of business logic |
| Migrations | Alembic | Spec §5; revision chain per env |
| Database | PostgreSQL 16 (D-001) | Production server target from day one |
| Financial math | Pure Python modules (planned) + `decimal` for currency | Spec §7; testable without the web layer |
| Python tooling | uv + `requirements.lock.txt` (D-005) | Reproducible installs without root |
| Charts | TBD in Phase 1 (mature library, self-hosted assets) | Must not pull from a CDN |
| Packaging | Docker/Compose for production (D-004), native runs locally | Spec §5 with documented non-Docker option |
| Monolith | Modular monolith, single backend process | Spec: no microservices without a concrete need |

## 2. Application components and boundaries

```
browser ── HTTP ──> Vite dev server (5173) ── proxy /api ──> FastAPI (:8010)
   │                                                       │
   │ (production: nginx serves static bundle and proxies) │
   ▼                                                       ▼
React SPA                                          routers (HTTP only)
                                                        │
                                                        ▼
                                            services / calculation engine   ← Phase 1+
                                                        │ pure Python,
                                                        │ no FastAPI imports
                                                        ▼
                                              SQLAlchemy repositories
                                                        │
                                                        ▼
                                                  PostgreSQL 16
```

Hard boundaries:

1. **Routers** translate HTTP ↔ Pydantic schemas; no financial logic.
2. **Calculation engine** (future `backend/app/calc/`) is pure: takes domain
   objects + assumptions, returns structured results. It must be importable
   and testable with zero HTTP/DB involvement.
3. **Persistence** is isolated behind repositories; migrations never run
   implicitly at request time.
4. **Frontend** talks to the API only (no direct DB, no business math in UI
   beyond display formatting).

## 3. Database schema and relationships

Current schema (revision `0001`): bookkeeping only — `alembic_version`.
The financial domain model arrives with DATA-001; its design must cover
spec §6: households → people (roles, DOB, longevity, retirement dates),
accounts (tax treatment, allocation, fees), liabilities, income streams,
expenses/budgets, plans/scenarios. Planned relationships: `household 1—*`,
`plan 1—* scenario` with a protected baseline flag, FKs with RESTRICT on
financial records, CHECK constraints on amounts/dates.

## 4. Financial calculation architecture (planned)

- Annual stepping by default, monthly refinement for timing-sensitive
  events; a fixed, documented ordering: income → contributions → returns &
  fees → taxes → required distributions → withdrawals → expenses →
  rebalancing/one-off events.
- Currency math in `decimal.Decimal` with documented rounding at
  reporting boundaries; floats only for statistical simulation outputs.
- Outputs are machine-readable structures (per-year rows: income, expenses,
  taxes, contributions, withdrawals, balances, net worth, estate, shortfalls)
  consumed by UI, reports, and tests alike.
- Unfunded expenses are recorded as shortfalls; accounts never go silently
  negative; borrowing must be an explicit rule.

## 5. API design

- Prefix `/api`; JSON; OpenAPI at `/api/openapi.json`, interactive docs at
  `/api/docs` (served by the same app — no external resources).
- Errors: FastAPI/Pydantic validation responses (422) with field-level detail;
  domain errors will map to 4xx with machine-readable codes in Phase 1.
- Phase 0 surface: `GET /api/health` (contract in D-009) and `GET /`.
- REST resources are plural nouns (`/api/households`, `/api/accounts`, …),
  created in DATA-002.

## 6. Security model

See `SECURITY.md` for the full threat model. Architecturally: localhost
binding by default (`.env`), CORS allowlist from settings, credentials only
in `.env`/environment (gitignored), no secrets in code/logs (health probe
logs exception class only), parameterized SQL everywhere via SQLAlchemy
text/ORM. Multi-user auth (D-002) will be added in Phase 1/2 as a router
middleware with hashed passwords and server-side sessions.

## 7. Dependency and integration decisions

- No runtime calls to external services; no CDN assets; system fonts only.
- Lockfiles: `backend/requirements.lock.txt` (pip-freeze of the venv) and
  `frontend/package-lock.json` (`npm ci` in Docker).
- Third-party services: none. Optional future AI assistant is opt-in and
  separable (spec §19).

## 8. Deployment architecture

- **Local (current):** `make backend` + `make frontend`, native Postgres.
- **Production (planned, unverified — INFRA-004):** `docker compose up`
  runs `db` (volume, port not published), `api` (published on
  `127.0.0.1:8010`, migrations run at container start), `web` (nginx,
  published on 8080, proxies `/api`, CSP header). HTTPS termination is not
  yet included — required before remote access (SEC-001).

## 9. Data flow and calculation flow

User input → validated Pydantic schema → repository → DB.
Read path: API request → service (loads plan + scenario) → calculation
engine → structured results → (cached only with reliable invalidation) →
JSON → charts. Monte Carlo (Phase 4) reuses the same engine per path with a
seeded RNG.

## 10. Important limitations (current)

- No financial calculations exist yet; any UI numbers before Phase 1 are
  service-health facts only.
- Docker artifacts are written but unexecuted (INFRA-004).
- Single lockfile mixes runtime/dev Python deps (KI-005).
- No coverage gate (KI-006), no automated dependency audit yet (SEC-001).
- The `retire_app` role has CREATEDB (dev convenience, D-008) — must be
  removed in production (SECURITY.md).
