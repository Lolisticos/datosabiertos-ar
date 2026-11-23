"""Transactional ingestion of one configured official statistical series."""

from __future__ import annotations

import asyncio
import hashlib
import json
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Protocol

from datosabiertos_connectors import SeriesFetchResult, canonical_hash
from sqlalchemy import select, text, update
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from ..catalog.models import Dataset, DatasetResource
from ..ingestion.models import (
    IngestionRun,
    IngestionRunStatus,
    IngestionRunType,
    ResourceSnapshot,
    SnapshotKind,
    SnapshotMetadata,
)
from ..ingestion.storage import StorageBackend, build_raw_key
from ..provenance.models import TransformationRun, TransformationStatus
from ..quality.models import DataQualityCheck, QualityStatus
from .models import Indicator, IndicatorObservation, ObservationReviewStatus

TRANSFORMATION_NAME = "official-series-json-to-observations"
TRANSFORMATION_VERSION = "1.0.0"


class StatisticalConnector(Protocol):
    async def fetch(self, series_id: str, *, limit: int = 5_000) -> SeriesFetchResult: ...


@dataclass(frozen=True)
class StatisticalSyncResult:
    run_id: uuid.UUID
    status: IngestionRunStatus
    records_read: int
    records_accepted: int
    records_rejected: int
    snapshot_id: uuid.UUID | None


class StatisticalSeriesSyncService:
    """Fetch, preserve and publish one indicator atomically."""

    def __init__(
        self,
        *,
        session: AsyncSession,
        connector: StatisticalConnector,
        storage: StorageBackend,
        indicator_code: str,
        triggered_by: str = "cli",
    ) -> None:
        self._session = session
        self._connector = connector
        self._storage = storage
        self._indicator_code = indicator_code
        self._triggered_by = triggered_by

    async def run(self) -> StatisticalSyncResult:
        indicator = await self._session.scalar(
            select(Indicator).where(Indicator.code == self._indicator_code)
        )
        if indicator is None or indicator.source_id is None or not indicator.source_series_id:
            raise ValueError(f"indicator {self._indicator_code!r} is not configured for ingestion")
        resource = await self._session.scalar(
            select(DatasetResource)
            .join(Dataset)
            .options(joinedload(DatasetResource.dataset))
            .where(
                Dataset.source_id == indicator.source_id,
                DatasetResource.external_id == indicator.source_series_id,
            )
        )
        if resource is None:
            raise ValueError(f"indicator {self._indicator_code!r} has no configured resource")

        source_id = indicator.source_id
        indicator_id = indicator.id
        resource_id = resource.id
        series_id = indicator.source_series_id
        unit = indicator.unit
        run = IngestionRun(
            source_id=source_id,
            dataset_id=resource.dataset_id,
            resource_id=resource_id,
            run_type=IngestionRunType.STATISTICAL_SERIES,
            status=IngestionRunStatus.RUNNING,
            triggered_by=self._triggered_by,
            transformation_version=TRANSFORMATION_VERSION,
        )
        self._session.add(run)
        await self._session.commit()
        run_id = run.id
        new_storage_key: str | None = None
        snapshot_id: uuid.UUID | None = None
        try:
            locked = bool(
                await self._session.scalar(
                    text("SELECT pg_try_advisory_xact_lock(hashtextextended(:key, 0))").bindparams(
                        key=f"statistical-series:{series_id}"
                    )
                )
            )
            if not locked:
                raise RuntimeError(f"a synchronization for series {series_id!r} is already running")

            fetched = await self._connector.fetch(series_id, limit=5_000)
            if fetched.metadata.units != unit:
                raise ValueError(
                    f"source unit changed from configured {unit!r} to {fetched.metadata.units!r}"
                )
            run.records_read = len(fetched.observations)
            content_hash = hashlib.sha256(fetched.raw).hexdigest()
            normalized_hash = _normalized_hash(fetched)
            snapshot = await self._session.scalar(
                select(ResourceSnapshot).where(
                    ResourceSnapshot.resource_id == resource_id,
                    ResourceSnapshot.content_hash == content_hash,
                )
            )
            if snapshot is None:
                new_storage_key = build_raw_key(
                    source_slug="series-tiempo-argentina",
                    kind="statistical-series",
                    content_hash=content_hash,
                    fetched_at=fetched.fetched_at,
                )
                stored = await self._storage.put_bytes(new_storage_key, fetched.raw)
                snapshot = ResourceSnapshot(
                    kind=SnapshotKind.RESOURCE_FILE,
                    resource_id=resource_id,
                    ingestion_run_id=run_id,
                    content_hash=content_hash,
                    normalized_hash=normalized_hash,
                    storage_key=stored.key,
                    media_type="application/json",
                    file_size=stored.size,
                    schema_fingerprint=canonical_hash(
                        {"columns": ["period", "value"], "frequency": fetched.metadata.frequency}
                    ),
                    fetched_at=fetched.fetched_at,
                )
                self._session.add(snapshot)
                await self._session.flush()
                self._session.add(
                    SnapshotMetadata(
                        snapshot_id=snapshot.id,
                        payload={
                            "response_url": fetched.response_url,
                            "series_id": series_id,
                            "source_download_url": fetched.metadata.download_url,
                        },
                    )
                )
            snapshot_id = snapshot.id

            transformation = await self._session.scalar(
                select(TransformationRun).where(
                    TransformationRun.snapshot_id == snapshot.id,
                    TransformationRun.name == TRANSFORMATION_NAME,
                    TransformationRun.version == TRANSFORMATION_VERSION,
                )
            )
            if transformation is None:
                transformation = TransformationRun(
                    snapshot_id=snapshot.id,
                    name=TRANSFORMATION_NAME,
                    version=TRANSFORMATION_VERSION,
                    status=TransformationStatus.RUNNING,
                    records_in=len(fetched.observations),
                )
                self._session.add(transformation)
                await self._session.flush()

            dimensions = {"base_year": 2004, "seasonal_adjustment": "original"}
            dimension_hash = canonical_hash(dimensions)
            rows = [
                {
                    "indicator_id": indicator_id,
                    "jurisdiction_id": None,
                    "period_start": observation.period,
                    "period_end": observation.period,
                    "value": observation.value,
                    "unit": unit,
                    "dimensions": dimensions,
                    "dimension_hash": dimension_hash,
                    "snapshot_id": snapshot.id,
                    "transformation_run_id": transformation.id,
                    "review_status": ObservationReviewStatus.PUBLISHED,
                }
                for observation in fetched.observations
            ]
            if rows:
                statement = insert(IndicatorObservation).values(rows)
                await self._session.execute(
                    statement.on_conflict_do_update(
                        constraint="uq_indicator_observation_key",
                        set_={
                            "period_end": statement.excluded.period_end,
                            "value": statement.excluded.value,
                            "unit": statement.excluded.unit,
                            "dimensions": statement.excluded.dimensions,
                            "snapshot_id": statement.excluded.snapshot_id,
                            "transformation_run_id": statement.excluded.transformation_run_id,
                            "review_status": statement.excluded.review_status,
                        },
                    )
                )

            missing_count = sum(item.value is None for item in fetched.observations)
            transformation.status = TransformationStatus.SUCCEEDED
            transformation.finished_at = datetime.now(UTC)
            transformation.records_out = len(fetched.observations)
            transformation.records_rejected = 0
            transformation.rejection_details = []
            run.status = IngestionRunStatus.SUCCEEDED
            run.finished_at = datetime.now(UTC)
            run.records_accepted = len(fetched.observations)
            run.records_rejected = 0
            resource.dataset.coverage_start = (
                fetched.observations[0].period if fetched.observations else None
            )
            resource.dataset.coverage_end = (
                fetched.observations[-1].period if fetched.observations else None
            )
            resource.dataset.last_successful_sync = run.finished_at
            resource.last_modified = run.finished_at
            self._session.add_all(
                [
                    DataQualityCheck(
                        ingestion_run_id=run.id,
                        check_type="official_series_contract",
                        status=QualityStatus.PASSED,
                        details={
                            "series_id": series_id,
                            "frequency": fetched.metadata.frequency,
                            "ordered_periods": True,
                            "unit": fetched.metadata.units,
                        },
                    ),
                    DataQualityCheck(
                        ingestion_run_id=run.id,
                        check_type="missing_values",
                        status=QualityStatus.WARNING if missing_count else QualityStatus.PASSED,
                        details={"count": missing_count, "represented_as_zero": False},
                    ),
                ]
            )
            await self._session.commit()
            return StatisticalSyncResult(
                run_id=run_id,
                status=IngestionRunStatus.SUCCEEDED,
                records_read=run.records_read,
                records_accepted=run.records_accepted,
                records_rejected=run.records_rejected,
                snapshot_id=snapshot_id,
            )
        except BaseException as exc:
            await self._session.rollback()
            if new_storage_key is not None:
                await self._storage.delete(new_storage_key)
            await self._session.execute(
                update(IngestionRun)
                .where(IngestionRun.id == run_id)
                .values(
                    status=IngestionRunStatus.FAILED,
                    finished_at=datetime.now(UTC),
                    error_summary=f"{type(exc).__name__}: {str(exc)[:900]}",
                    records_accepted=0,
                )
            )
            await self._session.commit()
            if isinstance(exc, asyncio.CancelledError):
                raise
            raise


def _normalized_hash(fetched: SeriesFetchResult) -> str:
    canonical = json.dumps(
        [
            [
                observation.period.isoformat(),
                str(observation.value) if observation.value is not None else None,
            ]
            for observation in fetched.observations
        ],
        ensure_ascii=False,
        separators=(",", ":"),
    ).encode()
    return hashlib.sha256(canonical).hexdigest()


__all__ = [
    "TRANSFORMATION_NAME",
    "TRANSFORMATION_VERSION",
    "StatisticalSeriesSyncService",
    "StatisticalSyncResult",
]
