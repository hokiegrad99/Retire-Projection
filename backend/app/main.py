"""FastAPI application factory and executable entry point.

Run locally with:  ``python -m app.main`` (reads host/port from settings).
"""

import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_settings
from app.routers import health
from app.version import __version__


def create_app() -> FastAPI:
    """Build the FastAPI application."""
    settings = get_settings()
    logging.basicConfig(level=settings.log_level)

    application = FastAPI(
        title="Retire Projection API",
        version=__version__,
        description=(
            "Local-first retirement planning platform API. All computation "
            "happens locally; no data leaves this machine."
        ),
        docs_url="/api/docs",
        redoc_url="/api/redoc",
        openapi_url="/api/openapi.json",
    )

    application.add_middleware(
        CORSMiddleware,
        allow_origins=settings.allowed_origin_list,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
        allow_headers=["*"],
    )

    application.include_router(health.router)

    @application.get("/", include_in_schema=False)
    def root() -> dict:
        return {
            "name": settings.app_name,
            "version": __version__,
            "environment": settings.environment,
            "health": "/api/health",
            "docs": "/api/docs",
        }

    return application


app = create_app()


if __name__ == "__main__":
    import uvicorn

    cfg = get_settings()
    uvicorn.run(
        "app.main:app",
        host=cfg.app_host,
        port=cfg.app_port,
        log_level=cfg.log_level.lower(),
    )
