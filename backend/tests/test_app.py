"""Tests for application wiring that do not require the database."""

from app.config import Settings


def test_settings_bind_to_localhost_by_default() -> None:
    """Local-first: the server must bind to loopback unless configured."""
    settings = Settings(_env_file=None)
    assert settings.app_host == "127.0.0.1"
    assert settings.app_port == 8000


def test_allowed_origin_list_is_parsed() -> None:
    settings = Settings(
        _env_file=None,
        allowed_origins="http://localhost:5173, http://127.0.0.1:5173 ,",
    )
    assert settings.allowed_origin_list == [
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ]


def test_root_endpoint_reports_service_info(client) -> None:
    response = client.get("/")
    assert response.status_code == 200
    body = response.json()
    assert body["name"] == "Retire Projection"
    assert body["health"] == "/api/health"
    assert body["docs"] == "/api/docs"


def test_openapi_document_is_served(client) -> None:
    response = client.get("/api/openapi.json")
    assert response.status_code == 200
    schema = response.json()
    assert schema["info"]["title"] == "Retire Projection API"
    assert "/api/health" in schema["paths"]


def test_swagger_docs_are_served(client) -> None:
    response = client.get("/api/docs")
    assert response.status_code == 200
