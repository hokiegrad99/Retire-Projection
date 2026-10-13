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
