"""Tests for the Alembic migration pipeline (head-agnostic)."""

from pathlib import Path

from alembic.config import Config
from sqlalchemy import create_engine, text

from alembic import command

BACKEND_DIR = Path(__file__).resolve().parents[1]
# The stable baseline revision; never renumbered.
BASELINE_REVISION = "0001"


def _alembic_config() -> Config:
    return Config(str(BACKEND_DIR / "alembic.ini"))


def _db_revision(url: str) -> str | None:
    engine = create_engine(url)
    try:
        with engine.connect() as conn:
            return conn.execute(text("SELECT version_num FROM alembic_version")).scalar_one()
    finally:
        engine.dispose()


def _table_exists(url: str, table: str) -> bool:
    engine = create_engine(url)
    try:
        with engine.connect() as conn:
            row = conn.execute(
                text(
                    "SELECT 1 FROM information_schema.tables "
                    "WHERE table_schema = 'public' AND table_name = :t"
                ),
                {"t": table},
            ).first()
            return row is not None
    finally:
        engine.dispose()


def test_migration_chain_applies_to_head(migrated_database: str, expected_head: str) -> None:
    """After ``alembic upgrade head`` the version table matches the head."""
    assert _db_revision(migrated_database) == expected_head
    assert _table_exists(migrated_database, "household")


def test_downgrade_reupgrade_round_trip(migrated_database: str, expected_head: str) -> None:
    """Downgrading to the baseline and re-upgrading must fully restore the schema.

    This exercises the downgrade path (including enum-type drops) that a
    production rollback would rely on.
    """
    cfg = _alembic_config()
    try:
        command.downgrade(cfg, BASELINE_REVISION)
        assert _db_revision(migrated_database) == BASELINE_REVISION
        assert not _table_exists(migrated_database, "household")
    finally:
        # Always restore the schema for tests that run after this one.
        command.upgrade(cfg, "head")

    assert _db_revision(migrated_database) == expected_head
    assert _table_exists(migrated_database, "household")
    assert _table_exists(migrated_database, "account_allocation")
