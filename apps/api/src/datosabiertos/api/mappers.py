"""ORM → HTTP contract mapping (no business logic, no ORM leakage)."""

from __future__ import annotations

from collections.abc import Iterable
from typing import Any

from ..modules.catalog.models import Dataset, DatasetResource
from ..modules.catalog.queries import DatasetDetail
from ..modules.history.models import DataChange
from ..modules.ingestion.models import IngestionRun
from ..modules.ingestion.queries import SourceSummary
from .schemas.catalog import (
    ChangeOut,
    DatasetDetailOut,
    DatasetListItem,
    ProvenanceOut,
    QualityCheckOut,
    ResourceOut,
    RunOut,
    SourceOut,
)
from .schemas.common import DateRange, ReferencedOrganization, ReferencedSource


def referral_source(dataset: Dataset) -> ReferencedSource:
    source = dataset.source
    return ReferencedSource(
        id=source.id,
        slug=source.slug,
        name=source.name,
        source_type=source.source_type.value,
        base_url=source.base_url,
    )


def referral_organization(dataset: Dataset) -> ReferencedOrganization | None:
    organization = dataset.organization
    if organization is None:
        return None
    return ReferencedOrganization(
        id=organization.id,
        name=organization.name,
        acronym=organization.acronym,
        official_url=organization.official_url,
    )


def _formats(resources: Iterable[DatasetResource]) -> list[str]:
    values = {resource.format for resource in resources if resource.format}
    return sorted(values)


def dataset_list_item(dataset: Dataset) -> DatasetListItem:
    resources = list(dataset.resources)
    return DatasetListItem(
        id=dataset.id,
        title=dataset.title,
        description=dataset.description,
        topic=dataset.topic,
        license=dataset.license,
        organization=referral_organization(dataset),
        source=referral_source(dataset),
        formats=_formats(resources),
        resource_count=len([resource for resource in resources if resource.is_available]),
        coverage=DateRange(start=dataset.coverage_start, end=dataset.coverage_end),
        last_source_update=dataset.last_source_update,
        last_successful_sync=dataset.last_successful_sync,
        is_available=dataset.is_available,
        landing_url=dataset.landing_url,
    )


def resource_out(resource: DatasetResource) -> ResourceOut:
    return ResourceOut(
        id=resource.id,
        external_id=resource.external_id,
        name=resource.name,
        format=resource.format,
        url=resource.url,
        mime_type=resource.mime_type,
        file_size=resource.file_size,
        checksum=resource.checksum,
        last_modified=resource.last_modified,
        is_available=resource.is_available,
    )


def quality_check_out(check: Any) -> QualityCheckOut:
    return QualityCheckOut(
        id=check.id,
        check_type=check.check_type,
        status=check.status.value if hasattr(check.status, "value") else str(check.status),
        details=check.details or {},
        checked_at=check.checked_at,
    )


def run_out(run: IngestionRun) -> RunOut:
    source = run.source
    return RunOut(
        id=run.id,
        source=ReferencedSource(
            id=source.id,
            slug=source.slug,
            name=source.name,
            source_type=source.source_type.value,
            base_url=source.base_url,
        )
        if source is not None
        else None,
        run_type=run.run_type.value,
        status=run.status.value,
        triggered_by=run.triggered_by,
        transformation_version=run.transformation_version,
        started_at=run.started_at,
        finished_at=run.finished_at,
        records_read=run.records_read,
        records_accepted=run.records_accepted,
        records_rejected=run.records_rejected,
        error_summary=run.error_summary,
        # Never trigger lazy IO here: only read relationships already loaded.
        quality_checks=[
            quality_check_out(check) for check in run.__dict__.get("quality_checks") or []
        ],
    )


def change_out(change: DataChange) -> ChangeOut:
    dataset = change.dataset
    resource = change.resource
    return ChangeOut(
        id=change.id,
        change_type=change.change_type.value,
        detected_at=change.detected_at,
        dataset=(None if dataset is None else {"id": dataset.id, "title": dataset.title}),
        resource=(None if resource is None else {"id": resource.id, "format": resource.format}),
        change_summary=change.change_summary or {},
    )


def dataset_detail(detail: DatasetDetail) -> DatasetDetailOut:
    dataset = detail.dataset
    base = dataset_list_item(dataset)
    last_run = detail.last_run
    return DatasetDetailOut(
        **base.model_dump(),
        raw_metadata=dataset.raw_metadata,
        resources=[resource_out(resource) for resource in detail.resources],
        quality_checks=[quality_check_out(check) for check in detail.quality_checks],
        changes=[change_out(change) for change in detail.changes],
        provenance=ProvenanceOut(
            raw_snapshot_count=detail.snapshot_count,
            last_snapshot_at=detail.last_snapshot_at,
            source_landing_url=dataset.source.base_url if dataset.source else None,
            dataset_landing_url=dataset.landing_url,
        ),
        latest_run=(
            RunOut(
                id=last_run.id,
                source=None,
                run_type=last_run.run_type.value,
                status=last_run.status.value,
                triggered_by=last_run.triggered_by,
                transformation_version=last_run.transformation_version,
                started_at=last_run.started_at,
                finished_at=last_run.finished_at,
                records_read=last_run.records_read,
                records_accepted=last_run.records_accepted,
                records_rejected=last_run.records_rejected,
                error_summary=last_run.error_summary,
                quality_checks=[quality_check_out(check) for check in detail.quality_checks],
            )
            if last_run is not None
            else None
        ),
    )


def source_out(
    summary: SourceSummary,
    *,
    last_successful_run_at: Any = None,
    last_run_status: str | None = None,
) -> SourceOut:
    source = summary.source
    organization = source.organization
    return SourceOut(
        id=source.id,
        slug=source.slug,
        name=source.name,
        base_url=source.base_url,
        source_type=source.source_type.value,
        license=source.license,
        notes=source.notes,
        is_active=source.is_active,
        organization=(
            None
            if organization is None
            else ReferencedOrganization(
                id=organization.id,
                name=organization.name,
                acronym=organization.acronym,
                official_url=organization.official_url,
            )
        ),
        dataset_count=summary.dataset_count,
        last_successful_run_at=last_successful_run_at,
        last_run_status=last_run_status,
    )


__all__ = [
    "change_out",
    "dataset_detail",
    "dataset_list_item",
    "quality_check_out",
    "resource_out",
    "run_out",
    "source_out",
]
