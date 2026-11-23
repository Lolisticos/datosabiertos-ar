"""Published indicator metadata, observations, coverage and downloads."""

from __future__ import annotations

import csv
import io
import re
import uuid
from datetime import date
from typing import Annotated

from fastapi import APIRouter, Query
from fastapi.responses import Response
from sqlalchemy import Select, func, select
from sqlalchemy.orm import joinedload

from ...core.errors import ApiError, NotFoundError
from ...modules.indicators.models import Indicator, IndicatorObservation, ObservationReviewStatus
from ...modules.ingestion.models import ResourceSnapshot
from ...modules.provenance.models import TransformationRun
from ..deps import PaginationDep, SessionDep
from ..schemas.common import DateRange, Page, ReferencedSource
from ..schemas.indicators import (
    IndicatorCoverageOut,
    IndicatorDetailOut,
    IndicatorSummaryOut,
    ObservationOut,
)

router = APIRouter(prefix="/indicators", tags=["indicators"])


async def _indicator_or_404(code: str, session: SessionDep) -> Indicator:
    indicator = await session.scalar(
        select(Indicator).where(Indicator.code == code).options(joinedload(Indicator.source))
    )
    if indicator is None:
        raise NotFoundError("Indicador no encontrado.")
    return indicator


def _source(indicator: Indicator) -> ReferencedSource | None:
    source = indicator.source
    if source is None:
        return None
    return ReferencedSource(
        id=source.id,
        slug=source.slug,
        name=source.name,
        source_type=source.source_type.value,
        base_url=source.base_url,
    )


async def _summary(indicator: Indicator, session: SessionDep) -> IndicatorSummaryOut:
    latest = (
        await session.execute(
            select(IndicatorObservation.period_start, IndicatorObservation.value)
            .where(
                IndicatorObservation.indicator_id == indicator.id,
                IndicatorObservation.review_status == ObservationReviewStatus.PUBLISHED,
                IndicatorObservation.value.is_not(None),
            )
            .order_by(IndicatorObservation.period_start.desc())
            .limit(1)
        )
    ).one_or_none()
    last_updated = await session.scalar(
        select(func.max(ResourceSnapshot.fetched_at))
        .join(IndicatorObservation, IndicatorObservation.snapshot_id == ResourceSnapshot.id)
        .where(IndicatorObservation.indicator_id == indicator.id)
    )
    return IndicatorSummaryOut(
        code=indicator.code,
        name=indicator.name,
        description=indicator.description,
        unit=indicator.unit,
        frequency=indicator.frequency,
        topic=indicator.topic,
        source=_source(indicator),
        latest_period=latest[0] if latest else None,
        latest_value=latest[1] if latest else None,
        last_updated_at=last_updated,
    )


@router.get("", response_model=Page[IndicatorSummaryOut])
async def read_indicators(
    session: SessionDep,
    pagination: PaginationDep,
    topic: Annotated[str | None, Query(max_length=128)] = None,
) -> Page[IndicatorSummaryOut]:
    statement = select(Indicator).options(joinedload(Indicator.source))
    count_statement = select(func.count()).select_from(Indicator)
    if topic:
        statement = statement.where(Indicator.topic == topic)
        count_statement = count_statement.where(Indicator.topic == topic)
    total = int(await session.scalar(count_statement) or 0)
    indicators = list(
        await session.scalars(
            statement.order_by(Indicator.name).offset(pagination.offset).limit(pagination.page_size)
        )
    )
    return Page[IndicatorSummaryOut](
        items=[await _summary(indicator, session) for indicator in indicators],
        total=total,
        page=pagination.page,
        page_size=pagination.page_size,
        pages=(total + pagination.page_size - 1) // pagination.page_size if total else 0,
    )


async def _detail(indicator: Indicator, session: SessionDep) -> IndicatorDetailOut:
    summary = await _summary(indicator, session)
    provenance = (
        await session.execute(
            select(ResourceSnapshot, TransformationRun)
            .join(TransformationRun, TransformationRun.snapshot_id == ResourceSnapshot.id)
            .join(IndicatorObservation, IndicatorObservation.snapshot_id == ResourceSnapshot.id)
            .where(IndicatorObservation.indicator_id == indicator.id)
            .order_by(ResourceSnapshot.fetched_at.desc())
            .limit(1)
        )
    ).one_or_none()
    snapshot, transformation = provenance if provenance else (None, None)
    return IndicatorDetailOut(
        **summary.model_dump(),
        methodology=indicator.methodology,
        source_series_id=indicator.source_series_id,
        source_url=indicator.source_url,
        methodology_url=indicator.methodology_url,
        license=indicator.license,
        transformation_name=transformation.name if transformation else None,
        transformation_version=transformation.version if transformation else None,
        snapshot_id=snapshot.id if snapshot else None,
        raw_content_hash=snapshot.content_hash if snapshot else None,
        normalized_hash=snapshot.normalized_hash if snapshot else None,
        downloaded_at=snapshot.fetched_at if snapshot else None,
    )


@router.get("/{code}", response_model=IndicatorDetailOut)
async def read_indicator(code: str, session: SessionDep) -> IndicatorDetailOut:
    return await _detail(await _indicator_or_404(code, session), session)


@router.get("/{code}/metadata", response_model=IndicatorDetailOut)
async def read_indicator_metadata(code: str, session: SessionDep) -> IndicatorDetailOut:
    return await _detail(await _indicator_or_404(code, session), session)


def _observation_statement(
    indicator: Indicator,
    *,
    start_period: date | None,
    end_period: date | None,
    jurisdiction_id: uuid.UUID | None,
) -> Select[IndicatorObservation]:
    statement = select(IndicatorObservation).where(
        IndicatorObservation.indicator_id == indicator.id,
        IndicatorObservation.review_status == ObservationReviewStatus.PUBLISHED,
    )
    if start_period:
        statement = statement.where(IndicatorObservation.period_start >= start_period)
    if end_period:
        statement = statement.where(IndicatorObservation.period_start <= end_period)
    if jurisdiction_id:
        statement = statement.where(IndicatorObservation.jurisdiction_id == jurisdiction_id)
    return statement


def _validate_frequency(indicator: Indicator, frequency: str | None) -> None:
    if frequency and frequency != indicator.frequency:
        raise ApiError(
            "La frecuencia solicitada no es compatible con este indicador.",
            details={"available_frequency": indicator.frequency},
        )


def _observation_out(observation: IndicatorObservation) -> ObservationOut:
    return ObservationOut(
        id=observation.id,
        period_start=observation.period_start,
        period_end=observation.period_end,
        value=observation.value,
        unit=observation.unit,
        dimensions=observation.dimensions,
        jurisdiction_id=observation.jurisdiction_id,
        snapshot_id=observation.snapshot_id,
        published_at=observation.published_at,
    )


@router.get("/{code}/observations", response_model=Page[ObservationOut])
async def read_indicator_observations(
    code: str,
    session: SessionDep,
    pagination: PaginationDep,
    start_period: date | None = None,
    end_period: date | None = None,
    jurisdiction_id: uuid.UUID | None = None,
    frequency: Annotated[str | None, Query(max_length=32)] = None,
) -> Page[ObservationOut]:
    indicator = await _indicator_or_404(code, session)
    _validate_frequency(indicator, frequency)
    statement = _observation_statement(
        indicator,
        start_period=start_period,
        end_period=end_period,
        jurisdiction_id=jurisdiction_id,
    )
    total = int(await session.scalar(select(func.count()).select_from(statement.subquery())) or 0)
    observations = list(
        await session.scalars(
            statement.order_by(IndicatorObservation.period_start)
            .offset(pagination.offset)
            .limit(pagination.page_size)
        )
    )
    return Page[ObservationOut](
        items=[_observation_out(item) for item in observations],
        total=total,
        page=pagination.page,
        page_size=pagination.page_size,
        pages=(total + pagination.page_size - 1) // pagination.page_size if total else 0,
    )


@router.get("/{code}/coverage", response_model=IndicatorCoverageOut)
async def read_indicator_coverage(code: str, session: SessionDep) -> IndicatorCoverageOut:
    indicator = await _indicator_or_404(code, session)
    row = (
        await session.execute(
            select(
                func.min(IndicatorObservation.period_start),
                func.max(IndicatorObservation.period_start),
                func.count(IndicatorObservation.id),
                func.count(IndicatorObservation.id).filter(IndicatorObservation.value.is_(None)),
                func.count(func.distinct(IndicatorObservation.jurisdiction_id)),
            ).where(
                IndicatorObservation.indicator_id == indicator.id,
                IndicatorObservation.review_status == ObservationReviewStatus.PUBLISHED,
            )
        )
    ).one()
    return IndicatorCoverageOut(
        code=indicator.code,
        period=DateRange(start=row[0], end=row[1]),
        observation_count=row[2],
        missing_value_count=row[3],
        jurisdiction_count=row[4],
        frequency=indicator.frequency,
    )


@router.get("/{code}/observations.csv", response_class=Response)
async def download_indicator_observations(code: str, session: SessionDep) -> Response:
    indicator = await _indicator_or_404(code, session)
    observations = list(
        await session.scalars(
            _observation_statement(
                indicator, start_period=None, end_period=None, jurisdiction_id=None
            ).order_by(IndicatorObservation.period_start)
        )
    )
    output = io.StringIO(newline="")
    writer = csv.writer(output)
    writer.writerow(["indicator_code", "period", "value", "unit", "seasonal_adjustment"])
    for observation in observations:
        writer.writerow(
            [
                indicator.code,
                observation.period_start.isoformat(),
                "" if observation.value is None else str(observation.value),
                observation.unit,
                observation.dimensions.get("seasonal_adjustment", ""),
            ]
        )
    safe_code = re.sub(r"[^a-z0-9-]", "-", indicator.code.lower())[:80]
    return Response(
        content=output.getvalue().encode("utf-8-sig"),
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{safe_code}.csv"'},
    )


__all__ = ["router"]
