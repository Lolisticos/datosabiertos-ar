"""API v1 router aggregation."""

from __future__ import annotations

from fastapi import APIRouter

from .routers import catalog, discovery, health, indicators, ingestion, sources

api_router = APIRouter()
api_router.include_router(health.router)
api_router.include_router(sources.router)
api_router.include_router(catalog.router)
api_router.include_router(discovery.router)
api_router.include_router(indicators.router)
api_router.include_router(ingestion.router)

__all__ = ["api_router"]
