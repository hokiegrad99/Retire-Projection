# NEXT_SESSION.md — Resume here

## 1. Reload the project state (in order)

1. Read `PROJECT_STATE.md` (authoritative status).
2. Read this file.
3. Skim `IMPLEMENTATION_PLAN.md` (task IDs) and `FEATURE_MATRIX.md`.
4. Check the repository: `git log --oneline -5 && git status`.
   If docs and code disagree, **the code wins**.
5. Run startup checks: `make lint && make test` (expect **82 backend +
   3 frontend** tests green; PostgreSQL must be running).

Current branch: `main`. Development phase: **Phase 1 — DATA-001,
DATA-002, DATA-003 done, CALC-001 next.**

## 2. Exact task to continue

**CALC-001 — deterministic year-by-year projection engine (Phase 1, P0):**

- Pure Python (no FastAPI/SQLAlchemy imports in the math core): a
  documented **annual sequence** per spec §7–9 (contributions → growth →
  withdrawals → shortfall handling → RMD placeholder until CALC-011).
- **Shortfalls are reported, never silently funded** (spec: accounts never
  go negative; unfunded expenses become explicit shortfall records).
- Structured output (per-year rows: balances, income, expenses, shortfall,
  net-worth) consumable by tests, future UI, and reports alike.
- Deterministic: identical inputs ⇒ identical outputs; no wall-clock or
  randomness (SIM-001 adds that later).
- Expose it via one thin endpoint later in the same task if cheap
  (`POST /api/plans/{id}/project` or a service call — decide early, keep
  the core importable without the app).

## 3. Relevant files and functions

- `backend/app/models/` — source data (accounts with balances/rates,
  income streams, expenses, liabilities; `plan`/`person` for ages).
- `backend/app/services/crud.py` + `scenarios.py` — service-layer style
  to follow; put the engine in a new `backend/app/services/projection.py`
  (or `app/calc/` package if it grows — decide and record in DECISIONS).
- `backend/tests/reference/` — create per `TESTING.md` §4: source,
  input fixture, expected output, tolerance.
- `TESTING.md` §4 — the validation rules the engine must satisfy
  (reference cases, regression scenarios, invariants).

## 4. Prerequisites and commands

```bash
export PATH="$HOME/.local/bin:$HOME/.cargo/bin:$PATH"
make test                      # 82 + 3 green before you start
make check                     # full gate before commit
```

No schema change is expected; if one is needed:
`make migrate-revision MSG="calc-001 …"` (new revision `0004`).

## 5. Expected result and acceptance tests

- Documented annual sequence (write it down first — DECISIONS or
  ARCHITECTURE §"calculation flow") and implemented exactly once.
- A reference household reconciles year by year (start with hand-computed
  2–3 year fixtures in `tests/reference/`).
- Invariants tested: balances never negative; contributions/withdrawals
  reconcile to balance changes; identical run twice ⇒ byte-identical
  output; unfunded expenses appear as shortfalls.
- All 82 + 3 existing tests still green.

## 6. Known pitfalls and unresolved decisions

- **Port:** `APP_PORT=8010` (8000 occupied, KI-001). **sudo** is
  interactive; system installs go via `pkexec`.
- `.env` is gitignored; never commit or log credentials.
- Keep money math in `Decimal` (or document a fixed-point policy); do not
  silently switch to float — if a fast path is needed, quantify the error
  first and record it in DECISIONS.
- Unresolved (decide + record): nominal vs real return handling and
  inflation application point; rounding cadence (annual vs per-event);
  whether age is measured in integer years or exact dates (spec §7).
