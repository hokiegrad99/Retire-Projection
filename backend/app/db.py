"""Database engine, session factory, and health probing.

The engine is created once per process from ``settings.database_url``.
Importing this module reads the settings, so test harnesses must set
``DATABASE_URL`` *before* importing ``app.main`` (see ``tests/conftest.py``).
"""

import logging
import time
from typing import Annotated

from fastapi import Depends
from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.config import get_settings

logger = logging.getLogger(__name__)


class Base(DeclarativeBase):
    """Declarative base for all ORM mappings.

    Phase 1 (DATA-001) will define the financial domain tables on top of
    this base; Phase 0 intentionally creates no application tables.
    """


def _build_engine(url: str) -> Engine:
    return create_engine(url, pool_pre_ping=True)


settings = get_settings()
engine: Engine = _build_engine(settings.database_url)
SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


def get_db():
    """FastAPI dependency: one session per request, always closed."""
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


#: Annotated dependency used by every router handler (modern FastAPI style,
#: which also keeps ruff's B008 happy: no call in a parameter default).
DbSession = Annotated[Session, Depends(get_db)]


def check_database() -> tuple[bool, float | None, str | None]:
    """Probe the database.

    Returns ``(connected, latency_ms, migration_revision)``.  The revision is
    the value stored by Alembic in ``alembic_version`` (``None`` when the
    schema has not been migrated yet, or when the table cannot be read).

    Errors are reported by exception class plus the driver message, which
    must not contain credentials for safety.
    """
    start = time.perf_counter()
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
            latency_ms = round((time.perf_counter() - start) * 1000, 2)
            revision: str | None = None
            try:
                revision = conn.execute(
                    text("SELECT version_num FROM alembic_version")
                ).scalar_one_or_none()
            except Exception:  # noqa: BLE001 - missing table means "not migrated yet"
                revision = None
            return True, latency_ms, revision
    except Exception as exc:  # noqa: BLE001 - any driver failure means unhealthy
        # Log only the exception class; avoid leaking connection strings.
        logger.warning("Database health check failed: %s", type(exc).__name__)
        return False, None, None
