"""Pytest configuration and shared fixtures.

Database strategy:

* ``DATABASE_URL`` is redirected to a dedicated ``*_test`` database *before*
  any application module creates its engine (this file is imported before
  test modules, and ``app.db`` only builds its engine on import).
* The ``database`` fixture drops and recreates that database, so tests never
  touch real financial data.
* The ``migrated_database`` fixture additionally applies all Alembic
  migrations.

Prerequisite: a running PostgreSQL server (see OPERATIONS.md).  When the
server is unreachable, database-dependent fixtures fail loudly with an
actionable message rather than being skipped.
"""

import sys
from pathlib import Path

import pytest

BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from sqlalchemy.engine import make_url  # noqa: E402

from app.config import Settings  # noqa: E402

# Resolve the configured database URL (env var > .env > defaults) without
# caching, then point the process at the test database.
BASE_URL = make_url(str(Settings().database_url))
TEST_DB_NAME = f"{(BASE_URL.database or 'retirement')}_test"
TEST_URL = BASE_URL.set(database=TEST_DB_NAME).render_as_string(hide_password=False)

import os  # noqa: E402

os.environ["DATABASE_URL"] = TEST_URL


def _admin_url():
    """URL of the maintenance database used to create/drop test databases."""
    return BASE_URL.set(database="postgres")


@pytest.fixture(scope="session")
def database() -> str:
    """Drop and recreate the test database.  Returns its URL."""
    from sqlalchemy import create_engine, text

    engine = create_engine(_admin_url(), isolation_level="AUTOCOMMIT")
    try:
        with engine.connect() as conn:
            conn.execute(text(f'DROP DATABASE IF EXISTS "{TEST_DB_NAME}"'))
            conn.execute(text(f'CREATE DATABASE "{TEST_DB_NAME}"'))
    except Exception as exc:  # noqa: BLE001 - converted into an actionable test failure
        pytest.fail(
            "PostgreSQL is not reachable; cannot create the test database "
            f"({type(exc).__name__}: {exc}).\n"
            "Install and start PostgreSQL first — see OPERATIONS.md, section "
            "'Database installation'."
        )
    finally:
        engine.dispose()
    return TEST_URL


@pytest.fixture()
def client():
    """FastAPI test client bound to the application.

    ``app.main`` is imported lazily here, after ``DATABASE_URL`` has been
    redirected to the test database.
    """
    from fastapi.testclient import TestClient

    from app.main import app

    return TestClient(app)


@pytest.fixture(scope="session")
def migrated_database(database: str) -> str:
    """Recreate the test database and apply all Alembic migrations."""
    from alembic.config import Config

    from alembic import command

    cfg = Config(str(BACKEND_DIR / "alembic.ini"))
    command.upgrade(cfg, "head")
    return database
