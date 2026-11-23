"""Canonical data structures exchanged between source connectors and the platform.

These models are the *only* thing the ingestion core knows about a source. Source
specific payloads are preserved verbatim inside ``SourceDataset.raw_metadata`` and
``ConnectorPage.raw_payload`` so a resource can always be reprocessed without
downloading it again.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import AsyncIterator, Iterable, Mapping
from datetime import date, datetime
from enum import StrEnum
from typing import Any, Protocol, runtime_checkable

from pydantic import BaseModel, ConfigDict, Field, field_validator


class SourceType(StrEnum):
    """Technical access pattern of a data source."""

    CKAN = "ckan"
    DKAN = "dkan"
    REST_API = "rest_api"
    FILE_DOWNLOAD = "file_download"
    HTML = "html"
    OTHER = "other"


class _Frozen(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")


class SourceResource(_Frozen):
    """A file or endpoint published by a dataset."""

    external_id: str
    name: str | None = None
    format: str | None = None
    url: str
    mime_type: str | None = None
    checksum: str | None = None
    file_size: int | None = Field(default=None, ge=0)
    last_modified: datetime | None = None
    description: str | None = None

    @field_validator("format")
    @classmethod
    def _normalize_format(cls, value: str | None) -> str | None:
        if value is None:
            return None
        cleaned = value.strip().upper()
        return cleaned or None


class SourceOrganization(_Frozen):
    """Publisher as described by the source, before it is mapped to `Organization`."""

    external_id: str
    name: str
    official_url: str | None = None


class SourceDataset(_Frozen):
    """One logical dataset as discovered in a source catalogue."""

    external_id: str
    title: str
    description: str | None = None
    organization: SourceOrganization | None = None
    topic: str | None = None
    license: str | None = None
    coverage_start: date | None = None
    coverage_end: date | None = None
    last_source_update: datetime | None = None
    landing_url: str | None = None
    resources: tuple[SourceResource, ...] = ()
    raw_metadata: dict[str, Any] = Field(default_factory=dict)

    def metadata_hash(self) -> str:
        """Stable fingerprint of the metadata a user can see.

        Used for change detection: it ignores key ordering and formatting so an
        unchanged dataset does not produce a false change record.
        """
        payload = {
            "external_id": self.external_id,
            "title": self.title,
            "description": self.description,
            "organization": None if self.organization is None else self.organization.model_dump(),
            "topic": self.topic,
            "license": self.license,
            "coverage_start": _iso(self.coverage_start),
            "coverage_end": _iso(self.coverage_end),
            "last_source_update": _iso(self.last_source_update),
            "landing_url": self.landing_url,
            "resources": sorted(
                (
                    {
                        "external_id": resource.external_id,
                        "format": resource.format,
                        "url": resource.url,
                        "mime_type": resource.mime_type,
                        "checksum": resource.checksum,
                        "file_size": resource.file_size,
                        "last_modified": _iso(resource.last_modified),
                    }
                    for resource in self.resources
                ),
                key=lambda item: str(item["external_id"]),
            ),
        }
        return canonical_hash(payload)


class ConnectorPage(_Frozen):
    """One page of a catalogue discovery walk, preserved as RAW evidence."""

    datasets: tuple[SourceDataset, ...]
    raw_payload: bytes
    media_type: str
    content_hash: str
    offset: int = Field(ge=0)
    total_available: int | None = Field(default=None, ge=0)
    fetched_at: datetime


class FetchResult(_Frozen):
    """Bytes (or a failure) obtained for a single resource."""

    url: str
    status_code: int
    content: bytes
    content_hash: str
    media_type: str | None = None
    source_last_modified: datetime | None = None
    fetched_at: datetime

    @property
    def size(self) -> int:
        return len(self.content)


class ConnectorMetadata(_Frozen):
    name: str
    version: str
    source_type: SourceType
    description: str = ""


@runtime_checkable
class SourceConnector(Protocol):
    """Contract implemented by every source connector.

    ``discover`` streams pages so a 1.000+ dataset catalogue never has to be held
    in memory at once, and every page keeps the untouched upstream payload.
    """

    def metadata(self) -> ConnectorMetadata: ...

    def discover(self) -> AsyncIterator[ConnectorPage]: ...

    async def fetch(self, resource: SourceResource) -> FetchResult: ...


def _iso(value: date | datetime | None) -> str | None:
    return None if value is None else value.isoformat()


def canonical_json(payload: Mapping[str, Any] | Iterable[Any]) -> bytes:
    """Deterministic JSON encoding used for hashing and reproducibility."""
    return json.dumps(
        payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False, default=str
    ).encode("utf-8")


def canonical_hash(payload: Mapping[str, Any] | Iterable[Any]) -> str:
    return hashlib.sha256(canonical_json(payload)).hexdigest()


def content_hash(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


__all__ = [
    "ConnectorMetadata",
    "ConnectorPage",
    "FetchResult",
    "SourceConnector",
    "SourceDataset",
    "SourceOrganization",
    "SourceResource",
    "SourceType",
    "canonical_hash",
    "canonical_json",
    "content_hash",
]
