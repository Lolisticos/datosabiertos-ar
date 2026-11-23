"""Data quality checks produced by ingestion and validation steps."""

from __future__ import annotations

import uuid
from datetime import datetime
from enum import StrEnum
from typing import TYPE_CHECKING, Any

from sqlalchemy import DateTime, Enum, ForeignKey, Index, String, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ...db.base import Base, UuidPrimaryKeyMixin

if TYPE_CHECKING:
    from ..ingestion.models import IngestionRun


class QualityStatus(StrEnum):
    PASSED = "passed"
    WARNING = "warning"
    FAILED = "failed"
    SKIPPED = "skipped"


class DataQualityCheck(UuidPrimaryKeyMixin, Base):
    """Outcome of one deterministic validation over one ingestion run."""

    __tablename__ = "data_quality_check"

    ingestion_run_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("ingestion_run.id", ondelete="CASCADE"), nullable=False
    )
    check_type: Mapped[str] = mapped_column(String(64), nullable=False)
    status: Mapped[QualityStatus] = mapped_column(
        Enum(
            QualityStatus,
            name="quality_status",
            values_callable=lambda enum: [member.value for member in enum],
        ),
        nullable=False,
    )
    details: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    checked_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    ingestion_run: Mapped[IngestionRun] = relationship(back_populates="quality_checks")

    __table_args__ = (
        Index("ix_data_quality_check_run_id", "ingestion_run_id"),
        Index("ix_data_quality_check_status", "status"),
    )
