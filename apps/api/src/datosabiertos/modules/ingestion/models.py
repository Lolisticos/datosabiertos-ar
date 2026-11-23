"""Ingestion executions and preserved RAW artifacts."""

from __future__ import annotations

import uuid
from datetime import datetime
from enum import StrEnum
from typing import TYPE_CHECKING, Any

from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ...db.base import Base, TimestampMixin, UuidPrimaryKeyMixin

if TYPE_CHECKING:
    from ..catalog.models import Dataset, DatasetResource
    from ..history.models import DataChange
    from ..provenance.models import TransformationRun
    from ..quality.models import DataQualityCheck
    from ..sources.models import DataSource


class IngestionRunStatus(StrEnum):
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    PARTIAL = "partial"
    FAILED = "failed"


class IngestionRunType(StrEnum):
    CATALOG_DISCOVERY = "catalog_discovery"
    RESOURCE_FETCH = "resource_fetch"


class IngestionRun(UuidPrimaryKeyMixin, TimestampMixin, Base):
    """One execution of a connector, with counters and a safe error summary."""

    __tablename__ = "ingestion_run"

    source_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("data_source.id", ondelete="RESTRICT"), nullable=False
    )
    dataset_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("dataset.id", ondelete="SET NULL"), nullable=True
    )
    resource_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("dataset_resource.id", ondelete="SET NULL"), nullable=True
    )
    run_type: Mapped[IngestionRunType] = mapped_column(
        Enum(
            IngestionRunType,
            name="ingestion_run_type",
            values_callable=lambda enum: [member.value for member in enum],
        ),
        nullable=False,
    )
    status: Mapped[IngestionRunStatus] = mapped_column(
        Enum(
            IngestionRunStatus,
            name="ingestion_run_status",
            values_callable=lambda enum: [member.value for member in enum],
        ),
        nullable=False,
        default=IngestionRunStatus.RUNNING,
        server_default=IngestionRunStatus.RUNNING.value,
    )
    triggered_by: Mapped[str] = mapped_column(String(64), nullable=False, default="cli")
    transformation_version: Mapped[str | None] = mapped_column(String(64), nullable=True)
    schema_fingerprint: Mapped[str | None] = mapped_column(String(64), nullable=True)

    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    records_read: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default="0"
    )
    records_accepted: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default="0"
    )
    records_rejected: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default="0"
    )
    error_summary: Mapped[str | None] = mapped_column(Text, nullable=True)

    source: Mapped[DataSource] = relationship(back_populates="ingestion_runs")
    dataset: Mapped[Dataset | None] = relationship()
    resource: Mapped[DatasetResource | None] = relationship(back_populates="ingestion_runs")
    snapshots: Mapped[list[ResourceSnapshot]] = relationship(back_populates="ingestion_run")
    quality_checks: Mapped[list[DataQualityCheck]] = relationship(back_populates="ingestion_run")
    changes: Mapped[list[DataChange]] = relationship(back_populates="ingestion_run")

    __table_args__ = (
        Index("ix_ingestion_run_source_started", "source_id", "started_at"),
        Index("ix_ingestion_run_status", "status"),
    )


class SnapshotKind(StrEnum):
    CATALOG_PAYLOAD = "catalog_payload"
    RESOURCE_FILE = "resource_file"


class ResourceSnapshot(UuidPrimaryKeyMixin, TimestampMixin, Base):
    """Immutable RAW artifact: exactly what the source returned, plus its hash.

    ``kind='catalog_payload'`` stores the untouched catalogue page (metadata
    discovery) and uses ``source_id``; ``kind='resource_file'`` stores the bytes
    of a distribution and uses ``resource_id``.
    """

    __tablename__ = "resource_snapshot"

    kind: Mapped[SnapshotKind] = mapped_column(
        Enum(
            SnapshotKind,
            name="snapshot_kind",
            values_callable=lambda enum: [member.value for member in enum],
        ),
        nullable=False,
    )
    source_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("data_source.id", ondelete="RESTRICT"), nullable=True
    )
    resource_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("dataset_resource.id", ondelete="RESTRICT"), nullable=True
    )
    ingestion_run_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("ingestion_run.id", ondelete="SET NULL"), nullable=True
    )

    content_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    normalized_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)
    storage_key: Mapped[str] = mapped_column(String(512), nullable=False)
    media_type: Mapped[str | None] = mapped_column(String(255), nullable=True)
    file_size: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    schema_fingerprint: Mapped[str | None] = mapped_column(String(64), nullable=True)

    fetched_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    source_last_modified: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    source: Mapped[DataSource | None] = relationship(back_populates="snapshots")
    resource: Mapped[DatasetResource | None] = relationship(back_populates="snapshots")
    ingestion_run: Mapped[IngestionRun | None] = relationship(back_populates="snapshots")
    transformations: Mapped[list[TransformationRun]] = relationship(back_populates="snapshot")

    __table_args__ = (
        Index(
            "uq_resource_snapshot_resource_hash",
            "resource_id",
            "content_hash",
            unique=True,
            postgresql_where=text("resource_id IS NOT NULL"),
        ),
        Index(
            "uq_resource_snapshot_catalog_hash",
            "source_id",
            "content_hash",
            unique=True,
            postgresql_where=text("resource_id IS NULL"),
        ),
        Index("ix_resource_snapshot_fetched_at", "fetched_at"),
        Index("ix_resource_snapshot_content_hash", "content_hash"),
        Index("ix_resource_snapshot_normalized_hash", "normalized_hash"),
        Index("uq_resource_snapshot_storage_key", "storage_key", unique=True),
        CheckConstraint(
            "(kind = 'catalog_payload' AND source_id IS NOT NULL AND resource_id IS NULL) "
            "OR (kind = 'resource_file' AND source_id IS NULL AND resource_id IS NOT NULL)",
            name="ck_resource_snapshot_owner",
        ),
    )


class SnapshotMetadata(Base):
    """Auxiliary structured metadata captured with a snapshot.

    Kept separate from ``ResourceSnapshot`` so response headers (or future
    connector-specific evidence) never force a migration on the main table.
    """

    __tablename__ = "snapshot_metadata"

    snapshot_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("resource_snapshot.id", ondelete="CASCADE"), primary_key=True
    )
    payload: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)


__all__ = [
    "IngestionRun",
    "IngestionRunStatus",
    "IngestionRunType",
    "ResourceSnapshot",
    "SnapshotKind",
    "SnapshotMetadata",
]
