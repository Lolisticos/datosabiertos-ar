"""Dataset search and discovery (PostgreSQL only).

Search is deliberately a repository-level concern behind a small interface so a
future strategy (another engine, ranking, embeddings) can replace the internals
without touching routers or the frontend contract.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import datetime
from typing import cast

from sqlalchemy import ColumnElement, Select, and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload, selectinload

from ...core.text import normalize_query as _normalize_query
from ..catalog.models import Dataset, DatasetResource
from ..organizations.models import Organization
from ..sources.models import DataSource

MAX_QUERY_LENGTH = 200


@dataclass(frozen=True)
class DatasetFilters:
    """Everything a catalogue visitor can filter by."""

    q: str | None = None
    source: str | None = None
    organization_id: uuid.UUID | None = None
    topic: str | None = None
    format: str | None = None
    jurisdiction_id: uuid.UUID | None = None
    updated_since: datetime | None = None
    available_only: bool = True


@dataclass(frozen=True)
class DatasetPage:
    items: list[Dataset]
    total: int
    page: int
    page_size: int

    @property
    def pages(self) -> int:
        return (self.total + self.page_size - 1) // self.page_size if self.page_size else 0


def normalize_query(value: str | None) -> str | None:
    """Public entry point: accent-free, whitespace-collapsed, bounded text."""
    return _normalize_query(value, limit=MAX_QUERY_LENGTH)


def _escape_like(term: str) -> str:
    return term.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")


def _apply_filters(
    statement: Select[tuple[Dataset]], filters: DatasetFilters
) -> Select[tuple[Dataset]]:
    conditions: list[ColumnElement[bool]] = []
    statement = statement.join(Dataset.source).outerjoin(Dataset.organization)
    if filters.available_only:
        conditions.append(Dataset.is_available.is_(True))
    if filters.source:
        conditions.append(DataSource.slug == filters.source)
    if filters.organization_id:
        conditions.append(Dataset.organization_id == filters.organization_id)
    if filters.jurisdiction_id:
        conditions.append(Dataset.source.has(DataSource.jurisdiction_id == filters.jurisdiction_id))
    if filters.topic:
        conditions.append(func.lower(Dataset.topic) == filters.topic.lower())
    if filters.updated_since:
        conditions.append(Dataset.last_source_update >= filters.updated_since)
    if filters.format:
        wanted = filters.format.upper()
        conditions.append(
            Dataset.id.in_(
                select(DatasetResource.dataset_id).where(DatasetResource.format == wanted)
            )
        )
    query = normalize_query(filters.q)
    if query:
        pattern = f"%{_escape_like(query)}%"
        conditions.append(Dataset.search_text.ilike(pattern, escape="\\"))
    if conditions:
        statement = statement.where(and_(*conditions))
    return statement


async def search_datasets(
    session: AsyncSession,
    filters: DatasetFilters,
    *,
    page: int = 1,
    page_size: int = 20,
) -> DatasetPage:
    base = _apply_filters(select(Dataset), filters)
    total = await session.scalar(
        select(func.count()).select_from(base.with_only_columns(Dataset.id).subquery())
    )
    statement = (
        base.options(
            joinedload(Dataset.source),
            joinedload(Dataset.organization),
            selectinload(Dataset.resources),
        )
        .order_by(Dataset.last_source_update.desc().nulls_last(), Dataset.title.asc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    result = await session.execute(statement)
    items = list(result.scalars().all())
    return DatasetPage(
        items=cast("list[Dataset]", items),
        total=int(total or 0),
        page=page,
        page_size=page_size,
    )


@dataclass(frozen=True)
class Facet:
    value: str
    count: int


@dataclass(frozen=True)
class CatalogueFacets:
    topics: list[Facet]
    formats: list[Facet]
    organizations: list[Facet]


async def catalogue_facets(session: AsyncSession, *, limit: int = 50) -> CatalogueFacets:
    """Counts used by the explorer filters; always derived from stored data."""
    topics = await session.execute(
        select(Dataset.topic, func.count())
        .where(Dataset.topic.is_not(None), Dataset.is_available.is_(True))
        .group_by(Dataset.topic)
        .order_by(func.count().desc(), Dataset.topic.asc())
        .limit(limit)
    )
    formats = await session.execute(
        select(DatasetResource.format, func.count(func.distinct(DatasetResource.dataset_id)))
        .where(DatasetResource.format.is_not(None))
        .group_by(DatasetResource.format)
        .order_by(func.count().desc(), DatasetResource.format.asc())
        .limit(limit)
    )
    organizations = await session.execute(
        select(Organization.name, func.count(Dataset.id))
        .join(Dataset, Dataset.organization_id == Organization.id)
        .where(Dataset.is_available.is_(True))
        .group_by(Organization.name)
        .order_by(func.count(Dataset.id).desc(), Organization.name.asc())
        .limit(limit)
    )
    return CatalogueFacets(
        topics=[Facet(value=str(value), count=int(count)) for value, count in topics if value],
        formats=[Facet(value=str(value), count=int(count)) for value, count in formats if value],
        organizations=[
            Facet(value=str(value), count=int(count)) for value, count in organizations if value
        ],
    )


__all__ = [
    "CatalogueFacets",
    "DatasetFilters",
    "DatasetPage",
    "Facet",
    "catalogue_facets",
    "normalize_query",
    "search_datasets",
]
