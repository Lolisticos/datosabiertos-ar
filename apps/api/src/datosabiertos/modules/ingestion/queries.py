"""Read queries for sources, ingestion runs, quality checks and history."""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import datetime

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload, selectinload

from ..catalog.models import Dataset, DatasetResource
from ..history.models import DataChange
from ..ingestion.models import IngestionRun, IngestionRunStatus, ResourceSnapshot
from ..organizations.models import Organization
from ..quality.models import DataQualityCheck
from ..sources.models import DataSource


@dataclass(frozen=True)
class SourceSummary:
    source: DataSource
    dataset_count: int


async def list_sources(
    session: AsyncSession, *, include_inactive: bool = False
) -> list[SourceSummary]:
    statement = (
        select(DataSource, func.count(Dataset.id))
        .outerjoin(Dataset, Dataset.source_id == DataSource.id)
        .group_by(DataSource.id)
        .order_by(DataSource.name.asc())
    )
    if not include_inactive:
        statement = statement.where(DataSource.is_active.is_(True))
    rows = await session.execute(statement)
    return [SourceSummary(source=source, dataset_count=int(count)) for source, count in rows]


async def get_source(session: AsyncSession, slug: str) -> SourceSummary | None:
    row = await session.execute(
        select(DataSource, func.count(Dataset.id))
        .outerjoin(Dataset, Dataset.source_id == DataSource.id)
        .where(DataSource.slug == slug)
        .group_by(DataSource.id)
    )
    first = row.first()
    if first is None:
        return None
    source, count = first
    return SourceSummary(source=source, dataset_count=int(count))


async def source_last_successful_run(
    session: AsyncSession, source_id: uuid.UUID
) -> IngestionRun | None:
    return await session.scalar(
        select(IngestionRun)
        .where(
            IngestionRun.source_id == source_id, IngestionRun.status == IngestionRunStatus.SUCCEEDED
        )
        .order_by(IngestionRun.finished_at.desc().nulls_last())
        .limit(1)
    )


@dataclass(frozen=True)
class RunPage:
    items: list[IngestionRun]
    total: int


async def list_ingestion_runs(
    session: AsyncSession,
    *,
    source: str | None = None,
    status: IngestionRunStatus | None = None,
    page: int = 1,
    page_size: int = 20,
) -> RunPage:
    statement = select(IngestionRun).join(IngestionRun.source)
    if source:
        statement = statement.where(DataSource.slug == source)
    if status:
        statement = statement.where(IngestionRun.status == status)
    total = int(
        await session.scalar(
            select(func.count()).select_from(
                statement.with_only_columns(IngestionRun.id).subquery()
            )
        )
        or 0
    )
    items = list(
        await session.scalars(
            statement.options(joinedload(IngestionRun.source))
            .order_by(IngestionRun.started_at.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
    )
    return RunPage(items=items, total=total)


async def get_run(session: AsyncSession, run_id: uuid.UUID) -> IngestionRun | None:
    return await session.scalar(
        select(IngestionRun)
        .where(IngestionRun.id == run_id)
        .options(
            joinedload(IngestionRun.source),
            selectinload(IngestionRun.quality_checks),
        )
    )


async def run_quality_checks(session: AsyncSession, run_id: uuid.UUID) -> list[DataQualityCheck]:
    return list(
        await session.scalars(
            select(DataQualityCheck)
            .where(DataQualityCheck.ingestion_run_id == run_id)
            .order_by(DataQualityCheck.checked_at.asc())
        )
    )


async def list_changes(
    session: AsyncSession,
    *,
    change_type: str | None = None,
    dataset_id: uuid.UUID | None = None,
    page: int = 1,
    page_size: int = 20,
) -> tuple[list[DataChange], int]:
    statement = select(DataChange)
    if change_type:
        statement = statement.where(DataChange.change_type == change_type)
    if dataset_id:
        statement = statement.where(DataChange.dataset_id == dataset_id)
    total = int(
        await session.scalar(
            select(func.count()).select_from(statement.with_only_columns(DataChange.id).subquery())
        )
        or 0
    )
    items = list(
        await session.scalars(
            statement.options(joinedload(DataChange.dataset), joinedload(DataChange.resource))
            .order_by(DataChange.detected_at.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
    )
    return items, total


@dataclass(frozen=True)
class Overview:
    datasets: int
    datasets_available: int
    resources: int
    sources: int
    organizations: int
    topics: int
    snapshots: int
    changes_last_7_days: int
    last_run: IngestionRun | None
    last_successful_run: IngestionRun | None
    latest_source_update: datetime | None


async def overview(session: AsyncSession, *, since: datetime) -> Overview:
    datasets = int(await session.scalar(select(func.count()).select_from(Dataset)) or 0)
    datasets_available = int(
        await session.scalar(
            select(func.count()).select_from(Dataset).where(Dataset.is_available.is_(True))
        )
        or 0
    )
    resources = int(await session.scalar(select(func.count()).select_from(DatasetResource)) or 0)
    sources = int(
        await session.scalar(
            select(func.count()).select_from(DataSource).where(DataSource.is_active.is_(True))
        )
        or 0
    )
    organizations = int(await session.scalar(select(func.count()).select_from(Organization)) or 0)
    topics = int(
        await session.scalar(
            select(func.count(func.distinct(Dataset.topic))).where(
                Dataset.topic.is_not(None), Dataset.is_available.is_(True)
            )
        )
        or 0
    )
    snapshots = int(await session.scalar(select(func.count()).select_from(ResourceSnapshot)) or 0)
    changes = int(
        await session.scalar(
            select(func.count()).select_from(DataChange).where(DataChange.detected_at >= since)
        )
        or 0
    )
    last_run = await session.scalar(
        select(IngestionRun)
        .options(joinedload(IngestionRun.source))
        .order_by(IngestionRun.started_at.desc())
        .limit(1)
    )
    last_successful_run = await session.scalar(
        select(IngestionRun)
        .options(joinedload(IngestionRun.source))
        .where(IngestionRun.status == IngestionRunStatus.SUCCEEDED)
        .order_by(IngestionRun.finished_at.desc().nulls_last())
        .limit(1)
    )
    latest_source_update = await session.scalar(select(func.max(Dataset.last_source_update)))
    return Overview(
        datasets=datasets,
        datasets_available=datasets_available,
        resources=resources,
        sources=sources,
        organizations=organizations,
        topics=topics,
        snapshots=snapshots,
        changes_last_7_days=changes,
        last_run=last_run,
        last_successful_run=last_successful_run,
        latest_source_update=latest_source_update,
    )


__all__ = [
    "Overview",
    "RunPage",
    "SourceSummary",
    "get_run",
    "get_source",
    "list_changes",
    "list_ingestion_runs",
    "list_sources",
    "overview",
    "run_quality_checks",
    "source_last_successful_run",
]
