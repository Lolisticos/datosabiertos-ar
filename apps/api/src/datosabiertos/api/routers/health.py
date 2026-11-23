"""Health and readiness endpoints (no sensitive information)."""

from __future__ import annotations

import os
from datetime import UTC, datetime

from fastapi import APIRouter
from sqlalchemy import text

from ... import __version__
from ...db.session import get_engine
from ..deps import SessionDep, SettingsDep
from ..schemas.common import HealthStatus

router = APIRouter(tags=["health"])


@router.get("/health", response_model=HealthStatus, summary="Liveness")
async def health(settings: SettingsDep) -> HealthStatus:
    """Cheap liveness probe: the process can answer HTTP."""
    return HealthStatus(
        status="ok",
        version=__version__,
        environment=settings.environment,
        timestamp=datetime.now(UTC),
    )


@router.get("/health/ready", response_model=HealthStatus, summary="Readiness")
async def ready(session: SessionDep, settings: SettingsDep) -> HealthStatus:
    """Readiness probe: database reachable and RAW storage writable."""
    details: dict[str, str] = {}
    database = "ok"
    try:
        await session.execute(text("select 1"))
    except Exception:
        database = "unavailable"

    storage = "not-configured"
    root = settings.storage_root
    try:
        root.mkdir(parents=True, exist_ok=True)
        storage = "writable" if os.access(root, os.W_OK) else "read-only"
    except OSError:
        storage = "unavailable"
    details["storage"] = storage
    details["driver"] = get_engine().dialect.name

    healthy = database == "ok" and storage == "writable"
    return HealthStatus(
        status="ok" if healthy else "degraded",
        version=__version__,
        environment=settings.environment,
        timestamp=datetime.now(UTC),
        database=database,
        details=details,
    )
