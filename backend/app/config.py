"""Application settings loaded from environment variables and ``.env``.

Precedence (highest first): real environment variables, project-root
``.env`` file, built-in defaults.  The ``.env`` file is gitignored and must
never be committed.
"""

from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

PROJECT_ROOT = Path(__file__).resolve().parents[2]
_ENV_FILE = PROJECT_ROOT / ".env"


class Settings(BaseSettings):
    """Runtime configuration for the API server."""

    app_name: str = "Retire Projection"
    environment: str = "development"
    app_host: str = "127.0.0.1"
    app_port: int = 8000
    database_url: str = "postgresql+psycopg://retire_app:changeme@127.0.0.1:5432/retirement"
    # Comma-separated list of browser origins allowed by CORS.
    allowed_origins: str = "http://localhost:5173,http://127.0.0.1:5173"
    log_level: str = "INFO"

    model_config = SettingsConfigDict(
        env_file=str(_ENV_FILE) if _ENV_FILE.exists() else None,
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    @property
    def allowed_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.allowed_origins.split(",") if origin.strip()]


@lru_cache
def get_settings() -> Settings:
    """Return the process-wide settings instance (cached)."""
    return Settings()
