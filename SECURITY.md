# SECURITY.md

Last reviewed: 2026-10-13 (Phase 0). Re-validate with SEC-001 (Phase 7) and
before any network exposure.

## 1. Threat model (what we defend against)

**Assets:** household financial records (balances, income, expenses, later
tax/SS details), database credentials in `.env`, backup dumps.

**Adversaries considered:**

1. Another user/process on the same machine reading data files.
2. An attacker on the LAN/WAN reaching an exposed service.
3. Accidental disclosure: committing secrets, logging credentials,
   sending data to third parties.

**Out of scope (documented limitations):** an attacker with root on this
machine; a compromised supply chain of `uv`/`npm`/PyPI at install time;
physical access to unencrypted backups.

## 2. Current posture (Phase 0 — what is actually implemented)

| Control | State | Evidence |
| --- | --- | --- |
| Localhost binding by default | ✅ | `.env` `APP_HOST=127.0.0.1`; `test_settings_bind_to_localhost_by_default` |
| No telemetry / no outbound calls at runtime | ✅ | Code contains no external endpoints; offline-by-construction frontend (system fonts, local bundle) |
| Secrets out of git | ✅ | `.env` gitignored (mode 600); `.dockerignore` excludes it; no credential strings in source |
| No credentials in API responses/logs | ✅ | `test_health_never_leaks_credentials`; health probe logs exception class only |
| Parameterized SQL | ✅ | SQLAlchemy ORM/`text()` with bound params only |
| CORS restricted to configured origins | ✅ | Settings-driven allowlist (default: the local Vite dev origin) |
| Input validation | ✅ (minimal) | Pydantic settings/schemas; grows with DATA-002 |
| Content Security Policy | partial | Set in production nginx config; not applied in dev |
| Authentication / sessions / CSRF | ❌ | Not yet implemented — **required before any non-localhost access** (AUTH-001, D-002) |
| HTTPS | ❌ | None yet; must be terminated in front of the app before remote use |
| Rate limiting / brute-force protection | ❌ | Part of AUTH-001 |
| Dependency vulnerability scanning | ❌ | Planned: `pip-audit` + `npm audit` wired into `make check` (SEC-001) |
| Backup encryption | ❌ | Dumps are plaintext SQL — treat `backups/` as sensitive data |

## 3. Exposure guidance (LAN / Internet)

The application will eventually be used over a network (D-002). Before
enabling that:

1. Implement AUTH-001 (password hashing — Argon2id or bcrypt via a
   maintained library — server-side sessions, CSRF on state-changing
   routes, lockout/rate limiting).
2. Put HTTPS in front (Caddy/nginx/Traefik with Let's Encrypt, or a VPN/
   SSH tunnel for personal use). Never send passwords over plain HTTP.
3. Publish **only** the web tier; keep `db` unpublished and the API bound to
   loopback inside the compose network (as configured today).
4. Firewall the host; verify with `ss -ltn` that nothing else is listening.
5. Create a least-privilege production DB role: login + schema rights only —
   **no CREATEDB** (the dev role has CREATEDB for tests, D-008).
6. Set `ENVIRONMENT=production`, a fresh `POSTGRES_PASSWORD`, and updated
   `ALLOWED_ORIGINS` for the real origin.

## 4. Secrets management

- `.env` holds all credentials, mode 600, gitignored, excluded from Docker
  contexts. Rotation: edit `.env`, restart, update the DB role password.
- Never place credentials in code, alembic.ini (URL is injected from
  settings), images, logs, or issue trackers.

## 5. Data handling rules (project-wide)

- Never commit financial data, backups, or `.env`.
- Never overwrite user plans/backups without explicit authorization
  (working rules §3).
- Tests must run against `retirement_test`, never the live database.
- The optional AI assistant (AI-001) must be opt-in, disclose what leaves
  the machine, and never be required for core features (spec §18–19).

## 6. Known limitations / open items

- No authentication yet — localhost-only is the current safety boundary.
- No HTTPS component in the compose stack yet.
- No automated vulnerability scanning in CI/make (SEC-001).
- Dev DB role privileges exceed production best practice (D-008).
- Threat model not yet adversarially reviewed (Phase 7).
