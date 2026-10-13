"""Tests for the Alembic migration pipeline."""

from sqlalchemy import create_engine, text


def test_baseline_migration_applies(migrated_database: str) -> None:
    """After ``alembic upgrade head`` the version table holds the baseline."""
    engine = create_engine(migrated_database)
    try:
        with engine.connect() as conn:
            revision = conn.execute(text("SELECT version_num FROM alembic_version")).scalar_one()
    finally:
        engine.dispose()
    assert revision == "0001"
