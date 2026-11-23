"""Catalogue synchronization.

One run reads every page a connector publishes, stores the untouched payload as a
RAW snapshot, upserts datasets and resources, records quality checks and writes
explicit ``DataChange`` rows. Repeating it on an unchanged catalogue produces no
duplicates and no new change records — that is the idempotency contract.
"""

from __future__ import annotations

import asyncio
import hashlib
import uuid
from collections.abc import Iterable
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

import structlog
from datosabiertos_connectors import (
    ConnectorError,
    SourceConnector,
    SourceDataset,
    SourceResource,
    content_hash,
)
from sqlalchemy import select, text, update
from sqlalchemy.ext.asyncio import AsyncSession

from ...core.text import build_search_text
from ..catalog.models import Dataset, DatasetResource
from ..history.models import ChangeType, DataChange
from ..ingestion.models import (
    IngestionRun,
    IngestionRunStatus,
    IngestionRunType,
    ResourceSnapshot,
    SnapshotKind,
)
from ..organizations.models import Organization
from ..quality.models import DataQualityCheck, QualityStatus
from ..sources.models import DataSource
from .storage import StorageBackend, build_raw_key

logger = structlog.get_logger(__name__)

TRANSFORMATION_VERSION = "catalog-normalizer-1.1.0"

# Column contracts. Values are fitted on write; the untouched upstream payload is
# always preserved in the RAW snapshot and in ``dataset.raw_metadata``.
MAX_TITLE = 512
MAX_TOPIC = 128
MAX_LICENSE = 255
MAX_LANDING_URL = 1024
MAX_ORGANIZATION = 255
MAX_RESOURCE_NAME = 512
MAX_RESOURCE_URL = 2048
MAX_EXTERNAL_ID = 128


@dataclass
class SyncResult:
    run_id: uuid.UUID
    source_slug: str
    status: IngestionRunStatus
    datasets_read: int = 0
    datasets_created: int = 0
    datasets_updated: int = 0
    datasets_unchanged: int = 0
    datasets_removed: int = 0
    resources_upserted: int = 0
    snapshots_stored: int = 0
    changes_recorded: int = 0
    pages: int = 0
    errors: list[str] = field(default_factory=list)

    @property
    def datasets_persisted(self) -> int:
        return self.datasets_created + self.datasets_updated + self.datasets_unchanged

    def as_dict(self) -> dict[str, Any]:
        return {
            "run_id": str(self.run_id),
            "source": self.source_slug,
            "status": self.status.value,
            "pages": self.pages,
            "datasets_read": self.datasets_read,
            "datasets_created": self.datasets_created,
            "datasets_updated": self.datasets_updated,
            "datasets_unchanged": self.datasets_unchanged,
            "datasets_removed": self.datasets_removed,
            "resources_upserted": self.resources_upserted,
            "snapshots_stored": self.snapshots_stored,
            "changes_recorded": self.changes_recorded,
            "errors": self.errors,
        }


class CatalogSyncService:
    """Synchronizes one configured ``DataSource`` using one connector."""

    def __init__(
        self,
        *,
        session: AsyncSession,
        connector: SourceConnector,
        source: DataSource,
        storage: StorageBackend,
        triggered_by: str = "cli",
    ) -> None:
        self._session = session
        self._connector = connector
        self._source = source
        self._source_id = source.id
        self._source_slug = source.slug
        self._storage = storage
        self._triggered_by = triggered_by
        self._pending_storage_keys: set[str] = set()

    async def run(self) -> SyncResult:
        run = IngestionRun(
            source_id=self._source.id,
            run_type=IngestionRunType.CATALOG_DISCOVERY,
            status=IngestionRunStatus.RUNNING,
            triggered_by=self._triggered_by,
            transformation_version=TRANSFORMATION_VERSION,
            started_at=datetime.now(UTC),
        )
        self._session.add(run)
        await self._session.flush()
        # The execution record must survive a rollback of catalogue mutations.
        await self._session.commit()

        result = SyncResult(
            run_id=run.id, source_slug=self._source.slug, status=IngestionRunStatus.RUNNING
        )
        seen_dataset_ids: set[uuid.UUID] = set()
        seen_external_ids: set[str] = set()
        catalog_schema_keys: set[str] = set()

        try:
            if not await self._acquire_source_lock():
                result.status = IngestionRunStatus.FAILED
                result.errors.append("concurrent_sync: another run owns the source lock")
                await self._finalize_failed_run(result)
                return result

            last_schema_fingerprint = await self._last_catalog_schema_fingerprint()
            async for page in self._connector.discover():
                result.pages += 1
                fingerprint = _schema_fingerprint(page.datasets)
                catalog_schema_keys.update(_schema_keys(page.datasets))
                _snapshot_id, created = await self._store_catalog_page(
                    content=page.raw_payload,
                    media_type=page.media_type,
                    fetched_at=page.fetched_at,
                    run=run,
                    schema_fingerprint=fingerprint,
                )
                if created:
                    result.snapshots_stored += 1

                for dataset in page.datasets:
                    if dataset.external_id in seen_external_ids:
                        # Overlapping page windows (shrinking retries) must not
                        # be counted twice or emit duplicate change records.
                        continue
                    seen_external_ids.add(dataset.external_id)
                    result.datasets_read += 1
                    dataset_row = await self._upsert_dataset(dataset, run=run, result=result)
                    if dataset_row is not None:
                        seen_dataset_ids.add(dataset_row.id)

                run.records_read = result.datasets_read
                run.records_accepted = result.datasets_persisted

            if result.pages == 0:
                result.errors.append("catalogue discovery completed without any page")
            if result.errors:
                raise _CatalogValidationError("; ".join(result.errors[:5]))

            if result.pages > 0:
                result.datasets_removed = await self._mark_missing_datasets(
                    seen_dataset_ids, run, result
                )
            global_schema_fingerprint = _fingerprint_keys(catalog_schema_keys)
            run.schema_fingerprint = global_schema_fingerprint
            if (
                last_schema_fingerprint
                and global_schema_fingerprint
                and last_schema_fingerprint != global_schema_fingerprint
            ):
                await self._record_change(
                    run=run,
                    change_type=ChangeType.SCHEMA_CHANGED,
                    summary={
                        "scope": "catalog",
                        "previous_schema_fingerprint": last_schema_fingerprint,
                        "current_schema_fingerprint": global_schema_fingerprint,
                    },
                )
                result.changes_recorded += 1
            await self._record_quality_checks(run=run, result=result)
            result.status = IngestionRunStatus.SUCCEEDED
        except (ConnectorError, _CatalogValidationError) as exc:
            await self._session.rollback()
            await self._discard_unconfirmed_storage()
            result.status = IngestionRunStatus.FAILED
            result.errors.append(f"{type(exc).__name__}: {exc}")
            logger.warning("catalog_sync_connector_error", error=str(exc), source=self._source_slug)
            _reset_rolled_back_counters(result)
            await self._finalize_failed_run(result)
            return result
        except asyncio.CancelledError:
            await self._session.rollback()
            await self._discard_unconfirmed_storage()
            result.status = IngestionRunStatus.FAILED
            result.errors.append("CancelledError: synchronization interrupted")
            _reset_rolled_back_counters(result)
            await asyncio.shield(self._finalize_failed_run(result))
            raise
        except Exception as exc:  # pragma: no cover - defensive boundary
            await self._session.rollback()
            await self._discard_unconfirmed_storage()
            result.status = IngestionRunStatus.FAILED
            result.errors.append(f"{type(exc).__name__}: unexpected failure")
            logger.exception("catalog_sync_failed", source=self._source_slug)
            _reset_rolled_back_counters(result)
            await self._finalize_failed_run(result)
            return result

        run.status = result.status
        run.finished_at = datetime.now(UTC)
        run.records_read = result.datasets_read
        run.records_accepted = result.datasets_persisted
        run.records_rejected = max(0, result.datasets_read - result.datasets_persisted)
        if result.errors:
            run.error_summary = "; ".join(result.errors)[:2000]
        await self._session.commit()
        self._pending_storage_keys.clear()
        logger.info("catalog_sync_finished", **result.as_dict())
        return result

    async def _acquire_source_lock(self) -> bool:
        locked = await self._session.scalar(
            text("SELECT pg_try_advisory_xact_lock(:lock_key)"),
            {"lock_key": _source_lock_key(self._source_id)},
        )
        return bool(locked)

    async def _finalize_failed_run(self, result: SyncResult) -> None:
        await self._session.execute(
            update(IngestionRun)
            .where(IngestionRun.id == result.run_id)
            .values(
                status=IngestionRunStatus.FAILED,
                finished_at=datetime.now(UTC),
                records_read=result.datasets_read,
                records_accepted=0,
                records_rejected=result.datasets_read,
                error_summary="; ".join(result.errors)[:2000],
            )
        )
        await self._session.commit()
        logger.info("catalog_sync_finished", **result.as_dict())

    async def _discard_unconfirmed_storage(self) -> None:
        for key in self._pending_storage_keys:
            await self._storage.delete(key)
        self._pending_storage_keys.clear()

    async def _last_catalog_schema_fingerprint(self) -> str | None:
        previous_run = await self._session.scalar(
            select(IngestionRun)
            .where(
                IngestionRun.source_id == self._source.id,
                IngestionRun.status == IngestionRunStatus.SUCCEEDED,
                IngestionRun.schema_fingerprint.is_not(None),
            )
            .order_by(IngestionRun.finished_at.desc().nulls_last())
            .limit(1)
        )
        return None if previous_run is None else previous_run.schema_fingerprint

    async def _store_catalog_page(
        self,
        *,
        content: bytes,
        media_type: str,
        fetched_at: datetime,
        run: IngestionRun,
        schema_fingerprint: str,
    ) -> tuple[uuid.UUID, bool]:
        digest = content_hash(content)
        existing = await self._session.scalar(
            select(ResourceSnapshot).where(
                ResourceSnapshot.source_id == self._source.id,
                ResourceSnapshot.resource_id.is_(None),
                ResourceSnapshot.content_hash == digest,
            )
        )
        if existing is not None:
            return existing.id, False

        key = build_raw_key(
            source_slug=self._source.slug,
            kind="catalog",
            content_hash=digest,
            fetched_at=fetched_at,
        )
        await self._storage.put_bytes(key, content)
        self._pending_storage_keys.add(key)
        snapshot = ResourceSnapshot(
            kind=SnapshotKind.CATALOG_PAYLOAD,
            source_id=self._source.id,
            ingestion_run_id=run.id,
            content_hash=digest,
            storage_key=key,
            media_type=media_type,
            file_size=len(content),
            schema_fingerprint=schema_fingerprint,
            fetched_at=fetched_at,
        )
        self._session.add(snapshot)
        await self._session.flush()
        return snapshot.id, True

    async def _upsert_dataset(
        self, incoming: SourceDataset, *, run: IngestionRun, result: SyncResult
    ) -> Dataset | None:
        if not incoming.title.strip():
            result.errors.append(f"dataset {incoming.external_id} without title")
            return None

        organization = await self._get_or_create_organization(incoming)
        organization_id = organization.id if organization else None
        existing = await self._session.scalar(
            select(Dataset).where(
                Dataset.source_id == self._source.id, Dataset.external_id == incoming.external_id
            )
        )
        new_hash = incoming.metadata_hash()
        now = datetime.now(UTC)

        if existing is None:
            dataset = Dataset(
                source_id=self._source.id,
                organization_id=organization_id,
                external_id=incoming.external_id,
                metadata_hash=new_hash,
                is_available=True,
                last_successful_sync=now,
                raw_metadata=incoming.raw_metadata,
            )
            self._apply_fields(
                dataset,
                incoming,
                organization_id=organization_id,
                organization_name=organization.name if organization else None,
            )
            self._session.add(dataset)
            await self._session.flush()
            result.datasets_created += 1
            await self._record_change(
                run=run,
                change_type=ChangeType.DATASET_ADDED,
                dataset_id=dataset.id,
                summary={"external_id": incoming.external_id, "title": incoming.title},
            )
            result.changes_recorded += 1
        else:
            dataset = existing
            was_unavailable = not dataset.is_available
            if dataset.metadata_hash == new_hash:
                result.datasets_unchanged += 1
            else:
                changed_fields = _changed_fields(dataset, incoming, organization_id)
                previous_hash = dataset.metadata_hash
                self._apply_fields(
                    dataset,
                    incoming,
                    organization_id=organization_id,
                    organization_name=organization.name if organization else None,
                )
                dataset.metadata_hash = new_hash
                result.datasets_updated += 1
                await self._record_change(
                    run=run,
                    change_type=ChangeType.METADATA_CHANGED,
                    dataset_id=dataset.id,
                    summary={
                        "external_id": incoming.external_id,
                        "fields": changed_fields,
                        "previous_metadata_hash": previous_hash,
                        "current_metadata_hash": new_hash,
                    },
                )
                result.changes_recorded += 1
            dataset.is_available = True
            dataset.removed_at = None
            dataset.last_successful_sync = now
            dataset.raw_metadata = incoming.raw_metadata
            if was_unavailable:
                await self._record_change(
                    run=run,
                    change_type=ChangeType.RECOVERED,
                    dataset_id=dataset.id,
                    summary={"external_id": incoming.external_id},
                )
                result.changes_recorded += 1
            await self._session.flush()

        await self._sync_resources(dataset, incoming.resources, run=run, result=result)
        return dataset

    @staticmethod
    def _apply_fields(
        dataset: Dataset,
        incoming: SourceDataset,
        *,
        organization_id: uuid.UUID | None,
        organization_name: str | None,
    ) -> None:
        dataset.title = _fit(incoming.title, MAX_TITLE) or incoming.external_id
        dataset.description = incoming.description
        dataset.topic = _fit(incoming.topic, MAX_TOPIC)
        dataset.license = _fit(incoming.license, MAX_LICENSE)
        dataset.coverage_start = incoming.coverage_start
        dataset.coverage_end = incoming.coverage_end
        dataset.last_source_update = incoming.last_source_update
        dataset.landing_url = _fit(incoming.landing_url, MAX_LANDING_URL)
        dataset.organization_id = organization_id
        dataset.search_text = build_search_text(
            incoming.title, incoming.description, organization_name
        )

    async def _sync_resources(
        self,
        dataset: Dataset,
        incoming: Iterable[SourceResource],
        *,
        run: IngestionRun,
        result: SyncResult,
    ) -> None:
        existing_rows = {
            row.external_id: row
            for row in await self._session.scalars(
                select(DatasetResource).where(DatasetResource.dataset_id == dataset.id)
            )
        }
        seen: set[str] = set()
        for resource in incoming:
            if len(resource.url) > MAX_RESOURCE_URL:
                result.errors.append(
                    f"resource {resource.external_id} skipped: "
                    f"URL longer than {MAX_RESOURCE_URL} chars"
                )
                continue
            seen.add(resource.external_id)
            row = existing_rows.get(resource.external_id)
            was_unavailable = row is not None and not row.is_available
            if row is None:
                row = DatasetResource(
                    dataset_id=dataset.id,
                    external_id=resource.external_id,
                    url=resource.url,
                    is_available=True,
                )
                self._session.add(row)
                await self._session.flush()
                await self._record_change(
                    run=run,
                    change_type=ChangeType.RESOURCE_ADDED,
                    dataset_id=dataset.id,
                    resource_id=row.id,
                    summary={"external_id": resource.external_id, "format": resource.format},
                )
                result.changes_recorded += 1
            self._apply_resource_fields(row, resource)
            if was_unavailable:
                await self._record_change(
                    run=run,
                    change_type=ChangeType.RESOURCE_RECOVERED,
                    dataset_id=dataset.id,
                    resource_id=row.id,
                    summary={"external_id": resource.external_id},
                )
                result.changes_recorded += 1
            result.resources_upserted += 1

        for external_id, row in existing_rows.items():
            if external_id not in seen and row.is_available:
                row.is_available = False
                row.removed_at = datetime.now(UTC)
                await self._record_change(
                    run=run,
                    change_type=ChangeType.RESOURCE_REMOVED,
                    dataset_id=dataset.id,
                    resource_id=row.id,
                    summary={"external_id": external_id, "format": row.format},
                )
                result.changes_recorded += 1

    @staticmethod
    def _apply_resource_fields(row: DatasetResource, resource: SourceResource) -> None:
        row.name = _fit(resource.name, MAX_RESOURCE_NAME)
        row.format = resource.format
        row.url = resource.url
        row.mime_type = resource.mime_type
        row.checksum = resource.checksum
        row.file_size = resource.file_size
        row.last_modified = resource.last_modified
        row.is_available = True
        row.removed_at = None

    async def _get_or_create_organization(self, incoming: SourceDataset) -> Organization | None:
        if incoming.organization is None:
            return None
        name = _fit(incoming.organization.name.strip(), MAX_ORGANIZATION)
        if not name:
            return None
        organization = await self._session.scalar(
            select(Organization).where(Organization.name == name)
        )
        if organization is None:
            organization = Organization(
                name=name,
                jurisdiction_id=self._source.jurisdiction_id,
                official_url=_fit(incoming.organization.official_url, MAX_LANDING_URL),
            )
            self._session.add(organization)
            await self._session.flush()
        return organization

    async def _mark_missing_datasets(
        self, seen_dataset_ids: set[uuid.UUID], run: IngestionRun, result: SyncResult
    ) -> int:
        statement = select(Dataset).where(
            Dataset.source_id == self._source.id, Dataset.is_available.is_(True)
        )
        if seen_dataset_ids:
            statement = statement.where(Dataset.id.not_in(seen_dataset_ids))
        removed = 0
        for dataset in await self._session.scalars(statement):
            dataset.is_available = False
            dataset.removed_at = datetime.now(UTC)
            await self._record_change(
                run=run,
                change_type=ChangeType.DATASET_REMOVED,
                dataset_id=dataset.id,
                summary={"external_id": dataset.external_id, "title": dataset.title},
            )
            result.changes_recorded += 1
            removed += 1
        return removed

    async def _record_quality_checks(self, *, run: IngestionRun, result: SyncResult) -> None:
        checks: list[tuple[str, QualityStatus, dict[str, Any]]] = [
            (
                "catalog_pages_fetched",
                QualityStatus.PASSED if result.pages > 0 else QualityStatus.FAILED,
                {"pages": result.pages},
            ),
            (
                "datasets_persisted",
                QualityStatus.PASSED if result.datasets_read > 0 else QualityStatus.WARNING,
                {
                    "read": result.datasets_read,
                    "created": result.datasets_created,
                    "updated": result.datasets_updated,
                    "unchanged": result.datasets_unchanged,
                },
            ),
            (
                "records_read_matches_persisted",
                QualityStatus.PASSED
                if result.datasets_read == result.datasets_persisted
                else QualityStatus.FAILED,
                {
                    "read": result.datasets_read,
                    "persisted": result.datasets_persisted,
                    "errors": result.errors[:5],
                },
            ),
        ]
        for check_type, status, details in checks:
            self._session.add(
                DataQualityCheck(
                    ingestion_run_id=run.id, check_type=check_type, status=status, details=details
                )
            )
        await self._session.flush()

    async def _record_change(
        self,
        *,
        run: IngestionRun,
        change_type: ChangeType,
        summary: dict[str, Any],
        dataset_id: uuid.UUID | None = None,
        resource_id: uuid.UUID | None = None,
        current_snapshot_id: uuid.UUID | None = None,
    ) -> None:
        self._session.add(
            DataChange(
                ingestion_run_id=run.id,
                dataset_id=dataset_id,
                resource_id=resource_id,
                current_snapshot_id=current_snapshot_id,
                change_type=change_type,
                change_summary=summary,
            )
        )
        await self._session.flush()


def _fit(value: str | None, limit: int) -> str | None:
    """Fit a value into its column without inventing content.

    Truncation only ever removes characters, and the RAW payload keeps the
    original string, so nothing is lost for provenance purposes.
    """
    if value is None:
        return None
    cleaned = value.strip()
    if not cleaned:
        return None
    return cleaned[:limit]


def _schema_keys(datasets: Iterable[SourceDataset]) -> set[str]:
    keys: set[str] = set()
    for dataset in datasets:
        keys.update(dataset.raw_metadata.keys())
    return keys


def _fingerprint_keys(keys: set[str]) -> str | None:
    if not keys:
        return None
    return hashlib.sha256("\n".join(sorted(keys)).encode("utf-8")).hexdigest()


def _schema_fingerprint(datasets: Iterable[SourceDataset]) -> str:
    """Fingerprint of the upstream field set, to detect schema drift."""
    return _fingerprint_keys(_schema_keys(datasets)) or hashlib.sha256(b"").hexdigest()


def _source_lock_key(source_id: uuid.UUID) -> int:
    return int.from_bytes(hashlib.sha256(source_id.bytes).digest()[:8], "big", signed=True)


def _reset_rolled_back_counters(result: SyncResult) -> None:
    result.datasets_created = 0
    result.datasets_updated = 0
    result.datasets_unchanged = 0
    result.datasets_removed = 0
    result.resources_upserted = 0
    result.snapshots_stored = 0
    result.changes_recorded = 0


class _CatalogValidationError(Exception):
    pass


def _changed_fields(
    dataset: Dataset, incoming: SourceDataset, organization_id: uuid.UUID | None
) -> list[str]:
    comparisons: dict[str, tuple[Any, Any]] = {
        "title": (dataset.title, incoming.title),
        "description": (dataset.description, incoming.description),
        "topic": (dataset.topic, incoming.topic),
        "license": (dataset.license, incoming.license),
        "coverage_start": (dataset.coverage_start, incoming.coverage_start),
        "coverage_end": (dataset.coverage_end, incoming.coverage_end),
        "last_source_update": (dataset.last_source_update, incoming.last_source_update),
        "landing_url": (dataset.landing_url, incoming.landing_url),
        "organization_id": (dataset.organization_id, organization_id),
    }
    return [name for name, (before, after) in comparisons.items() if before != after]


__all__ = ["TRANSFORMATION_VERSION", "CatalogSyncService", "SyncResult"]
