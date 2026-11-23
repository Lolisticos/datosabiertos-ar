"""Indicators and their observations.

This is the structural answer to "add dimensions without a migration per
dataset": an observation carries a canonical ``dimensions`` JSONB document plus
``dimension_hash`` (SHA-256 of the canonical JSON). The uniqueness key is
``(indicator_id, jurisdiction_id, period_start, dimension_hash)``, so a new
dimension (sex, age bracket, sector, currency…) needs a new observation, never a
schema change. Values are ``Numeric`` — never floating point.
"""

from __future__ import annotations

import uuid
from datetime import date, datetime
from enum import StrEnum
from typing import TYPE_CHECKING, Any

from sqlalchemy import (
    Date,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ...db.base import Base, TimestampMixin, UuidPrimaryKeyMixin

if TYPE_CHECKING:
    from ..ingestion.models import ResourceSnapshot
    from ..jurisdictions.models import Jurisdiction
    from ..sources.models import DataSource


class ObservationReviewStatus(StrEnum):
    DRAFT = "draft"
    REVIEWED = "reviewed"
    PUBLISHED = "published"


class Indicator(UuidPrimaryKeyMixin, TimestampMixin, Base):
    """Semantic definition of a measurable quantity, with its methodology."""

    __tablename__ = "indicator"

    code: Mapped[str] = mapped_column(String(128), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    unit: Mapped[str] = mapped_column(String(64), nullable=False)
    methodology: Mapped[str | None] = mapped_column(Text, nullable=True)
    source_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("data_source.id", ondelete="SET NULL"), nullable=True
    )
    topic: Mapped[str | None] = mapped_column(String(128), nullable=True)

    observations: Mapped[list[IndicatorObservation]] = relationship(back_populates="indicator")
    source: Mapped[DataSource | None] = relationship()

    __table_args__ = (
        Index("uq_indicator_code", "code", unique=True),
        Index("ix_indicator_topic", "topic"),
    )


class IndicatorObservation(UuidPrimaryKeyMixin, Base):
    __tablename__ = "indicator_observation"

    indicator_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("indicator.id", ondelete="RESTRICT"), nullable=False
    )
    jurisdiction_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("jurisdiction.id", ondelete="RESTRICT"), nullable=True
    )
    period_start: Mapped[date] = mapped_column(Date, nullable=False)
    period_end: Mapped[date | None] = mapped_column(Date, nullable=True)
    value: Mapped[Any] = mapped_column(Numeric(24, 6), nullable=False)
    unit: Mapped[str] = mapped_column(String(64), nullable=False)
    dimensions: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    dimension_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    snapshot_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("resource_snapshot.id", ondelete="SET NULL"), nullable=True
    )
    review_status: Mapped[ObservationReviewStatus] = mapped_column(
        Enum(
            ObservationReviewStatus,
            name="observation_review_status",
            values_callable=lambda enum: [member.value for member in enum],
        ),
        nullable=False,
        default=ObservationReviewStatus.DRAFT,
        server_default=ObservationReviewStatus.DRAFT.value,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    indicator: Mapped[Indicator] = relationship(back_populates="observations")
    jurisdiction: Mapped[Jurisdiction | None] = relationship()
    snapshot: Mapped[ResourceSnapshot | None] = relationship()

    __table_args__ = (
        UniqueConstraint(
            "indicator_id",
            "jurisdiction_id",
            "period_start",
            "dimension_hash",
            name="uq_indicator_observation_key",
            postgresql_nulls_not_distinct=True,
        ),
        Index("ix_indicator_observation_indicator_period", "indicator_id", "period_start"),
        Index("ix_indicator_observation_jurisdiction_id", "jurisdiction_id"),
    )
