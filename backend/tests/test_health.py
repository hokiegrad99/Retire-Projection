"""Tests for GET /api/health."""

from fastapi.testclient import TestClient

from app.version import __version__


def test_health_requires_database(client: TestClient, database: str) -> None:
    """With a reachable database the endpoint reports status ok (200)."""
    response = client.get("/api/health")
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["status"] == "ok"
    assert body["version"] == __version__
    assert body["service"] == "retire-projection-api"
    assert body["database"]["connected"] is True
    assert isinstance(body["database"]["latency_ms"], (int, float))
    assert body["timestamp"]


def test_health_reports_migration_revision(client: TestClient, migrated_database: str) -> None:
    """After ``alembic upgrade head`` the baseline revision is visible."""
    response = client.get("/api/health")
    assert response.status_code == 200, response.text
    assert response.json()["database"]["migration_revision"] == "0001"


def test_health_never_leaks_credentials(client: TestClient, database: str) -> None:
    """The response body must not contain the database password."""
    from app.config import get_settings

    password = get_settings().database_url.rsplit("@", 1)[0].split(":", 1)[-1]
    response = client.get("/api/health")
    if password and password not in ("changeme",):
        assert password not in response.text
