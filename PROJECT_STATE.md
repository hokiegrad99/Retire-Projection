# PROJECT_STATE.md — Authoritative project status

> **Session startup protocol:** read this file first, then `NEXT_SESSION.md`,
> then skim `IMPLEMENTATION_PLAN.md` / `FEATURE_MATRIX.md`. The repository is
> the source of truth wherever documentation and code disagree.

- **Checkpoint:** 2026-10-13, end of session 4 (see `SESSION_LOG.md`)
- **Purpose / scope:** a local-first, subscription-free retirement and
  financial planning platform, running locally with an eventual move to a
  production server.
- **Current development phase:** **Phase 1 in progress — DATA-001,
  DATA-002 and DATA-003 done; CALC-001 (projection engine) is next.**

## Completion estimates

| Area | Estimate | Notes |
| --- | --- | --- |
| Phase 0 — foundation | 95% | Exit criteria met; INFRA-004 still blocked (KI-003) |
| Phase 1 — MVP planning app | ~33% | 3 of 9 tasks done (DATA-001…003); engine/UI/auth remain |
| Phase 2 — retirement income | 0% | not started |
| Phase 3 — tax engine | 0% | not started (NJ prioritized) |
| Phase 4 — risk & simulation | 0% | not started |
| Phase 5 — optimizers | 0% | not started |
| Phase 6 — advanced UX / AI assistant | 0% | not started |
| Phase 7 — hardening & release | 0% | not started |
| **Overall** | **15%** | 6 of 40 planned tasks done |

## Task status

- **Last successfully completed task:** **DATA-003 — scenario
  management**: `POST /api/plans/{id}/duplicate` (deep copy of every
  owned row with owner remapping, exact Decimal/date values, lineage via
  `parent_plan_id`, optional rename/baseline seeding with 409 conflict);
  archive via `PATCH {"archived": true}` + migration `0003`
  (`plan.archived_at`) with `?include_archived=true` listing and the
  mutual baseline/archive guards (D-018); `GET
  /api/plans/{id}/compare/{other}` field-level diff with name-matched
  rows, presence lists, and 422 for cross-household comparisons (D-019).
  11 new tests + live HTTP smoke.
- **Current task:** none in progress; session 4 closed cleanly.
- **Single most useful next task:** **CALC-001 — deterministic
  year-by-year projection engine** (see `NEXT_SESSION.md`).

## Implemented and verified (session 4; all observed)

- **Scenario API** on top of the DATA-002 surface (now **37 entity
  endpoints / 17 OpenAPI paths**): duplicate, compare, archive.
- **Migration `0003`:** autogenerate-detected exactly one change
  (`plan.archived_at`); applied to the live DB (`alembic current` →
  `0003 (head)`) and exercised by the head-agnostic chain + downgrade →
  re-upgrade round-trip tests.
- **Tests:** `make check` exit 0 — **82 backend** (11 scenarios + 25
  api_crud + 25 schemas + 11 models + 5 app + 3 health + 2 migrations)
  + **3 frontend**.
- **Live E2E smoke** (HTTP against the running API on 0.4.0): health
  (`0003`, 0.4.0) → household → baseline → person → account+allocations
  → duplicate with rename (lineage verified) → balance diff reported
  left `250000.00` → right `300000.00` → archive hides from default
  listing / baseline archive refused 409 / archived plan still readable
  → cross-household compare 422 → confirmed deletes → live DB verified
  left at **0 households, 0 plans, revision 0003**; port 8010 released.
- **§13 invariant extended:** editing a duplicate (account balance,
  plan name) leaves the source untouched
  (`test_editing_a_duplicate_never_touches_the_source`); duplicate
  deep-copy counts/balances/allocations compared row-for-row.
- **Red states this session:** all test-authoring errors, fixed at the
  cause — builder payload shape (422 extra_forbidden), SQL alias typo
  (`FROM account` vs `account_allocation`), a paren-count
  IndentationError, ruff F841 leftover variable, and a smoke-script field
  path. No product-code defects surfaced.

## Implemented but not fully verified

- Docker artifacts (INFRA-004 / KI-003) — still never built.
- Backup/restore (KI-004), coverage (KI-006) — unchanged.

## Features partially implemented (spec gaps in this area)

- Unchanged from session 3: goals/preferences, employment periods,
  structured survivor/beneficiary assumptions (**DATA-012**), per-account
  withdrawal rules (CALC phase), one age-adjustment per expense row,
  single filing status per household; no pagination/optimistic locking.
- **New:** comparison matches rows **by name** — renaming an entity
  surfaces as presence diffs rather than field diffs (D-019); the diff
  loads both plan graphs into memory (household scale; revisit with
  PERF-001).

## Known bugs / blockers / technical debt

- KI-001 … KI-008 all unchanged (see `KNOWN_ISSUES.md`). No new defects
  after this session's test-authoring fixes.
- Design notes: archive/baseline mutual exclusion (D-018); name-matched
  comparison (D-019).

## Operational status

- **Application startup status:** verified start/stop in session 4;
  servers **currently stopped**, port 8010 released.
- **Database migration status:** live `retirement` at `0003 (head)`
  (migrated this session; `plan.archived_at` column present).
- **Latest build & test results (2026-10-13):** `make check` exit 0 —
  ruff clean, tsc clean, 82 backend + 3 frontend tests passed.
- **Last known-good commit:** session-4 DATA-003 commit (SHA recorded
  in the follow-up commit below). Previous: `de9ca48` (session 3 docs
  correction), `c1745a6` (session 3 code).
- **Version:** 0.4.0 (`backend/app/version.py`, `pyproject.toml`).
