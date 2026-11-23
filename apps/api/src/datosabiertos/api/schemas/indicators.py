"""Stable HTTP contracts for published statistical indicators."""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field

from .common import DateRange, ReferencedSource


class IndicatorSummaryOut(BaseModel):
    code: str
    name: str
    description: str | None = None
    unit: str
    frequency: str | None = None
    topic: str | None = None
    source: ReferencedSource | None = None
    latest_period: date | None = None
    latest_value: Decimal | None = None
    last_updated_at: datetime | None = None


class IndicatorDetailOut(IndicatorSummaryOut):
    methodology: str | None = None
    source_series_id: str | None = None
    source_url: str | None = None
    methodology_url: str | None = None
    license: str | None = None
    transformation_name: str | None = None
    transformation_version: str | None = None
    snapshot_id: UUID | None = None
    raw_content_hash: str | None = None
    normalized_hash: str | None = None
    downloaded_at: datetime | None = None


class ObservationOut(BaseModel):
    id: UUID
    period_start: date
    period_end: date | None = None
    value: Decimal | None
    unit: str
    dimensions: dict[str, Any]
    jurisdiction_id: UUID | None = None
    snapshot_id: UUID | None = None
    published_at: datetime | None = None


class IndicatorCoverageOut(BaseModel):
    code: str
    period: DateRange
    observation_count: int = Field(ge=0)
    missing_value_count: int = Field(ge=0)
    jurisdiction_count: int = Field(ge=0)
    frequency: str | None = None


__all__ = [
    "IndicatorCoverageOut",
    "IndicatorDetailOut",
    "IndicatorSummaryOut",
    "ObservationOut",
]
