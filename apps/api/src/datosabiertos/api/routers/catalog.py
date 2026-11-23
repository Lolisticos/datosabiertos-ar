"""Catalogue endpoints: datasets, search, facets, statistics and coverage."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta
from typing import Annotated

from fastapi import APIRouter, Query
from sqlalchemy import select

from ...core.errors import NotFoundError
from ...modules.catalog.queries import get_dataset_detail
from ...modules.ingestion.queries import list_changes, overview
from ...modules.search.service import (
    DatasetFilters,
    catalogue_facets,
    normalize_query,
    search_datasets,
)
from ...modules.sources.models import DataSource
from ..deps import PaginationDep, SessionDep
from ..mappers import change_out, dataset_detail, dataset_list_item, run_out
from ..schemas.catalog import (
    ChangeOut,
    DatasetCoverageOut,
    DatasetDetailOut,
    DatasetFiltersOut,
    DatasetListItem,
    StatsOut,
)
from ..schemas.common import Facet as FacetSchema
from ..schemas.common import Facets, Page, ReferencedSource

router = APIRouter(tags=["catalogue"])

COVERAGE_NOTE = (
    "Cobertura actual: metadatos del catálogo nacional (datos.gob.ar) y de las fuentes "
    "habilitadas. En esta fase se preservan los archivos originales y se normalizan los "
    "metadatos; todavía no se importaron tablas de datos, por lo que no hay indicadores "
    "ni visualizaciones estadísticas publicadas."
)


def _filters(
    q: str | None,
    source: str | None,
    organization_id: uuid.UUID | None,
    topic: str | None,
    format: str | None,
    jurisdiction_id: uuid.UUID | None,
    updated_since: datetime | None,
    available_only: bool,
) -> DatasetFilters:
    return DatasetFilters(
        q=normalize_query(q),
        source=source,
        organization_id=organization_id,
        topic=topic,
        format=format,
        jurisdiction_id=jurisdiction_id,
        updated_since=updated_since,
        available_only=available_only,
    )


@router.get("/datasets", response_model=Page[DatasetListItem], summary="Search datasets")
async def read_datasets(
    session: SessionDep,
    pagination: PaginationDep,
    q: Annotated[str | None, Query(max_length=200, description="Texto libre")] = None,
    source: Annotated[str | None, Query(max_length=64, description="Slug de la fuente")] = None,
    organization_id: uuid.UUID | None = None,
    topic: Annotated[str | None, Query(max_length=128)] = None,
    format: Annotated[str | None, Query(max_length=32, description="Formato del recurso")] = None,
    jurisdiction_id: uuid.UUID | None = None,
    updated_since: datetime | None = None,
    available_only: bool = True,
) -> Page[DatasetListItem]:
    """Filtered, paginated catalogue search backed by PostgreSQL."""
    filters = _filters(
        q, source, organization_id, topic, format, jurisdiction_id, updated_since, available_only
    )
    page = await search_datasets(
        session, filters, page=pagination.page, page_size=pagination.page_size
    )
    return Page[DatasetListItem](
        items=[dataset_list_item(dataset) for dataset in page.items],
        total=page.total,
        page=page.page,
        page_size=page.page_size,
        pages=page.pages,
    )


@router.get("/search", response_model=Page[DatasetListItem], summary="Search datasets (alias)")
async def search(
    session: SessionDep,
    pagination: PaginationDep,
    q: Annotated[str, Query(min_length=1, max_length=200, description="Texto libre")],
) -> Page[DatasetListItem]:
    """Same engine as `/datasets`, with a mandatory query (discovery entry point)."""
    page = await search_datasets(
        session,
        DatasetFilters(q=normalize_query(q)),
        page=pagination.page,
        page_size=pagination.page_size,
    )
    return Page[DatasetListItem](
        items=[dataset_list_item(dataset) for dataset in page.items],
        total=page.total,
        page=page.page,
        page_size=page.page_size,
        pages=page.pages,
    )


@router.get("/facets", response_model=Facets, summary="Filter options with counts")
async def read_facets(session: SessionDep) -> Facets:
    facets = await catalogue_facets(session)
    return Facets(
        topics=[FacetSchema(value=facet.value, count=facet.count) for facet in facets.topics],
        formats=[FacetSchema(value=facet.value, count=facet.count) for facet in facets.formats],
        organizations=[
            FacetSchema(value=facet.value, count=facet.count) for facet in facets.organizations
        ],
    )


@router.get("/datasets/filters", response_model=DatasetFiltersOut, summary="Explorer filters")
async def read_dataset_filters(session: SessionDep) -> DatasetFiltersOut:
    facets = await catalogue_facets(session)
    sources = list(await session.scalars(select(DataSource).order_by(DataSource.name)))
    return DatasetFiltersOut(
        topics=[facet.value for facet in facets.topics],
        formats=[facet.value for facet in facets.formats],
        sources=[
            ReferencedSource(
                id=source.id,
                slug=source.slug,
                name=source.name,
                source_type=source.source_type.value,
                base_url=source.base_url,
            )
            for source in sources
        ],
    )


@router.get("/stats/overview", response_model=StatsOut, summary="Catalogue coverage")
async def read_overview(session: SessionDep) -> StatsOut:
    since = datetime.now(UTC) - timedelta(days=7)
    data = await overview(session, since=since)
    return StatsOut(
        datasets=data.datasets,
        datasets_available=data.datasets_available,
        resources=data.resources,
        sources=data.sources,
        organizations=data.organizations,
        topics=data.topics,
        raw_snapshots=data.snapshots,
        changes_last_7_days=data.changes_last_7_days,
        latest_source_update=data.latest_source_update,
        last_run=run_out(data.last_run) if data.last_run else None,
        last_successful_run=run_out(data.last_successful_run) if data.last_successful_run else None,
        coverage_note=COVERAGE_NOTE,
    )


@router.get("/datasets/{dataset_id}", response_model=DatasetDetailOut, summary="Dataset detail")
async def read_dataset(dataset_id: uuid.UUID, session: SessionDep) -> DatasetDetailOut:
    detail = await get_dataset_detail(session, dataset_id)
    if detail is None:
        raise NotFoundError("Dataset no encontrado.")
    return dataset_detail(detail)


@router.get(
    "/datasets/{dataset_id}/changes",
    response_model=Page[ChangeOut],
    summary="Dataset change history",
)
async def read_dataset_changes(
    dataset_id: uuid.UUID, session: SessionDep, pagination: PaginationDep
) -> Page[ChangeOut]:
    detail = await get_dataset_detail(session, dataset_id)
    if detail is None:
        raise NotFoundError("Dataset no encontrado.")
    items, total = await list_changes(
        session, dataset_id=dataset_id, page=pagination.page, page_size=pagination.page_size
    )
    pages = (total + pagination.page_size - 1) // pagination.page_size if total else 0
    return Page[ChangeOut](
        items=[change_out(change) for change in items],
        total=total,
        page=pagination.page,
        page_size=pagination.page_size,
        pages=pages,
    )


@router.get(
    "/datasets/{dataset_id}/visualization",
    response_model=DatasetCoverageOut,
    summary="Visualization availability",
)
async def read_dataset_visualization(
    dataset_id: uuid.UUID, session: SessionDep
) -> DatasetCoverageOut:
    """State the real availability instead of rendering an invented chart."""
    detail = await get_dataset_detail(session, dataset_id)
    if detail is None:
        raise NotFoundError("Dataset no encontrado.")
    return DatasetCoverageOut(
        available=False,
        visualizations=[],
        reason=(
            "Este dataset todavía no tiene una tabla normalizada ni un indicador asociado. "
            "La visualización se habilitará cuando exista un indicador con observaciones "
            "verificadas para el período y la jurisdicción."
        ),
        dataset_id=dataset_id,
    )
