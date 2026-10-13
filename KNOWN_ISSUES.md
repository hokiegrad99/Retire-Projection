# KNOWN_ISSUES.md

Format: ID · severity · symptom · workaround · planned fix/task.
Update when an issue is confirmed, worked around, and when it is fixed
(closing entry references the fix).

---

**KI-001 · low · Port 8000 already in use on this machine**

- Symptom: starting the API with the default port fails:
  `ERROR: [Errno 98] ... bind on address ('127.0.0.1', 8000): address
  already in use`. Occupied by an unrelated process
  (`/usr/bin/python3 main.py --host 127.0.0.1 --port 8000`, pid 1074 at
  time of discovery).
- Workaround: `.env` sets `APP_PORT=8010`; Vite proxy and
  `docker-compose.yml` host mapping use the same value (D-006).
- Planned fix: none (foreign process). Revisit only if it disappears —
  documented so nobody "fixes" it by killing pid 1074.

**KI-002 · cosmetic · Starlette TestClient deprecation warning**

- Symptom: pytest prints `StarletteDeprecationWarning: Using httpx with
  starlette.testclient is deprecated; install httpx2 instead.`
- Workaround: none needed; tests pass.
- Planned fix: follow-up dependency update when httpx2 stabilizes (fold
  into next dependency-bump / SEC-001).

**KI-003 · high (for deployment) · Docker artifacts never executed**

- Symptom: `Dockerfile.backend`, `frontend/Dockerfile`, `nginx.conf`, and
  `docker-compose.yml` were written without Docker available on the dev
  host, so they are untested.
- Workaround: native development path (`make setup/backend/frontend`) is
  fully verified.
- Planned fix: INFRA-004 — build and run the stack on a Docker-capable
  machine before any deployment.

**KI-004 · medium · Backup restore not exercised**

- Symptom: backup procedure in OPERATIONS.md §5 is documented but
  `pg_restore` has not been run and verified against this project.
- Workaround: none (procedural risk).
- Planned fix: BACKUP-001 — perform a real backup → restore → `make test`
  cycle and record the result.

**KI-005 · low · Single Python lockfile mixes runtime and dev dependencies**

- Symptom: `backend/requirements.lock.txt` is a full venv freeze
  (includes pytest/ruff/httpx) and is reused by `Dockerfile.backend`.
- Workaround: acceptable for now; image is slightly larger.
- Planned fix: split runtime/dev locks (uv `--no-dev` or pip-tools) —
  see DECISIONS D-010.

**KI-006 · medium · No coverage measurement**

- Symptom: no coverage numbers exist for backend or frontend.
- Workaround: none.
- Planned fix: add pytest-cov + Vitest coverage in QA-001; record baselines
  in TESTING.md §5.

**KI-007 · low · Setup requires network access**

- Symptom: `make setup` (uv + npm) needs internet; offline operation is
  guaranteed only at runtime, not installation.
- Workaround: standard for source-based installs; vendor wheels offline if
  ever required.
- Planned fix: none unless offline-install becomes a real requirement.

**KI-008 · low · `migration_revision: null` on a fresh database**

- Symptom: a brand-new database shows `null` until `make migrate` runs
  (production container runs migrations at startup, so it self-heals).
- Workaround: `make migrate`.
- Planned fix: acceptable behavior; documented for support scripts.
