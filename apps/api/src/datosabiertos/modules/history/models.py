"""Detected changes between snapshots and catalogue states."""

from __future__ import annotations

import uuid
from datetime import datetime
from enum import StrEnum
from typing import TYPE_CHECKING, Any

from sqlalchemy import DateTime, Enum, ForeignKey, Index, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ...db.base import Base, UuidPrimaryKeyMixin

if TYPE_CHECKING:
    from ..catalog.models import Dataset, DatasetResource
    from ..ingestion.models import IngestionRun, ResourceSnapshot


class ChangeType(StrEnum):
    DATASET_ADDED = "dataset_added"
    DATASET_REMOVED = "dataset_removed"
    RESOURCE_ADDED = "resource_added"
    RESOURCE_REMOVED = "resource_removed"
    CONTENT_CHANGED = "content_changed"
    SCHEMA_CHANGED = "schema_changed"
    METADATA_CHANGED = "metadata_changed"
    FETCH_FAILED = "fetch_failed"
    RECOVERED = "recovered"


class DataChange(UuidPrimaryKeyMixin, Base):
    """A factual, explainable difference — never a judgement of irregularity."""

    __tablename__ = "data_change"

    ingestion_run_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("ingestion_run.id", ondelete="SET NULL"), nullable=True
    )
    dataset_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("dataset.id", ondelete="CASCADE"), nullable=True
    )
    resource_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("dataset_resource.id", ondelete="CASCADE"), nullable=True
    )
    previous_snapshot_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("resource_snapshot.id", ondelete="SET NULL"), nullable=True
    )
    current_snapshot_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("resource_snapshot.id", ondelete="SET NULL"), nullable=True
    )
    change_type: Mapped[ChangeType] = mapped_column(
        Enum(
            ChangeType,
            name="change_type",
            values_callable=lambda enum: [member.value for member in enum],
        ),
        nullable=False,
    )
    change_summary: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    detected_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    dataset: Mapped[Dataset | None] = relationship(back_populates="changes")
    resource: Mapped[DatasetResource | None] = relationship(back_populates="changes")
    ingestion_run: Mapped[IngestionRun | None] = relationship(back_populates="changes")
    previous_snapshot: Mapped[ResourceSnapshot | None] = relationship(
        foreign_keys=[previous_snapshot_id]
    )
    current_snapshot: Mapped[ResourceSnapshot | None] = relationship(
        foreign_keys=[current_snapshot_id]
    )

    __table_args__ = (
        Index("ix_data_change_detected_at", "detected_at"),
        Index("ix_data_change_dataset_id", "dataset_id"),
        Index("ix_data_change_resource_id", "resource_id"),
        Index("ix_data_change_type", "change_type"),
    )
