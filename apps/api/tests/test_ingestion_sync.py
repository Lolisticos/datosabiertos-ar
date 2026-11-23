"""Idempotent catalogue synchronization and change detection (integration)."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from datosabiertos_connectors import (
    ConnectorMetadata,
    ConnectorPage,
    FetchResult,
    SourceDataset,
    SourceOrganization,
    SourceResource,
    SourceType,
    canonical_json,
    content_hash,
)
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from datosabiertos.modules.catalog.models import Dataset, DatasetResource
from datosabiertos.modules.history.models import ChangeType, DataChange
from datosabiertos.modules.ingestion.models import ResourceSnapshot
from datosabiertos.modules.ingestion.service import CatalogSyncService
from datosabiertos.modules.ingestion.storage import InMemoryStorage
from datosabiertos.modules.sources.models import DataSource

from .conftest import build_source


class FakeConnector:
    """Deterministic in-memory connector: one page per provided dataset list."""

    def __init__(self, pages: list[tuple[SourceDataset, ...]]) -> None:
        self._pages = pages

    def metadata(self) -> ConnectorMetadata:
        return ConnectorMetadata(name="fake", version="1.0.0", source_type=SourceType.CKAN)

    async def discover(self):
        for datasets in self._pages:
            payload = canonical_json([dataset.raw_metadata for dataset in datasets])
            yield ConnectorPage(
                datasets=datasets,
                raw_payload=payload,
                media_type="application/json",
                content_hash=content_hash(payload),
                offset=0,
                total_available=len(datasets),
                fetched_at=datetime.now(UTC),
            )

    async def fetch(self, resource: SourceResource) -> FetchResult:  # pragma: no cover
        raise NotImplementedError


def dataset(
    external_id: str = "ds-1",
    *,
    title: str = "Dataset de prueba",
    description: str = "Descripción original",
    resources: tuple[SourceResource, ...] = (),
) -> SourceDataset:
    return SourceDataset(
        external_id=external_id,
        title=title,
        description=description,
        organization=SourceOrganization(external_id="org-1", name="Organismo de prueba"),
        topic="Medio ambiente",
        license="CC-BY 4.0",
        resources=resources,
        raw_metadata={"id": external_id, "title": title, "notes": description},
    )


def resource(external_id: str = "res-1") -> SourceResource:
    return SourceResource(
        external_id=external_id,
        name="Recurso CSV",
        format="csv",
        url=f"https://example.test/{external_id}.csv",
        mime_type="text/csv",
    )


async def _count(session: AsyncSession, model: Any) -> int:
    return int(await session.scalar(select(func.count()).select_from(model)) or 0)


async def _service(
    session: AsyncSession, source: DataSource, connector: FakeConnector, storage: InMemoryStorage
) -> CatalogSyncService:
    return CatalogSyncService(session=session, connector=connector, source=source, storage=storage)


async def test_first_sync_persists_catalogue_and_raw_snapshot(db: AsyncSession) -> None:
    source = build_source()
    db.add(source)
    await db.commit()

    storage = InMemoryStorage()
    connector = FakeConnector([(dataset(resources=(resource(),)),)])
    result = await (await _service(db, source, connector, storage)).run()

    assert result.status.value == "succeeded"
    assert result.datasets_created == 1
    assert result.pages == 1
    assert result.snapshots_stored == 1
    assert result.changes_recorded == 2  # dataset_added + resource_added
    assert await _count(db, Dataset) == 1
    assert await _count(db, DatasetResource) == 1

    snapshot = await db.scalar(select(ResourceSnapshot))
    assert snapshot is not None
    stored = storage.objects[snapshot.storage_key]
    assert stored == canonical_json(
        [{"id": "ds-1", "title": "Dataset de prueba", "notes": "Descripción original"}]
    )

    stored_dataset = await db.scalar(select(Dataset))
    assert stored_dataset is not None
    assert stored_dataset.last_successful_sync is not None
    assert stored_dataset.search_text is not None
    assert "dataset de prueba" in stored_dataset.search_text


async def test_second_identical_sync_is_idempotent(db: AsyncSession) -> None:
    source = build_source()
    db.add(source)
    await db.commit()

    storage = InMemoryStorage()
    payload = (dataset(resources=(resource(),)),)
    first = await (await _service(db, source, FakeConnector([payload]), storage)).run()
    changes_after_first = await _count(db, DataChange)
    datasets_after_first = await _count(db, Dataset)

    second = await (await _service(db, source, FakeConnector([payload]), storage)).run()

    assert first.datasets_created == 1
    assert second.datasets_created == 0
    assert second.datasets_updated == 0
    assert second.datasets_unchanged == 1
    assert second.changes_recorded == 0
    assert second.snapshots_stored == 0
    assert await _count(db, DataChange) == changes_after_first
    assert await _count(db, Dataset) == datasets_after_first
    assert await _count(db, ResourceSnapshot) == 1


async def test_metadata_change_is_detected_and_explained(db: AsyncSession) -> None:
    source = build_source()
    db.add(source)
    await db.commit()

    storage = InMemoryStorage()
    await (
        await _service(db, source, FakeConnector([(dataset(title="Título original"),)]), storage)
    ).run()
    result = await (
        await _service(db, source, FakeConnector([(dataset(title="Título corregido"),)]), storage)
    ).run()

    assert result.datasets_updated == 1
    assert result.datasets_unchanged == 0
    assert result.changes_recorded == 1

    change = await db.scalar(
        select(DataChange).where(DataChange.change_type == ChangeType.METADATA_CHANGED)
    )
    assert change is not None
    assert change.change_summary["fields"] == ["title"]

    stored = await db.scalar(select(Dataset))
    assert stored is not None
    assert stored.title == "Título corregido"


async def test_missing_dataset_is_marked_removed(db: AsyncSession) -> None:
    source = build_source()
    db.add(source)
    await db.commit()

    storage = InMemoryStorage()
    await (
        await _service(db, source, FakeConnector([(dataset("ds-1"), dataset("ds-2"))]), storage)
    ).run()
    result = await (await _service(db, source, FakeConnector([(dataset("ds-1"),)]), storage)).run()

    assert result.datasets_removed == 1
    assert result.changes_recorded == 1

    removed = await db.scalar(select(Dataset).where(Dataset.external_id == "ds-2"))
    assert removed is not None
    assert removed.is_available is False

    change = await db.scalar(
        select(DataChange).where(DataChange.change_type == ChangeType.DATASET_REMOVED)
    )
    assert change is not None


async def test_quality_checks_and_run_record_are_persisted(db: AsyncSession) -> None:
    source = build_source()
    db.add(source)
    await db.commit()

    storage = InMemoryStorage()
    result = await (await _service(db, source, FakeConnector([(dataset(),)]), storage)).run()

    from datosabiertos.modules.ingestion.models import IngestionRun
    from datosabiertos.modules.quality.models import DataQualityCheck

    stored_run = await db.get(IngestionRun, result.run_id)
    assert stored_run is not None
    assert stored_run.status.value == "succeeded"
    assert stored_run.records_read == 1
    assert stored_run.records_accepted == 1
    assert stored_run.finished_at is not None

    check_count = int(await db.scalar(select(func.count()).select_from(DataQualityCheck)) or 0)
    assert check_count >= 1
