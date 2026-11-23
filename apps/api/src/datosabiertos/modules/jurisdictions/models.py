"""Territorial entities.

Argentine geography does not have a single official code system: INDEC, GeoRef,
provincial and municipal catalogues each carry their own identifiers. The model
therefore keeps a stable internal ``jurisdiction`` row plus an explicit
``jurisdiction_code`` table so several schemes can coexist for the same place
without guessing which one is canonical.
"""

from __future__ import annotations

import uuid
from enum import StrEnum
from typing import Any

from geoalchemy2 import Geometry
from sqlalchemy import Enum, ForeignKey, Index, String, UniqueConstraint, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ...db.base import Base, TimestampMixin, UuidPrimaryKeyMixin


class JurisdictionType(StrEnum):
    COUNTRY = "country"
    PROVINCE = "province"
    DEPARTMENT = "department"
    MUNICIPALITY = "municipality"
    LOCALITY = "locality"


class Jurisdiction(UuidPrimaryKeyMixin, TimestampMixin, Base):
    """A territorial unit at any level, from Nación down to a locality."""

    __tablename__ = "jurisdiction"

    name: Mapped[str] = mapped_column(String(200), nullable=False)
    type: Mapped[JurisdictionType] = mapped_column(
        Enum(
            JurisdictionType,
            name="jurisdiction_type",
            values_callable=lambda enum: [member.value for member in enum],
        ),
        nullable=False,
    )
    parent_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("jurisdiction.id", ondelete="RESTRICT"), nullable=True
    )
    official_code: Mapped[str | None] = mapped_column(String(64), nullable=True)
    geometry: Mapped[Any | None] = mapped_column(
        Geometry(geometry_type="GEOMETRY", srid=4326, spatial_index=False), nullable=True
    )

    parent: Mapped[Jurisdiction | None] = relationship(
        remote_side="Jurisdiction.id", backref="children"
    )
    codes: Mapped[list[JurisdictionCode]] = relationship(
        back_populates="jurisdiction", cascade="all, delete-orphan"
    )

    __table_args__ = (
        UniqueConstraint("parent_id", "type", "name", name="uq_jurisdiction_parent_type_name"),
        # Roots (Nación) have a NULL parent, which a plain unique constraint ignores.
        Index(
            "uq_jurisdiction_root_type_name",
            "type",
            "name",
            unique=True,
            postgresql_where=text("parent_id IS NULL"),
        ),
        Index("ix_jurisdiction_parent_id", "parent_id"),
        Index("ix_jurisdiction_type", "type"),
    )


class JurisdictionCode(UuidPrimaryKeyMixin, TimestampMixin, Base):
    """One official code for a jurisdiction within a named coding scheme."""

    __tablename__ = "jurisdiction_code"

    jurisdiction_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("jurisdiction.id", ondelete="CASCADE"), nullable=False
    )
    scheme: Mapped[str] = mapped_column(String(64), nullable=False)
    code: Mapped[str] = mapped_column(String(64), nullable=False)

    jurisdiction: Mapped[Jurisdiction] = relationship(back_populates="codes")

    __table_args__ = (
        UniqueConstraint("scheme", "code", name="uq_jurisdiction_code_scheme_code"),
        Index("ix_jurisdiction_code_jurisdiction_id", "jurisdiction_id"),
    )
