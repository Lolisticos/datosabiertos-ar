from __future__ import annotations

from datetime import UTC, date, datetime
from decimal import Decimal

import pytest
from datosabiertos_connectors import SeriesFetchResult, SeriesMetadata, SeriesObservation
from httpx import AsyncClient
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from datosabiertos.modules.catalog.models import Dataset, DatasetResource
from datosabiertos.modules.indicators.models import Indicator, IndicatorObservation
from datosabiertos.modules.indicators.service import StatisticalSeriesSyncService
from datosabiertos.modules.ingestion.models import (
    IngestionRun,
    IngestionRunStatus,
    ResourceSnapshot,
)
from datosabiertos.modules.ingestion.storage import InMemoryStorage
from datosabiertos.modules.provenance.models import TransformationRun
from datosabiertos.modules.sources.models import DataSource, SourceType


class FakeSeriesConnector:
    def __init__(self, result: SeriesFetchResult) -> None:
        self.result = result

    async def fetch(self, series_id: str, *, limit: int = 5_000) -> SeriesFetchResult:
        assert series_id == "143.3_NO_PR_2004_A_21"
        assert limit == 5_000
        return self.result


class FailingSeriesConnector:
    async def fetch(self, series_id: str, *, limit: int = 5_000) -> SeriesFetchResult:
        raise RuntimeError("official API unavailable")


def official_result() -> SeriesFetchResult:
    return SeriesFetchResult(
        metadata=SeriesMetadata(
            series_id="143.3_NO_PR_2004_A_21",
            description="EMAE. Base 2004",
            units="Índice 2004=100",
            frequency="month",
            dataset_title="Estimador Mensual de Actividad Económica (EMAE). Base 2004",
            dataset_description="Serie original",
            source="Instituto Nacional de Estadística y Censos (INDEC)",
            distribution_title="EMAE mensual",
            download_url="https://infra.datos.gob.ar/emae.csv",
        ),
        observations=(
            SeriesObservation(date(2025, 1, 1), Decimal("146.49668268147974")),
            SeriesObservation(date(2025, 2, 1), None),
            SeriesObservation(date(2025, 3, 1), Decimal("150.61008581723874")),
        ),
        raw=b'{"official":"fixture"}',
        fetched_at=datetime(2026, 11, 23, tzinfo=UTC),
        response_url="https://apis.datos.gob.ar/series/api/series/?ids=143.3_NO_PR_2004_A_21",
    )


async def configured_indicator(db: AsyncSession) -> Indicator:
    source = DataSource(
        slug="series-test",
        name="Series test",
        base_url="https://apis.datos.gob.ar",
        source_type=SourceType.REST_API,
    )
    db.add(source)
    await db.flush()
    dataset = Dataset(
        source_id=source.id,
        external_id="143",
        title="EMAE",
        topic="Economía",
        metadata_hash="a" * 64,
        is_available=True,
    )
    db.add(dataset)
    await db.flush()
    resource = DatasetResource(
        dataset_id=dataset.id,
        external_id="143.3_NO_PR_2004_A_21",
        name="EMAE original",
        format="JSON",
        url="https://apis.datos.gob.ar/series/api/series/?ids=143.3_NO_PR_2004_A_21",
        is_available=True,
    )
    indicator = Indicator(
        code="emae-original-2004",
        name="EMAE",
        unit="Índice 2004=100",
        frequency="monthly",
        source_series_id="143.3_NO_PR_2004_A_21",
        source_id=source.id,
        topic="Economía",
    )
    db.add_all([resource, indicator])
    await db.commit()
    return indicator


async def test_statistical_sync_preserves_raw_and_publishes_decimal_observations(
    db: AsyncSession,
) -> None:
    indicator = await configured_indicator(db)
    storage = InMemoryStorage()
    service = StatisticalSeriesSyncService(
        session=db,
        connector=FakeSeriesConnector(official_result()),
        storage=storage,
        indicator_code=indicator.code,
        triggered_by="pytest",
    )

    first = await service.run()
    second = await service.run()

    assert first.status is IngestionRunStatus.SUCCEEDED
    assert second.status is IngestionRunStatus.SUCCEEDED
    assert first.snapshot_id == second.snapshot_id
    assert await db.scalar(select(func.count()).select_from(ResourceSnapshot)) == 1
    assert await db.scalar(select(func.count()).select_from(TransformationRun)) == 1
    observations = list(
        await db.scalars(select(IndicatorObservation).order_by(IndicatorObservation.period_start))
    )
    assert len(observations) == 3
    assert observations[0].value == Decimal("146.496682681480")
    assert observations[1].value is None
    assert observations[1].dimensions["seasonal_adjustment"] == "original"
    assert observations[0].snapshot_id == first.snapshot_id
    assert observations[0].transformation_run_id is not None
    assert len(storage.objects) == 1


async def test_statistical_sync_records_fetch_failure_without_partial_data(
    db: AsyncSession,
) -> None:
    indicator = await configured_indicator(db)
    storage = InMemoryStorage()
    service = StatisticalSeriesSyncService(
        session=db,
        connector=FailingSeriesConnector(),
        storage=storage,
        indicator_code=indicator.code,
    )

    with pytest.raises(RuntimeError, match="official API unavailable"):
        await service.run()

    run = await db.scalar(select(IngestionRun))
    assert run is not None
    assert run.status is IngestionRunStatus.FAILED
    assert run.error_summary and "official API unavailable" in run.error_summary
    assert await db.scalar(select(func.count()).select_from(IndicatorObservation)) == 0
    assert await db.scalar(select(func.count()).select_from(ResourceSnapshot)) == 0
    assert storage.objects == {}


async def test_indicator_api_exposes_metadata_observations_coverage_and_csv(
    db: AsyncSession, client: AsyncClient
) -> None:
    indicator = await configured_indicator(db)
    await StatisticalSeriesSyncService(
        session=db,
        connector=FakeSeriesConnector(official_result()),
        storage=InMemoryStorage(),
        indicator_code=indicator.code,
    ).run()

    listing = await client.get("/api/v1/indicators")
    assert listing.status_code == 200
    assert listing.json()["items"][0]["code"] == indicator.code
    detail = await client.get(f"/api/v1/indicators/{indicator.code}")
    assert detail.status_code == 200
    assert detail.json()["source_series_id"] == "143.3_NO_PR_2004_A_21"
    assert detail.json()["transformation_version"] == "1.0.0"

    observations = await client.get(
        f"/api/v1/indicators/{indicator.code}/observations", params={"page_size": 100}
    )
    assert observations.status_code == 200
    body = observations.json()
    assert body["total"] == 3
    assert body["items"][0]["value"] == "146.496682681480"
    assert body["items"][1]["value"] is None

    incompatible = await client.get(
        f"/api/v1/indicators/{indicator.code}/observations",
        params={"frequency": "yearly"},
    )
    assert incompatible.status_code == 400
    coverage = await client.get(f"/api/v1/indicators/{indicator.code}/coverage")
    assert coverage.json()["missing_value_count"] == 1
    assert coverage.json()["period"] == {"start": "2025-01-01", "end": "2025-03-01"}

    csv_response = await client.get(f"/api/v1/indicators/{indicator.code}/observations.csv")
    assert csv_response.status_code == 200
    assert csv_response.headers["content-disposition"].endswith('filename="emae-original-2004.csv"')
    assert "2025-02-01,,Índice 2004=100,original" in csv_response.text
