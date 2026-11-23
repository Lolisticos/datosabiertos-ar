"""Test fixtures for the API and ingestion suites.

Integration tests require the dedicated PostgreSQL/PostGIS database created by
``scripts/dev-bootstrap.sh`` (``DATOSABIERTOS_TEST_DATABASE_URL``). The schema is
brought to Alembic ``head`` once per session and every test starts from empty
tables, so assertions never depend on the developer's real catalogue.
"""

from __future__ import annotations

import os
from collections.abc import AsyncIterator, Iterable
from datetime import UTC, date, datetime, timedelta
from pathlib import Path
from typing import Any

import pytest

TEST_DATABASE_URL = os.environ.get(
    "DATOSABIERTOS_TEST_DATABASE_URL",
    "postgresql+psycopg://datosabiertos:datosabiertos@localhost:55437/datosabiertos_test",
)
# Must be set before any ``datosabiertos`` module reads the settings.
os.environ["DATOSABIERTOS_DATABASE_URL"] = TEST_DATABASE_URL
os.environ["DATOSABIERTOS_ENVIRONMENT"] = "test"
os.environ["DATOSABIERTOS_LOG_LEVEL"] = "WARNING"

from alembic import command  # noqa: E402
from alembic.config import Config  # noqa: E402
from httpx import ASGITransport, AsyncClient  # noqa: E402
from sqlalchemy import text  # noqa: E402
from sqlalchemy.ext.asyncio import (  # noqa: E402
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from datosabiertos.api.deps import get_settings  # noqa: E402
from datosabiertos.core.config import Settings  # noqa: E402
from datosabiertos.core.text import build_search_text  # noqa: E402
from datosabiertos.db.base import Base  # noqa: E402
from datosabiertos.db.session import get_session  # noqa: E402
from datosabiertos.main import create_app  # noqa: E402
from datosabiertos.modules.catalog.models import Dataset, DatasetResource  # noqa: E402
from datosabiertos.modules.history.models import ChangeType, DataChange  # noqa: E402
from datosabiertos.modules.ingestion.models import (  # noqa: E402
    IngestionRun,
    IngestionRunStatus,
    IngestionRunType,
    ResourceSnapshot,
    SnapshotKind,
)
from datosabiertos.modules.organizations.models import Organization  # noqa: E402
from datosabiertos.modules.quality.models import (  # noqa: E402
    DataQualityCheck,
    QualityStatus,
)
from datosabiertos.modules.sources.models import DataSource, SourceType  # noqa: E402

API_DIR = Path(__file__).resolve().parents[1]


@pytest.fixture(scope="session", autouse=True)
def migrated_database() -> None:
    """Bring the test database to the latest migration exactly once."""
    config = Config(str(API_DIR / "alembic.ini"))
    config.set_main_option("script_location", str(API_DIR / "alembic"))
    config.set_main_option("sqlalchemy.url", TEST_DATABASE_URL)
    command.upgrade(config, "head")


@pytest.fixture(scope="session")
def settings(tmp_path_factory: pytest.TempPathFactory) -> Settings:
    storage_root = tmp_path_factory.mktemp("storage")
    return Settings(
        environment="test",
        log_level="WARNING",
        database_url=TEST_DATABASE_URL,
        storage_root=storage_root,
    )


@pytest.fixture(scope="session")
async def engine() -> AsyncIterator[AsyncEngine]:
    engine = create_async_engine(TEST_DATABASE_URL, pool_pre_ping=True)
    try:
        yield engine
    finally:
        await engine.dispose()


@pytest.fixture(scope="session")
def session_factory(engine: AsyncEngine) -> async_sessionmaker[AsyncSession]:
    return async_sessionmaker(engine, expire_on_commit=False, autoflush=False)


async def _truncate_all(engine: AsyncEngine) -> None:
    tables = ", ".join(table.name for table in Base.metadata.sorted_tables)
    async with engine.begin() as connection:
        await connection.execute(text(f"TRUNCATE TABLE {tables} RESTART IDENTITY CASCADE"))


@pytest.fixture
async def db(
    engine: AsyncEngine, session_factory: async_sessionmaker[AsyncSession]
) -> AsyncIterator[AsyncSession]:
    await _truncate_all(engine)
    async with session_factory() as session:
        yield session
        await session.rollback()


@pytest.fixture
async def client(
    settings: Settings, session_factory: async_sessionmaker[AsyncSession]
) -> AsyncIterator[AsyncClient]:
    app = create_app(settings)

    async def override_session() -> AsyncIterator[AsyncSession]:
        async with session_factory() as session:
            try:
                yield session
            except Exception:
                await session.rollback()
                raise

    app.dependency_overrides[get_session] = override_session
    app.dependency_overrides[get_settings] = lambda: settings
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as http:
        yield http


def build_source(**overrides: Any) -> DataSource:
    values: dict[str, Any] = {
        "slug": "test-source",
        "name": "Catálogo de prueba",
        "base_url": "https://example.test",
        "source_type": SourceType.CKAN,
    }
    values.update(overrides)
    return DataSource(**values)


def build_dataset(
    *,
    source: DataSource,
    organization: Organization | None,
    external_id: str,
    title: str,
    **overrides: Any,
) -> Dataset:
    now = datetime.now(UTC)
    values: dict[str, Any] = {
        "source_id": source.id,
        "organization_id": organization.id if organization else None,
        "external_id": external_id,
        "title": title,
        "description": f"Descripción de {title}",
        "topic": "Educación",
        "license": "Creative Commons Attribution 4.0",
        "coverage_start": date(2020, 1, 1),
        "coverage_end": date(2024, 12, 31),
        "last_source_update": now - timedelta(days=1),
        "last_successful_sync": now,
        "search_text": build_search_text(
            title, f"Descripción de {title}", organization.name if organization else None
        ),
        "metadata_hash": "0" * 64,
        "is_available": True,
        "raw_metadata": {"name": external_id, "title": title},
    }
    values.update(overrides)
    return Dataset(**values)


def build_resource(*, dataset: Dataset, external_id: str, **overrides: Any) -> DatasetResource:
    values: dict[str, Any] = {
        "dataset_id": dataset.id,
        "external_id": external_id,
        "name": f"Recurso {external_id}",
        "format": "CSV",
        "url": f"https://example.test/{external_id}.csv",
        "is_available": True,
    }
    values.update(overrides)
    return DatasetResource(**values)


def build_run(
    *,
    source: DataSource,
    status: IngestionRunStatus = IngestionRunStatus.SUCCEEDED,
    **overrides: Any,
) -> IngestionRun:
    now = datetime.now(UTC)
    values: dict[str, Any] = {
        "source_id": source.id,
        "run_type": IngestionRunType.CATALOG_DISCOVERY,
        "status": status,
        "triggered_by": "pytest",
        "transformation_version": "catalog-normalizer-test",
        "started_at": now - timedelta(seconds=5),
        "finished_at": now,
        "records_read": 2,
        "records_accepted": 2,
        "records_rejected": 0,
    }
    values.update(overrides)
    return IngestionRun(**values)


def build_snapshot(
    *, source: DataSource, content_hash: str, run: IngestionRun | None = None
) -> ResourceSnapshot:
    return ResourceSnapshot(
        kind=SnapshotKind.CATALOG_PAYLOAD,
        source_id=source.id,
        ingestion_run_id=run.id if run else None,
        content_hash=content_hash,
        storage_key=f"raw/{content_hash}.json",
        media_type="application/json",
        file_size=128,
        fetched_at=datetime.now(UTC),
    )


@pytest.fixture
async def seeded_catalog(db: AsyncSession) -> dict[str, Any]:
    """Deterministic catalogue: one source, two datasets, one run and checks."""
    organization = Organization(name="Ministerio de Educación")
    db.add(organization)
    await db.flush()

    source = build_source()
    db.add(source)
    await db.flush()

    run = build_run(source=source)
    db.add(run)
    await db.flush()

    first = build_dataset(
        source=source,
        organization=organization,
        external_id="dataset-educacion",
        title="Educación pública por provincia",
        raw_metadata={"name": "educacion-publica", "title": "Educación pública por provincia"},
    )
    second = build_dataset(
        source=source,
        organization=organization,
        external_id="dataset-presupuesto",
        title="Presupuesto educativo",
        topic="Economía y Finanzas",
        is_available=False,
        search_text=build_search_text(
            "Presupuesto educativo",
            "Descripción de Presupuesto educativo",
            "Ministerio de Educación",
        ),
    )
    db.add_all([first, second])
    await db.flush()

    resource = build_resource(dataset=first, external_id="recurso-csv")
    db.add(resource)
    await db.flush()

    snapshot = build_snapshot(source=source, content_hash="a" * 64, run=run)
    db.add(snapshot)
    await db.flush()

    db.add_all(
        [
            DataQualityCheck(
                ingestion_run_id=run.id,
                check_type="datasets_persisted",
                status=QualityStatus.PASSED,
                details={"read": 2, "created": 2},
            ),
            DataChange(
                ingestion_run_id=run.id,
                dataset_id=first.id,
                change_type=ChangeType.DATASET_ADDED,
                change_summary={"title": first.title},
            ),
            DataChange(
                ingestion_run_id=run.id,
                dataset_id=first.id,
                change_type=ChangeType.RESOURCE_ADDED,
                resource_id=resource.id,
                change_summary={"format": "CSV"},
            ),
        ]
    )
    await db.commit()

    return {
        "organization_id": organization.id,
        "source_id": source.id,
        "source_slug": source.slug,
        "run_id": run.id,
        "dataset_id": first.id,
        "dataset_title": first.title,
        "unavailable_dataset_id": second.id,
        "resource_id": resource.id,
    }


def as_rows(items: Iterable[dict[str, Any]]) -> list[dict[str, Any]]:
    return list(items)
