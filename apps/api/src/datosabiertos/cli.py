"""Operator command line interface.

Only configured sources can be ingested: the CLI looks the source up by slug in
the database, builds the matching connector from the stored configuration and
never accepts an arbitrary URL.
"""

from __future__ import annotations

import asyncio
import json
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Annotated

import typer
from datosabiertos_connectors import CkanConnector, HttpPolicy, SourceConnector
from sqlalchemy import select, update

from .core.config import Settings, get_settings
from .core.logging import configure_logging, get_logger
from .db.session import dispose_engine, session_scope
from .modules.ingestion.models import IngestionRun, IngestionRunStatus
from .modules.ingestion.service import CatalogSyncService
from .modules.ingestion.storage import LocalFileSystemStorage
from .modules.sources.models import DataSource, SourceType

app = typer.Typer(help="DatosAbiertos AR operator CLI", no_args_is_help=True)
ingest_app = typer.Typer(help="Ingestion operations", no_args_is_help=True)
app.add_typer(ingest_app, name="ingest")

logger = get_logger(__name__)


def _settings() -> Settings:
    settings = get_settings()
    configure_logging(settings.log_level, json_logs=False)
    return settings


def _build_connector(source: DataSource, settings: Settings) -> SourceConnector:
    if source.source_type is not SourceType.CKAN:
        raise typer.BadParameter(
            f"source type {source.source_type.value!r} has no connector implementation yet"
        )
    return CkanConnector(
        base_url=source.base_url,
        user_agent=settings.ingestion_user_agent,
        policy=HttpPolicy(
            timeout_seconds=settings.ingestion_request_timeout_seconds,
            max_bytes=settings.ingestion_max_download_bytes,
            requests_per_second=settings.ingestion_requests_per_second,
            retry_attempts=settings.ingestion_retry_attempts,
        ),
    )


async def _reap_stale_runs(session: object) -> int:
    """Mark abandoned runs as failed.

    A run left in ``running`` means the process died (OOM, Ctrl-C, deploy); the
    history must not keep it as active forever.
    """
    from sqlalchemy.ext.asyncio import AsyncSession

    assert isinstance(session, AsyncSession)
    threshold = datetime.now(UTC) - timedelta(minutes=60)
    result = await session.execute(
        update(IngestionRun)
        .where(
            IngestionRun.status == IngestionRunStatus.RUNNING, IngestionRun.started_at < threshold
        )
        .values(
            status=IngestionRunStatus.FAILED,
            finished_at=datetime.now(UTC),
            error_summary="interrupted: run abandoned without finishing (stale run reaper)",
        )
    )
    return int(getattr(result, "rowcount", 0) or 0)


async def _load_source(slug: str) -> DataSource:
    async with session_scope() as session:
        source = await session.scalar(select(DataSource).where(DataSource.slug == slug))
        if source is None:
            raise typer.BadParameter(f"unknown source {slug!r}; run `datosabiertos ingest sources`")
        if not source.is_active:
            raise typer.BadParameter(f"source {slug!r} is disabled")
        session.expunge_all()
        return source


@ingest_app.command("sources")
def list_sources() -> None:
    """List the configured sources and whether a connector is available."""

    async def _run() -> list[dict[str, object]]:
        _settings()
        async with session_scope() as session:
            rows = await session.scalars(select(DataSource).order_by(DataSource.slug))
            return [
                {
                    "slug": row.slug,
                    "name": row.name,
                    "type": row.source_type.value,
                    "base_url": row.base_url,
                    "active": row.is_active,
                }
                for row in rows
            ]

    for item in asyncio.run(_run()):
        typer.echo(json.dumps(item, ensure_ascii=False))


@ingest_app.command("sync")
def sync(
    source: Annotated[str, typer.Option(help="Configured source slug")] = "datos-gob-ar",
    triggered_by: Annotated[str, typer.Option(help="Actor recorded on the run")] = "cli",
) -> None:
    """Synchronize one configured catalogue (metadata discovery only)."""
    settings = _settings()
    source_row = asyncio.run(_load_source(source))

    async def _run() -> dict[str, object]:
        connector = _build_connector(source_row, settings)
        try:
            async with session_scope() as session:
                reaped = await _reap_stale_runs(session)
                if reaped:
                    logger.warning("stale_runs_reaped", count=reaped)
                db_source = await session.get(DataSource, source_row.id)
                if db_source is None:  # pragma: no cover - deleted between calls
                    raise typer.BadParameter(f"source {source!r} disappeared")
                service = CatalogSyncService(
                    session=session,
                    connector=connector,
                    source=db_source,
                    storage=LocalFileSystemStorage(Path(settings.storage_root)),
                    triggered_by=triggered_by,
                )
                return (await service.run()).as_dict()
        finally:
            close = getattr(connector, "aclose", None)
            if close is not None:
                await close()
            await dispose_engine()

    result = asyncio.run(_run())
    typer.echo(json.dumps(result, indent=2, ensure_ascii=False))
    status = str(result["status"])
    raise typer.Exit(code=0 if status == "succeeded" else 1)


catalog_app = typer.Typer(help="Catalogue maintenance", no_args_is_help=True)
app.add_typer(catalog_app, name="catalog")


@catalog_app.command("reindex-search")
def reindex_search() -> None:
    """Rebuild the accent-free search projection for every stored dataset."""

    async def _run() -> int:
        from sqlalchemy.orm import joinedload

        from .core.text import build_search_text
        from .modules.catalog.models import Dataset

        _settings()
        updated = 0
        async with session_scope() as session:
            rows = await session.scalars(select(Dataset).options(joinedload(Dataset.organization)))
            for dataset in rows:
                dataset.search_text = build_search_text(
                    dataset.title,
                    dataset.description,
                    dataset.organization.name if dataset.organization else None,
                )
                updated += 1
        await dispose_engine()
        return updated

    count = asyncio.run(_run())
    typer.echo(json.dumps({"reindexed": count}, indent=2))


@app.command("check")
def check() -> None:
    """Verify database connectivity and the migrated schema."""
    from sqlalchemy import text

    async def _run() -> dict[str, object]:
        settings = _settings()
        async with session_scope() as session:
            version = await session.scalar(text("select version()"))
            tables = await session.scalar(
                text("select count(*) from information_schema.tables where table_schema = 'public'")
            )
        await dispose_engine()
        return {
            "database": str(version).split(" on ")[0] if version else "unknown",
            "public_tables": tables,
            "storage_root": str(settings.storage_root),
            "environment": settings.environment,
        }

    typer.echo(json.dumps(asyncio.run(_run()), indent=2, ensure_ascii=False))


if __name__ == "__main__":  # pragma: no cover
    app()
