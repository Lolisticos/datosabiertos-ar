"""Seed the national jurisdiction and the first authorized source.

Only reference data lives here: the country row used to classify national
catalogues, its ISO code, and the `datos.gob.ar` CKAN source that the CLI is
allowed to ingest. No dataset, organization or observation is invented.

Revision ID: 7f6c1d2ab9e4
Revises: 403adb281215
Create Date: 2026-11-23 19:30:00+00:00
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "7f6c1d2ab9e4"
down_revision: str | None = "403adb281215"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

JURISDICTION_ID = "c0a8014e-0000-4000-8000-000000000001"


def upgrade() -> None:
    op.execute(
        sa.text(
            """
            INSERT INTO jurisdiction (id, name, type, official_code)
            VALUES (CAST(:id AS uuid), 'Argentina', 'country', 'AR')
            ON CONFLICT DO NOTHING
            """
        ).bindparams(id=JURISDICTION_ID)
    )
    op.execute(
        sa.text(
            """
            INSERT INTO jurisdiction_code (jurisdiction_id, scheme, code)
            VALUES (CAST(:id AS uuid), 'iso-3166-1-alpha-2', 'AR')
            ON CONFLICT DO NOTHING
            """
        ).bindparams(id=JURISDICTION_ID)
    )
    op.execute(
        sa.text(
            """
            INSERT INTO data_source
                (slug, name, base_url, source_type, jurisdiction_id, license, notes, is_active)
            VALUES (
                'datos-gob-ar',
                'Catálogo Nacional de Datos Abiertos',
                'https://datos.gob.ar',
                'ckan',
                CAST(:jurisdiction_id AS uuid),
                NULL,
                'Catálogo CKAN nacional administrado por la Jefatura de Gabinete de Ministros. '
                'La licencia se registra por dataset: el catálogo no declara una licencia única '
                'y varias distribuciones informan Creative Commons Attribution 4.0.',
                true
            )
            ON CONFLICT DO NOTHING
            """
        ).bindparams(jurisdiction_id=JURISDICTION_ID)
    )


def downgrade() -> None:
    op.execute("DELETE FROM data_source WHERE slug = 'datos-gob-ar'")
    op.execute(sa.text("DELETE FROM jurisdiction WHERE id = CAST(:id AS uuid)").bindparams(id=JURISDICTION_ID))
