"""Provenance of transformations applied to RAW snapshots.

Every normalization step registers the version that produced its output, so a
result can be reproduced from the preserved original bytes.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from enum import StrEnum
from typing import TYPE_CHECKING

from sqlalchemy import (
    DateTime,
    Enum,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ...db.base import Base, TimestampMixin, UuidPrimaryKeyMixin

if TYPE_CHECKING:
    from ..ingestion.models import ResourceSnapshot


class TransformationStatus(StrEnum):
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"


class TransformationRun(UuidPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "transformation_run"

    snapshot_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("resource_snapshot.id", ondelete="RESTRICT"), nullable=False
    )
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    version: Mapped[str] = mapped_column(String(64), nullable=False)
    status: Mapped[TransformationStatus] = mapped_column(
        Enum(
            TransformationStatus,
            name="transformation_status",
            values_callable=lambda enum: [member.value for member in enum],
        ),
        nullable=False,
        default=TransformationStatus.RUNNING,
    )
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    records_in: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    records_out: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    error_summary: Mapped[str | None] = mapped_column(Text, nullable=True)

    snapshot: Mapped[ResourceSnapshot] = relationship(back_populates="transformations")

    __table_args__ = (
        UniqueConstraint(
            "snapshot_id", "name", "version", name="uq_transformation_run_snapshot_name_version"
        ),
        Index("ix_transformation_run_snapshot_id", "snapshot_id"),
    )
