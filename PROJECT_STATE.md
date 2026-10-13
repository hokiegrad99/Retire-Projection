# PROJECT_STATE.md — Authoritative project status

> **Session startup protocol:** read this file first, then `NEXT_SESSION.md`,
> then skim `IMPLEMENTATION_PLAN.md` / `FEATURE_MATRIX.md`. The repository is
> the source of truth wherever documentation and code disagree.

- **Checkpoint:** 2026-10-13, end of session 3 (see `SESSION_LOG.md`)
- **Purpose / scope:** a local-first, subscription-free retirement and
  financial planning platform, running locally with an eventual move to a
  production server.
- **Current development phase:** **Phase 1 in progress — DATA-001 and
  DATA-002 done; DATA-003 (scenario management) is next.**

## Completion estimates

| Area | Estimate | Notes |
| --- | --- | --- |
| Phase 0 — foundation | 95% | Exit criteria met; INFRA-004 still blocked (KI-003) |
| Phase 1 — MVP planning app | ~30% | 2 of 9 tasks done (DATA-001, DATA-002); UI/engine remain |
| Phase 2 — retirement income | 0% | not started |
| Phase 3 — tax engine | 0% | not started (NJ prioritized) |
| Phase 4 — risk & simulation | 0% | not started |
| Phase 5 — optimizers | 0% | not started |
| Phase 6 — advanced UX / AI assistant | 0% | not started |
| Phase 7 — hardening & release | 0% | not started |
| **Overall** | **~13%** | 5 of 40 planned tasks done |

## Task status

- **Last successfully completed task:** **DATA-002 — CRUD API**: 38 REST
  endpoints across 7 routers + a service layer, OpenAPI-documented; guarded
  deletes (household/baseline need `?confirm=true`); baseline protection
  (second baseline → 409; PATCH promotion demotes the old baseline and keeps
  lineage); owner-in-plan referential guards; PATCH re-validates the merged
  record. 25 new API tests + a live HTTP smoke test.
- **Current task:** none in progress; session 3 closed cleanly.
- **Single most useful next task:** **DATA-003 — plan/scenario duplication,
  rename, archive, and comparison flows** on top of the existing plan
  endpoints (see `NEXT_SESSION.md`).

## Implemented and verified (session 3; all observed)

- **API surface** (`/api/households`, `/api/plans`, `/api/people`,
  `/api/accounts`, `/api/liabilities`, `/api/income-streams`,
  `/api/expenses`): list/create/get/patch/delete with 201/204/404/409/422
  semantics; 422 details are field-level (same shape FastAPI uses for body
  validation, including merged-state errors raised at runtime).
- **Tests:** `make check` exit 0 — **71 backend** (25 api_crud + 25 schemas
  + 11 models + 5 app + 3 health + 2 migrations) + **3 frontend**.
- **Live E2E smoke** (HTTP against the running API on 0.3.0): health
  (`0002`, version 0.3.0) → create household → baseline plan → person →
  account with allocation → list → delete-without-confirm 400 →
  delete-with-confirm 204 → list empty (live DB left as found).
- **Scenario-isolation invariant (spec §13) proven via API:** patching a
  scenario account leaves the baseline's balance untouched; lists are
  plan-scoped; deleting a scenario reclaims only its rows.
- **Bugs found and fixed during the session (honestly red first):**
  runtime PATCH validation surfaced as 500 (now 422 via service-layer
  conversion) and allocation-set replacement violated the unique
  constraint (now a two-phase delete-then-insert flush).

## Implemented but not fully verified

- Docker artifacts (INFRA-004 / KI-003) — still never built.
- Backup/restore (KI-004), coverage (KI-006) — unchanged.

## Features partially implemented (spec gaps in this area)

- Unchanged from session 2: goals/preferences, employment periods,
  structured survivor/beneficiary assumptions (**DATA-012**), per-account
  withdrawal rules (CALC phase), one age-adjustment per expense row,
  single filing status per household.
- **New:** list endpoints are unpaginated (household-scale data; revisit if
  needed — PERFORMANCE task PERF-001); no optimistic-concurrency/ETag on
  PATCH (single-user local app for now; revisit with AUTH-001).

## Known bugs / blockers / technical debt

- KI-001 … KI-008 all unchanged (see `KNOWN_ISSUES.md`). No new defects
  after this session's fixes.
- Design notes: allocation-sum enforced at API/schema layer (D-011);
  `E501` excepted only for generated Alembic revisions (D-013).

## Operational status

- **Application startup status:** verified start/stop in session 3;
  servers **currently stopped**.
- **Database migration status:** live `retirement` at `0002 (head)`
  (unchanged this session — no schema change was needed for the API).
- **Latest build & test results (2026-10-13):** `make check` exit 0 —
  ruff clean, tsc clean, 71 backend + 3 frontend tests passed.
- **Last known-good commit:** session 2 code: `78f9b2f`; session 3 SHA is
  recorded at the bottom after its commit.
- **Version:** 0.3.0 (`backend/app/version.py`, `pyproject.toml`).
