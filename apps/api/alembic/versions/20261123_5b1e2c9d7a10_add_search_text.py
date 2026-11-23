"""Add the accent-free search projection used by the catalogue search.

The projection is maintained by the application (see ``core.text``), because
PostgreSQL's ``unaccent`` is not IMMUTABLE and therefore cannot back an index
directly. Backfilling existing rows happens through
``datosabiertos catalog reindex-search``.

Revision ID: 5b1e2c9d7a10
Revises: 7f6c1d2ab9e4
Create Date: 2026-11-23 19:45:00+00:00
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "5b1e2c9d7a10"
down_revision: str | None = "7f6c1d2ab9e4"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("dataset", sa.Column("search_text", sa.Text(), nullable=True))
    op.create_index("ix_dataset_search_text", "dataset", ["search_text"])
    op.execute(
        "CREATE INDEX ix_dataset_search_text_trgm ON dataset USING gin (search_text gin_trgm_ops)"
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ix_dataset_search_text_trgm")
    op.drop_index("ix_dataset_search_text", table_name="dataset")
    op.drop_column("dataset", "search_text")
