"""Source endpoints."""

from __future__ import annotations

from fastapi import APIRouter

from ...core.errors import NotFoundError
from ...modules.ingestion.queries import (
    get_source,
    list_ingestion_runs,
    list_sources,
    source_last_successful_run,
)
from ..deps import SessionDep
from ..mappers import source_out
from ..schemas.catalog import SourceOut

router = APIRouter(prefix="/sources", tags=["sources"])


@router.get("", response_model=list[SourceOut], summary="List configured sources")
async def read_sources(session: SessionDep) -> list[SourceOut]:
    summaries = await list_sources(session)
    result: list[SourceOut] = []
    for summary in summaries:
        last_success = await source_last_successful_run(session, summary.source.id)
        last_runs = await list_ingestion_runs(session, source=summary.source.slug, page_size=1)
        result.append(
            source_out(
                summary,
                last_successful_run_at=last_success.finished_at if last_success else None,
                last_run_status=last_runs.items[0].status.value if last_runs.items else None,
            )
        )
    return result


@router.get("/{slug}", response_model=SourceOut, summary="Source detail")
async def read_source(slug: str, session: SessionDep) -> SourceOut:
    summary = await get_source(session, slug)
    if summary is None:
        raise NotFoundError(f"Fuente {slug!r} no encontrada.")
    last_success = await source_last_successful_run(session, summary.source.id)
    last_runs = await list_ingestion_runs(session, source=slug, page_size=1)
    return source_out(
        summary,
        last_successful_run_at=last_success.finished_at if last_success else None,
        last_run_status=last_runs.items[0].status.value if last_runs.items else None,
    )
