"""Catalogue entities: datasets and their resources."""

from __future__ import annotations

import uuid
from datetime import date, datetime
from typing import TYPE_CHECKING, Any

from sqlalchemy import (
    BigInteger,
    Boolean,
    Date,
    DateTime,
    ForeignKey,
    Index,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ...db.base import Base, TimestampMixin, UuidPrimaryKeyMixin

if TYPE_CHECKING:
    from ..history.models import DataChange
    from ..ingestion.models import IngestionRun, ResourceSnapshot
    from ..organizations.models import Organization
    from ..sources.models import DataSource


class Dataset(UuidPrimaryKeyMixin, TimestampMixin, Base):
    """A logical dataset as published by a source (normalized, not RAW)."""

    __tablename__ = "dataset"

    source_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("data_source.id", ondelete="RESTRICT"), nullable=False
    )
    organization_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("organization.id", ondelete="SET NULL"), nullable=True
    )
    external_id: Mapped[str] = mapped_column(String(128), nullable=False)
    title: Mapped[str] = mapped_column(String(512), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    topic: Mapped[str | None] = mapped_column(String(128), nullable=True)
    license: Mapped[str | None] = mapped_column(String(255), nullable=True)

    # Publication/coverage dates are distinct from our own processing timestamps.
    coverage_start: Mapped[date | None] = mapped_column(Date, nullable=True)
    coverage_end: Mapped[date | None] = mapped_column(Date, nullable=True)
    last_source_update: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    last_successful_sync: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    removed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    landing_url: Mapped[str | None] = mapped_column(String(1024), nullable=True)

    # Accent-free, lower-cased projection of title/description/organization used
    # by the PostgreSQL search (``ILIKE`` on an indexed column).
    search_text: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Change detection without relying on string formatting differences upstream.
    metadata_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    is_available: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True, server_default="true"
    )
    raw_metadata: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)

    source: Mapped[DataSource] = relationship(back_populates="datasets")
    organization: Mapped[Organization | None] = relationship(back_populates="datasets")
    resources: Mapped[list[DatasetResource]] = relationship(back_populates="dataset")
    changes: Mapped[list[DataChange]] = relationship(back_populates="dataset")

    __table_args__ = (
        UniqueConstraint("source_id", "external_id", name="uq_dataset_source_external_id"),
        Index("ix_dataset_source_id", "source_id"),
        Index("ix_dataset_organization_id", "organization_id"),
        Index("ix_dataset_topic", "topic"),
        Index("ix_dataset_last_source_update", "last_source_update"),
        Index("ix_dataset_metadata_hash", "metadata_hash"),
        Index("ix_dataset_removed_at", "removed_at"),
        Index("ix_dataset_search_text", "search_text"),
        # Trigram indexes are created in the Alembic migration (needs pg_trgm).
    )


class DatasetResource(UuidPrimaryKeyMixin, TimestampMixin, Base):
    """A file or endpoint that distributes a dataset."""

    __tablename__ = "dataset_resource"

    dataset_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("dataset.id", ondelete="RESTRICT"), nullable=False
    )
    external_id: Mapped[str] = mapped_column(String(128), nullable=False)
    name: Mapped[str | None] = mapped_column(String(512), nullable=True)
    format: Mapped[str | None] = mapped_column(String(32), nullable=True)
    url: Mapped[str] = mapped_column(String(2048), nullable=False)
    mime_type: Mapped[str | None] = mapped_column(String(255), nullable=True)
    checksum: Mapped[str | None] = mapped_column(String(128), nullable=True)
    file_size: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    last_modified: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    is_available: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True, server_default="true"
    )
    removed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    dataset: Mapped[Dataset] = relationship(back_populates="resources")
    snapshots: Mapped[list[ResourceSnapshot]] = relationship(back_populates="resource")
    ingestion_runs: Mapped[list[IngestionRun]] = relationship(back_populates="resource")
    changes: Mapped[list[DataChange]] = relationship(back_populates="resource")

    __table_args__ = (
        UniqueConstraint(
            "dataset_id", "external_id", name="uq_dataset_resource_dataset_external_id"
        ),
        Index("ix_dataset_resource_format", "format"),
        Index("ix_dataset_resource_dataset_id", "dataset_id"),
        Index("ix_dataset_resource_removed_at", "removed_at"),
    )
