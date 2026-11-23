"""Publishing organizations (organismos)."""

from __future__ import annotations

import uuid
from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, Index, String, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ...db.base import Base, TimestampMixin, UuidPrimaryKeyMixin

if TYPE_CHECKING:
    from ..catalog.models import Dataset
    from ..sources.models import DataSource


class Organization(UuidPrimaryKeyMixin, TimestampMixin, Base):
    """Entity that publishes data.

    Organizations are de-duplicated by name across sources. A source-local
    identifier is not stored here because CKAN (and every other catalogue) scopes
    its organization ids to itself; the original payload is preserved on the
    dataset's RAW snapshot instead.
    """

    __tablename__ = "organization"

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    acronym: Mapped[str | None] = mapped_column(String(32), nullable=True)
    jurisdiction_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("jurisdiction.id", ondelete="SET NULL"), nullable=True
    )
    official_url: Mapped[str | None] = mapped_column(String(1024), nullable=True)

    datasets: Mapped[list[Dataset]] = relationship(back_populates="organization")
    sources: Mapped[list[DataSource]] = relationship(back_populates="organization")

    __table_args__ = (
        # Case-insensitive de-duplication without relying on the client.
        Index("uq_organization_name_lower", text("lower(name)"), unique=True),
    )
