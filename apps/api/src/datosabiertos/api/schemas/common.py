"""Shared HTTP contracts."""

from __future__ import annotations

from datetime import date, datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class Page[T](BaseModel):
    items: list[T]
    total: int = Field(ge=0)
    page: int = Field(ge=1)
    page_size: int = Field(ge=1)
    pages: int = Field(ge=0)


class ReferencedSource(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    slug: str
    name: str
    source_type: str
    base_url: str


class ReferencedOrganization(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    acronym: str | None = None
    official_url: str | None = None


class ReferencedDataset(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    title: str


class ReferencedResource(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    format: str | None = None


class Facet(BaseModel):
    value: str
    count: int = Field(ge=0)


class Facets(BaseModel):
    topics: list[Facet]
    formats: list[Facet]
    organizations: list[Facet]


class HealthStatus(BaseModel):
    status: str
    version: str
    environment: str
    timestamp: datetime
    database: str | None = None
    details: dict[str, str] | None = None


class ApiInfo(BaseModel):
    name: str
    version: str
    environment: str
    docs_url: str
    openapi_url: str
    coverage_note: str


class DateRange(BaseModel):
    start: date | None = None
    end: date | None = None


__all__ = [
    "ApiInfo",
    "DateRange",
    "Facet",
    "Facets",
    "HealthStatus",
    "Page",
    "ReferencedDataset",
    "ReferencedOrganization",
    "ReferencedResource",
    "ReferencedSource",
]
