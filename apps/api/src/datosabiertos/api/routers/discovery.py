"""Bounded discovery endpoints for catalogue filter dimensions."""

from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Query
from sqlalchemy import func, select

from ...core.errors import NotFoundError
from ...modules.catalog.models import Dataset
from ...modules.jurisdictions.models import Jurisdiction
from ...modules.organizations.models import Organization
from ..deps import PaginationDep, SessionDep
from ..schemas.catalog import JurisdictionOut, OrganizationOut, TopicOut
from ..schemas.common import Page

router = APIRouter(tags=["discovery"])


def _pages(total: int, page_size: int) -> int:
    return (total + page_size - 1) // page_size if total else 0


def _organization_out(row: tuple[Organization, int, int]) -> OrganizationOut:
    organization, dataset_count, available_count = row
    return OrganizationOut(
        id=organization.id,
        name=organization.name,
        acronym=organization.acronym,
        official_url=organization.official_url,
        jurisdiction_id=organization.jurisdiction_id,
        dataset_count=dataset_count,
        available_dataset_count=available_count,
    )


@router.get("/organizations", response_model=Page[OrganizationOut])
async def read_organizations(
    session: SessionDep,
    pagination: PaginationDep,
    q: Annotated[str | None, Query(max_length=200)] = None,
) -> Page[OrganizationOut]:
    """List organizations without downloading the complete dataset catalogue."""
    dataset_count = func.count(Dataset.id).label("dataset_count")
    available_count = (
        func.count(Dataset.id).filter(Dataset.is_available.is_(True)).label("available_count")
    )
    base = (
        select(Organization, dataset_count, available_count)
        .outerjoin(Dataset, Dataset.organization_id == Organization.id)
        .group_by(Organization.id)
    )
    count_statement = select(func.count()).select_from(Organization)
    if q:
        pattern = f"%{q.strip()}%"
        base = base.where(Organization.name.ilike(pattern))
        count_statement = count_statement.where(Organization.name.ilike(pattern))
    total = int(await session.scalar(count_statement) or 0)
    rows = (
        await session.execute(
            base.order_by(Organization.name).offset(pagination.offset).limit(pagination.page_size)
        )
    ).all()
    return Page[OrganizationOut](
        items=[_organization_out(row) for row in rows],
        total=total,
        page=pagination.page,
        page_size=pagination.page_size,
        pages=_pages(total, pagination.page_size),
    )


@router.get("/organizations/{organization_id}", response_model=OrganizationOut)
async def read_organization(organization_id: uuid.UUID, session: SessionDep) -> OrganizationOut:
    dataset_count = func.count(Dataset.id).label("dataset_count")
    available_count = (
        func.count(Dataset.id).filter(Dataset.is_available.is_(True)).label("available_count")
    )
    row = (
        await session.execute(
            select(Organization, dataset_count, available_count)
            .outerjoin(Dataset, Dataset.organization_id == Organization.id)
            .where(Organization.id == organization_id)
            .group_by(Organization.id)
        )
    ).one_or_none()
    if row is None:
        raise NotFoundError("Organismo no encontrado.")
    return _organization_out(row)


@router.get("/jurisdictions", response_model=Page[JurisdictionOut])
async def read_jurisdictions(
    session: SessionDep,
    pagination: PaginationDep,
    type: Annotated[str | None, Query(max_length=32)] = None,
) -> Page[JurisdictionOut]:
    organization_count = func.count(func.distinct(Organization.id)).label("organization_count")
    dataset_count = func.count(func.distinct(Dataset.id)).label("dataset_count")
    base = (
        select(Jurisdiction, organization_count, dataset_count)
        .outerjoin(Organization, Organization.jurisdiction_id == Jurisdiction.id)
        .outerjoin(Dataset, Dataset.organization_id == Organization.id)
        .group_by(Jurisdiction.id)
    )
    count_statement = select(func.count()).select_from(Jurisdiction)
    if type:
        base = base.where(Jurisdiction.type == type)
        count_statement = count_statement.where(Jurisdiction.type == type)
    total = int(await session.scalar(count_statement) or 0)
    rows = (
        await session.execute(
            base.order_by(Jurisdiction.type, Jurisdiction.name)
            .offset(pagination.offset)
            .limit(pagination.page_size)
        )
    ).all()
    return Page[JurisdictionOut](
        items=[
            JurisdictionOut(
                id=jurisdiction.id,
                name=jurisdiction.name,
                type=jurisdiction.type.value,
                parent_id=jurisdiction.parent_id,
                official_code=jurisdiction.official_code,
                organization_count=organizations,
                dataset_count=datasets,
            )
            for jurisdiction, organizations, datasets in rows
        ],
        total=total,
        page=pagination.page,
        page_size=pagination.page_size,
        pages=_pages(total, pagination.page_size),
    )


@router.get("/topics", response_model=Page[TopicOut])
async def read_topics(session: SessionDep, pagination: PaginationDep) -> Page[TopicOut]:
    base = (
        select(Dataset.topic, func.count(Dataset.id))
        .where(Dataset.topic.is_not(None), Dataset.is_available.is_(True))
        .group_by(Dataset.topic)
    )
    total = int(
        await session.scalar(
            select(func.count(func.distinct(Dataset.topic))).where(
                Dataset.topic.is_not(None), Dataset.is_available.is_(True)
            )
        )
        or 0
    )
    rows = (
        await session.execute(
            base.order_by(Dataset.topic).offset(pagination.offset).limit(pagination.page_size)
        )
    ).all()
    return Page[TopicOut](
        items=[TopicOut(name=topic, dataset_count=count) for topic, count in rows if topic],
        total=total,
        page=pagination.page,
        page_size=pagination.page_size,
        pages=_pages(total, pagination.page_size),
    )


__all__ = ["router"]
