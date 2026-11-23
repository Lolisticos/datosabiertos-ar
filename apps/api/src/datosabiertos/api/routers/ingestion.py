"""Ingestion run and change-history endpoints."""

from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Query

from ...core.errors import NotFoundError
from ...modules.history.models import ChangeType
from ...modules.ingestion.models import IngestionRunStatus
from ...modules.ingestion.queries import (
    get_run,
    list_changes,
    list_ingestion_runs,
    run_quality_checks,
)
from ..deps import PaginationDep, SessionDep
from ..mappers import change_out, quality_check_out, run_out
from ..schemas.catalog import ChangeListItem, RunOut
from ..schemas.common import Page

router = APIRouter(tags=["ingestion"])


@router.get("/ingestion-runs", response_model=Page[RunOut], summary="Ingestion history")
async def read_runs(
    session: SessionDep,
    pagination: PaginationDep,
    source: Annotated[str | None, Query(max_length=64)] = None,
    status: IngestionRunStatus | None = None,
) -> Page[RunOut]:
    page = await list_ingestion_runs(
        session, source=source, status=status, page=pagination.page, page_size=pagination.page_size
    )
    pages = (page.total + pagination.page_size - 1) // pagination.page_size if page.total else 0
    return Page[RunOut](
        items=[run_out(run) for run in page.items],
        total=page.total,
        page=pagination.page,
        page_size=pagination.page_size,
        pages=pages,
    )


@router.get("/ingestion-runs/{run_id}", response_model=RunOut, summary="Run detail")
async def read_run(run_id: uuid.UUID, session: SessionDep) -> RunOut:
    run = await get_run(session, run_id)
    if run is None:
        raise NotFoundError("Ejecución de ingesta no encontrada.")
    checks = await run_quality_checks(session, run_id)
    response = run_out(run)
    response.quality_checks = [quality_check_out(check) for check in checks]
    return response


@router.get("/changes", response_model=Page[ChangeListItem], summary="Recent detected changes")
async def read_changes(
    session: SessionDep,
    pagination: PaginationDep,
    change_type: ChangeType | None = None,
    dataset_id: uuid.UUID | None = None,
) -> Page[ChangeListItem]:
    items, total = await list_changes(
        session,
        change_type=change_type.value if change_type else None,
        dataset_id=dataset_id,
        page=pagination.page,
        page_size=pagination.page_size,
    )
    pages = (total + pagination.page_size - 1) // pagination.page_size if total else 0
    return Page[ChangeListItem](
        items=[
            ChangeListItem(**change_out(change).model_dump(), source_slug=None) for change in items
        ],
        total=total,
        page=pagination.page,
        page_size=pagination.page_size,
        pages=pages,
    )
