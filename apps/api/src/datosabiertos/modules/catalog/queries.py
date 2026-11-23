"""Read queries for the catalogue detail view."""

from __future__ import annotations

import uuid
from dataclasses import dataclass

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload, selectinload

from ..catalog.models import Dataset, DatasetResource
from ..history.models import DataChange
from ..ingestion.models import (
    IngestionRun,
    IngestionRunStatus,
    ResourceSnapshot,
)
from ..quality.models import DataQualityCheck


@dataclass(frozen=True)
class DatasetDetail:
    dataset: Dataset
    resources: list[DatasetResource]
    last_run: IngestionRun | None
    quality_checks: list[DataQualityCheck]
    changes: list[DataChange]
    snapshot_count: int
    last_snapshot_at: object | None


async def get_dataset_detail(session: AsyncSession, dataset_id: uuid.UUID) -> DatasetDetail | None:
    dataset = await session.scalar(
        select(Dataset)
        .where(Dataset.id == dataset_id)
        .options(
            joinedload(Dataset.source),
            joinedload(Dataset.organization),
            selectinload(Dataset.resources),
        )
    )
    if dataset is None:
        return None

    last_run = await session.scalar(
        select(IngestionRun)
        .where(IngestionRun.source_id == dataset.source_id)
        .order_by(IngestionRun.started_at.desc())
        .limit(1)
    )
    quality_checks: list[DataQualityCheck] = []
    if last_run is not None:
        quality_checks = list(
            await session.scalars(
                select(DataQualityCheck)
                .where(DataQualityCheck.ingestion_run_id == last_run.id)
                .order_by(DataQualityCheck.checked_at.asc())
            )
        )
    changes = list(
        await session.scalars(
            select(DataChange)
            .where(DataChange.dataset_id == dataset.id)
            .order_by(DataChange.detected_at.desc())
            .limit(50)
        )
    )
    snapshot_count = int(
        await session.scalar(
            select(func.count())
            .select_from(ResourceSnapshot)
            .where(
                ResourceSnapshot.source_id == dataset.source_id,
                ResourceSnapshot.resource_id.is_(None),
            )
        )
        or 0
    )
    last_snapshot_at = await session.scalar(
        select(func.max(ResourceSnapshot.fetched_at)).where(
            ResourceSnapshot.source_id == dataset.source_id,
            ResourceSnapshot.resource_id.is_(None),
        )
    )
    return DatasetDetail(
        dataset=dataset,
        resources=list(dataset.resources),
        last_run=last_run,
        quality_checks=quality_checks,
        changes=changes,
        snapshot_count=snapshot_count,
        last_snapshot_at=last_snapshot_at,
    )


async def get_dataset_by_external_id(
    session: AsyncSession, source_slug: str, external_id: str
) -> Dataset | None:
    return await session.scalar(
        select(Dataset)
        .join(Dataset.source)
        .where(Dataset.external_id == external_id, Dataset.source.has(slug=source_slug))
    )


async def datasets_missing_snapshot(session: AsyncSession) -> int:
    """Datasets whose source never stored a RAW payload (observability signal)."""
    return int(
        await session.scalar(
            select(func.count()).select_from(Dataset).where(Dataset.last_successful_sync.is_(None))
        )
        or 0
    )


async def failed_runs(session: AsyncSession, *, limit: int = 5) -> list[IngestionRun]:
    return list(
        await session.scalars(
            select(IngestionRun)
            .where(IngestionRun.status.in_([IngestionRunStatus.FAILED, IngestionRunStatus.PARTIAL]))
            .order_by(IngestionRun.started_at.desc())
            .limit(limit)
        )
    )


__all__ = [
    "DatasetDetail",
    "datasets_missing_snapshot",
    "failed_runs",
    "get_dataset_by_external_id",
    "get_dataset_detail",
]
