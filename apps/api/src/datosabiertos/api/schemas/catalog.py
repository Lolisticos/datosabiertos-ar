"""Catalogue, ingestion, quality and history HTTP contracts."""

from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from .common import (
    DateRange,
    ReferencedDataset,
    ReferencedOrganization,
    ReferencedResource,
    ReferencedSource,
)


class ResourceOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    external_id: str
    name: str | None = None
    format: str | None = None
    url: str
    mime_type: str | None = None
    file_size: int | None = None
    checksum: str | None = None
    last_modified: datetime | None = None
    is_available: bool


class DatasetListItem(BaseModel):
    id: UUID
    title: str
    description: str | None = None
    topic: str | None = None
    license: str | None = None
    organization: ReferencedOrganization | None = None
    source: ReferencedSource
    formats: list[str]
    resource_count: int = Field(ge=0)
    coverage: DateRange
    last_source_update: datetime | None = None
    last_successful_sync: datetime | None = None
    is_available: bool
    landing_url: str | None = None


class QualityCheckOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    check_type: str
    status: str
    details: dict[str, Any]
    checked_at: datetime


class ChangeOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    change_type: str
    detected_at: datetime
    dataset: ReferencedDataset | None = None
    resource: ReferencedResource | None = None
    change_summary: dict[str, Any]


class ProvenanceOut(BaseModel):
    raw_snapshot_count: int = Field(ge=0)
    last_snapshot_at: datetime | None = None
    source_landing_url: str | None = None
    dataset_landing_url: str | None = None


class DatasetDetailOut(DatasetListItem):
    raw_metadata: dict[str, Any] | None = None
    resources: list[ResourceOut]
    quality_checks: list[QualityCheckOut]
    changes: list[ChangeOut]
    provenance: ProvenanceOut
    latest_run: RunOut | None = None


class RunOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    source: ReferencedSource | None = None
    run_type: str
    status: str
    triggered_by: str
    transformation_version: str | None = None
    started_at: datetime
    finished_at: datetime | None = None
    records_read: int
    records_accepted: int
    records_rejected: int
    error_summary: str | None = None
    quality_checks: list[QualityCheckOut] = Field(default_factory=list)


class ChangeListItem(ChangeOut):
    dataset: ReferencedDataset | None = None
    source_slug: str | None = None


class SourceOut(BaseModel):
    id: UUID
    slug: str
    name: str
    base_url: str
    source_type: str
    license: str | None = None
    notes: str | None = None
    is_active: bool
    organization: ReferencedOrganization | None = None
    dataset_count: int = Field(ge=0)
    last_successful_run_at: datetime | None = None
    last_run_status: str | None = None


class StatsOut(BaseModel):
    datasets: int = Field(ge=0)
    datasets_available: int = Field(ge=0)
    resources: int = Field(ge=0)
    sources: int = Field(ge=0)
    organizations: int = Field(ge=0)
    topics: int = Field(ge=0)
    raw_snapshots: int = Field(ge=0)
    changes_last_7_days: int = Field(ge=0)
    latest_source_update: datetime | None = None
    last_run: RunOut | None = None
    last_successful_run: RunOut | None = None
    coverage_note: str


class DatasetFiltersOut(BaseModel):
    """Machine-readable filter options, derived from stored data."""

    topics: list[str]
    formats: list[str]
    sources: list[ReferencedSource]


class DatasetCoverageOut(BaseModel):
    available: bool
    visualizations: list[str]
    reason: str
    dataset_id: UUID


__all__ = [
    "ChangeListItem",
    "ChangeOut",
    "DatasetCoverageOut",
    "DatasetDetailOut",
    "DatasetFiltersOut",
    "DatasetListItem",
    "ProvenanceOut",
    "QualityCheckOut",
    "ResourceOut",
    "RunOut",
    "SourceOut",
    "StatsOut",
]
