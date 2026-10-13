# IMPLEMENTATION_PLAN.md — Phased roadmap

Status values: `done`, `in progress`, `blocked`, `not started`.
Priorities: P0 = blocking, P1 = important, P2 = later.
Task IDs are permanent — never renumber; add new IDs in the same family.

## Phase 0 — Discovery and project foundation

| ID | Task | Pri | Depends on | Status | Acceptance criteria |
| --- | --- | --- | --- | --- | --- |
| INFRA-001 | Repository, environment inspection, stack selection | P0 | — | **done** | Git repo, venv via uv, locked deps, stack recorded in DECISIONS (D-001…D-007) |
| INFRA-002 | All 12 continuity documents created | P0 | INFRA-001 | **done** | Documents exist, accurate, and follow the startup/shutdown protocol |
| INFRA-003 | Runnable app + DB connection + health check + tests + startup workflow | P0 | INFRA-001 | **done** | `make test` green; live `/api/health` 200 with `database.connected=true`; migrations apply; start/stop verified |
| INFRA-004 | Build & verify Docker/Compose stack | P1 | INFRA-003 | **blocked** (no Docker on dev host — D-004) | `docker compose up --build` starts app; health check green inside stack; run once on the production server or any Docker-capable host |

Phase 0 exit criteria: reconstruct, start, test, and resume the project from
its files — **met** (except the optional Docker verification).

## Phase 1 — Minimum viable planning application

| ID | Task | Pri | Depends on | Status | Acceptance criteria |
| --- | --- | --- | --- | --- | --- |
| DATA-001 | Financial domain model (household, people, accounts, liabilities, income, expenses) + migrations + validation | P0 | INFRA-003 | not started | Models migrate cleanly; validation rejects bad dates/amounts/enums; unit tests pass |
| DATA-002 | CRUD API for all domain objects | P0 | DATA-001 | not started | Create/read/update/delete via API with OpenAPI docs; server-side validation errors are explicit |
| DATA-003 | Plans/scenarios: protected baseline, duplicate/rename/archive, lineage | P0 | DATA-001 | not started | Mutating a scenario never alters the baseline (invariant test) |
| CALC-001 | Deterministic year-by-year projection engine (pure Python, structured output) | P0 | DATA-001 | not started | Documented annual sequence; no circular flows; shortfalls reported, never silently funded; reference scenario reconciles |
| UI-001 | Financial dashboard (net worth, cash flow, portfolio charts) | P1 | CALC-001 | not started | Every chart derives from calculation output; no hard-coded values |
| UI-002 | Data-entry modules (household, accounts, income, expenses, debts) | P1 | DATA-002 | not started | Guided entry with validation and inline help; persists across restart |
| DATA-004 | CSV import/export, JSON plan export/import, DB backup + restore | P1 | DATA-002 | not started | Backup restores into a clean DB (tested); import previews and reports errors |
| AUTH-001 | Authentication + sessions + CSRF (required by D-002) | P0 | DATA-002 | not started | No access without login once enabled; password hashing; security tests pass |

Phase 1 exit criteria: enter a realistic household, save it, restart the
application, reproduce its projections.

## Phase 2 — Retirement income modeling

| ID | Task | Pri | Depends on | Status | Acceptance criteria |
| --- | --- | --- | --- | --- | --- |
| DATA-010 | Pensions, annuities, annuitization rules | P1 | CALC-001 | not started | Payments, COLA, survivor elections appear correctly in projections |
| CALC-010 | Social Security engine (claiming ages, spousal/survivor, COLA) | P0 | CALC-001 | not started | Claiming-age comparison reproduces published reduction/credit rules |
| CALC-011 | Retirement contributions & employer match; RMD engine | P1 | CALC-001 | not started | Contribution limits enforced per effective year; RMDs computed and withdrawn |
| CALC-012 | Healthcare & Medicare costs (pre-Medicare, Parts B/D, IRMAA, LTC) | P0 | CALC-001 | not started | Effective-dated assumptions; healthcare inflation independent of general inflation |
| CALC-013 | Debt amortization + real estate events (buy/sell/rent) | P1 | CALC-001 | not started | Payoff dates and interest match reference amortization; equity not spendable without a transaction |
| QA-010 | Integration tests: income/expense streams through projection | P0 | all Phase 2 | not started | End-to-end reference household reconciles year by year |

## Phase 3 — Tax engine

| ID | Task | Pri | Depends on | Status | Acceptance criteria |
| --- | --- | --- | --- | --- | --- |
| TAX-001 | Federal income tax (brackets, filing status, deductions, cap gains, taxable SS) | P0 | CALC-001 | not started | Reference cases from IRS publications match within documented rounding |
| TAX-002 | New Jersey state module (D-003) + relocation support | P0 | TAX-001 | not started | NJ reference cases match; moves apply from effective date |
| TAX-003 | Effective-dated rule store (brackets, limits, thresholds) + assumption transparency | P0 | TAX-001 | not started | Rules versioned by tax year; no silent extrapolation past the last enacted year |
| TAX-004 | Roth conversions & RMD interplay, IRMAA interactions | P1 | TAX-001 | not started | Conversion schedules evaluated by the real engine, taxed in the conversion year |

## Phase 4 — Risk and simulation

| ID | Task | Pri | Depends on | Status | Acceptance criteria |
| --- | --- | --- | --- | --- | --- |
| SIM-001 | Monte Carlo engine (seeded, configurable N, documented distributions) | P0 | CALC-001 | not started | Same seed → identical results; success criterion defined in output; percentile bands render |
| SIM-002 | Stress tests (early crash, low-return decades, longevity, benefit cuts) | P1 | SIM-001 | not started | Each scenario reproducible and documented |
| SIM-003 | Sensitivity analysis & historical backtesting where supported | P2 | SIM-001 | not started | Historical ≠ forward-looking labeling enforced |

## Phase 5 — Advanced optimizers

| ID | Task | Pri | Depends on | Status | Acceptance criteria |
| --- | --- | --- | --- | --- | --- |
| OPT-001 | Roth conversion optimizer (bracket/IRMAA filling, lifetime tax, estate value) | P1 | TAX-004 | not started | Objective + constraints stated; results validated by independent projection runs |
| OPT-002 | Social Security claiming optimizer | P1 | CALC-010 | not started | Compares household strategies on stated objectives |
| OPT-003 | Retirement date optimizer | P2 | CALC-001 | not started | Earliest feasible date under explicit risk criteria |
| OPT-004 | Sustainable spending optimizer | P1 | SIM-001 | not started | Deterministic or probabilistic constraint stated in output |
| OPT-005 | Withdrawal strategy & asset-location comparison | P1 | TAX-001 | not started | Heuristic vs. optimized clearly distinguished in docs/UI |

## Phase 6 — Advanced UX and reporting

| ID | Task | Pri | Depends on | Status | Acceptance criteria |
| --- | --- | --- | --- | --- | --- |
| UI-010 | Guided onboarding, full module coverage, accessibility pass | P1 | UI-001 | not started | All spec §16 screens exist and are documented |
| UI-011 | Reports (printable/PDF), import/export UX polish | P1 | DATA-004 | not started | Reports render offline from real results |
| AI-001 | Optional plan-aware assistant (tool-calling only, opt-in, local model option) | P2 | CALC-001 stable | not started | Every quantitative answer cites scenario/years; core works fully without it |
| DATA-011 | Additional states/account types | P2 | TAX-002 | not started | Each new jurisdiction independently tested |

## Phase 7 — Hardening and release

| ID | Task | Pri | Depends on | Status | Acceptance criteria |
| --- | --- | --- | --- | --- | --- |
| QA-001 | Full regression suite + reference scenarios with tolerances | P0 | all | not started | Deterministic reference outputs version-controlled |
| SEC-001 | Security review, dependency vulnerability checks, threat-model validation | P0 | AUTH-001 | not started | No unresolved critical findings; SECURITY.md matches reality |
| BACKUP-001 | Backup/restore, upgrade/migration rehearsal | P0 | DATA-004 | not started | Restored backup passes full test suite |
| PERF-001 | Performance profiling (calc + simulation timing recorded) | P1 | SIM-001 | not started | Measured numbers recorded, not estimated |
| OPS-001 | Install docs, release notes, known-limitations sign-off | P1 | all | not started | Clean-machine install from OPERATIONS.md succeeds |

**Next task:** DATA-001.
