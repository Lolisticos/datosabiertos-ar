"""Data sources: the technical origin of everything we ingest.

A ``DataSource`` is created by an operator (or a seed migration) *before* any
ingestion runs. Connectors never accept a URL from a request: they always work
against a configured, authorized source.
"""

from __future__ import annotations

import uuid
from enum import StrEnum
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, Enum, ForeignKey, Index, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ...db.base import Base, TimestampMixin, UuidPrimaryKeyMixin

if TYPE_CHECKING:
    from ..catalog.models import Dataset
    from ..ingestion.models import IngestionRun, ResourceSnapshot
    from ..organizations.models import Organization


class SourceType(StrEnum):
    CKAN = "ckan"
    DKAN = "dkan"
    REST_API = "rest_api"
    FILE_DOWNLOAD = "file_download"
    HTML = "html"
    OTHER = "other"


class DataSource(UuidPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "data_source"

    organization_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("organization.id", ondelete="SET NULL"), nullable=True
    )
    jurisdiction_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("jurisdiction.id", ondelete="SET NULL"), nullable=True
    )
    slug: Mapped[str] = mapped_column(String(64), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    base_url: Mapped[str] = mapped_column(String(1024), nullable=False)
    source_type: Mapped[SourceType] = mapped_column(
        Enum(
            SourceType,
            name="source_type",
            values_callable=lambda enum: [member.value for member in enum],
        ),
        nullable=False,
    )
    license: Mapped[str | None] = mapped_column(String(255), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_active: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True, server_default="true"
    )

    organization: Mapped[Organization | None] = relationship(back_populates="sources")
    datasets: Mapped[list[Dataset]] = relationship(back_populates="source")
    ingestion_runs: Mapped[list[IngestionRun]] = relationship(back_populates="source")
    snapshots: Mapped[list[ResourceSnapshot]] = relationship(back_populates="source")

    __table_args__ = (
        Index("uq_data_source_slug", "slug", unique=True),
        Index("uq_data_source_base_url", "base_url", unique=True),
        Index("ix_data_source_source_type", "source_type"),
    )
