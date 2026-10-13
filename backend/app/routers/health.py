"""Health check endpoint used by startup verification, Docker health
checks, and end-to-end tests."""

from datetime import UTC, datetime

from fastapi import APIRouter, Response

from app.db import check_database
from app.version import __version__

router = APIRouter(prefix="/api", tags=["health"])


@router.get("/health")
def health(response: Response) -> dict:
    """Return service health.

    ``200`` when the API and database are reachable, ``503`` when the
    database cannot be reached.  Never returns credentials.
    """
    connected, latency_ms, revision = check_database()
    body = {
        "status": "ok" if connected else "degraded",
        "version": __version__,
        "service": "retire-projection-api",
        "database": {
            "connected": connected,
            "latency_ms": latency_ms,
            "migration_revision": revision,
        },
        "timestamp": datetime.now(UTC).isoformat(),
    }
    if not connected:
        response.status_code = 503
    return body
