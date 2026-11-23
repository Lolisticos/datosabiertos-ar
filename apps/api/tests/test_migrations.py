"""The migrated database matches the declared head of the migration chain."""

from __future__ import annotations

from pathlib import Path

from alembic.config import Config
from alembic.script import ScriptDirectory
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine

API_DIR = Path(__file__).resolve().parents[1]


def _head_revision() -> str:
    config = Config(str(API_DIR / "alembic.ini"))
    config.set_main_option("script_location", str(API_DIR / "alembic"))
    head = ScriptDirectory.from_config(config).get_current_head()
    assert head is not None
    return head


async def test_database_is_at_alembic_head(engine: AsyncEngine) -> None:
    async with engine.connect() as connection:
        revision = await connection.scalar(text("SELECT version_num FROM alembic_version"))
    assert revision == _head_revision()


async def test_required_extensions_and_tables_exist(engine: AsyncEngine) -> None:
    async with engine.connect() as connection:
        extensions = {
            row[0] for row in await connection.execute(text("SELECT extname FROM pg_extension"))
        }
        tables = {
            row[0]
            for row in await connection.execute(
                text("SELECT tablename FROM pg_tables WHERE schemaname = 'public'")
            )
        }

    assert {"pg_trgm", "postgis"} <= extensions
    assert {
        "jurisdiction",
        "jurisdiction_code",
        "organization",
        "data_source",
        "dataset",
        "dataset_resource",
        "ingestion_run",
        "resource_snapshot",
        "data_quality_check",
        "data_change",
        "indicator",
        "indicator_observation",
        "transformation_run",
    } <= tables
