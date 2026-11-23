"""Add versioned statistical series metadata and seed the official EMAE source.

Revision ID: d91a7b3c4e52
Revises: c8e4f2a91d63
Create Date: 2026-11-23 23:30:00+00:00
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "d91a7b3c4e52"
down_revision: str | None = "c8e4f2a91d63"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

JURISDICTION_ID = "c0a8014e-0000-4000-8000-000000000001"
ORGANIZATION_ID = "c0a8014e-0000-4000-8000-000000000011"
SOURCE_ID = "c0a8014e-0000-4000-8000-000000000012"
DATASET_ID = "c0a8014e-0000-4000-8000-000000000013"
RESOURCE_ID = "c0a8014e-0000-4000-8000-000000000014"
INDICATOR_ID = "c0a8014e-0000-4000-8000-000000000015"


def upgrade() -> None:
    op.execute("ALTER TYPE ingestion_run_type ADD VALUE IF NOT EXISTS 'statistical_series'")

    op.add_column("indicator", sa.Column("frequency", sa.String(32)))
    op.add_column("indicator", sa.Column("source_series_id", sa.String(128)))
    op.add_column("indicator", sa.Column("source_url", sa.String(1024)))
    op.add_column("indicator", sa.Column("methodology_url", sa.String(1024)))
    op.add_column("indicator", sa.Column("license", sa.String(255)))
    op.alter_column(
        "indicator_observation",
        "value",
        existing_type=sa.Numeric(24, 6),
        type_=sa.Numeric(24, 12),
        nullable=True,
    )
    op.add_column("indicator_observation", sa.Column("transformation_run_id", sa.Uuid()))
    op.add_column(
        "indicator_observation", sa.Column("published_at", sa.DateTime(timezone=True))
    )
    op.create_foreign_key(
        "fk_indicator_observation_transformation_run",
        "indicator_observation",
        "transformation_run",
        ["transformation_run_id"],
        ["id"],
        ondelete="RESTRICT",
    )
    op.create_index(
        "ix_indicator_observation_transformation_run_id",
        "indicator_observation",
        ["transformation_run_id"],
    )
    op.add_column(
        "transformation_run",
        sa.Column("records_rejected", sa.Integer(), server_default="0", nullable=False),
    )
    op.add_column(
        "transformation_run",
        sa.Column(
            "rejection_details",
            postgresql.JSONB(),
            server_default=sa.text("'[]'::jsonb"),
            nullable=False,
        ),
    )

    # Keep this migration reproducible even in ephemeral test databases where
    # tables are truncated while Alembic's revision marker is preserved.
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
            INSERT INTO organization (id, name, acronym, jurisdiction_id, official_url)
            VALUES (
                CAST(:id AS uuid),
                'Instituto Nacional de Estadística y Censos',
                'INDEC',
                CAST(:jurisdiction_id AS uuid),
                'https://www.indec.gob.ar'
            )
            ON CONFLICT DO NOTHING
            """
        ).bindparams(id=ORGANIZATION_ID, jurisdiction_id=JURISDICTION_ID)
    )
    op.execute(
        sa.text(
            """
            INSERT INTO data_source (
                id, organization_id, jurisdiction_id, slug, name, base_url,
                source_type, license, notes, is_active
            ) VALUES (
                CAST(:id AS uuid), CAST(:organization_id AS uuid),
                CAST(:jurisdiction_id AS uuid), 'series-tiempo-argentina',
                'API Series de Tiempo de la Administración Pública Nacional',
                'https://apis.datos.gob.ar', 'rest_api',
                'Creative Commons Attribution 4.0',
                'La serie seleccionada declara al INDEC como fuente primaria. '
                'El conector consume una serie explícita y conserva la respuesta RAW.',
                true
            )
            ON CONFLICT DO NOTHING
            """
        ).bindparams(
            id=SOURCE_ID,
            organization_id=ORGANIZATION_ID,
            jurisdiction_id=JURISDICTION_ID,
        )
    )
    op.execute(
        sa.text(
            """
            INSERT INTO dataset (
                id, source_id, organization_id, external_id, title, description,
                topic, license, landing_url, search_text, metadata_hash,
                is_available, raw_metadata
            ) VALUES (
                CAST(:id AS uuid), CAST(:source_id AS uuid), CAST(:organization_id AS uuid),
                '143', 'Estimador Mensual de Actividad Económica (EMAE). Base 2004',
                'Índice original mensual del EMAE, base 2004.', 'Economía',
                'Creative Commons Attribution 4.0',
                'https://datos.gob.ar/dataset/sspm-estimador-mensual-actividad-economica-emae-base-2004',
                'estimador mensual de actividad economica emae base 2004 indec',
                '59d76dafea9955d77035378facd54984c35192fcc58f58ecf6d80cbc374aa298',
                true,
                jsonb_build_object(
                    'official_series_id', '143.3_NO_PR_2004_A_21',
                    'seeded_reference', true
                )
            )
            ON CONFLICT DO NOTHING
            """
        ).bindparams(id=DATASET_ID, source_id=SOURCE_ID, organization_id=ORGANIZATION_ID)
    )
    op.execute(
        sa.text(
            """
            INSERT INTO dataset_resource (
                id, dataset_id, external_id, name, format, url, mime_type, is_available
            ) VALUES (
                CAST(:id AS uuid), CAST(:dataset_id AS uuid), '143.3_NO_PR_2004_A_21',
                'EMAE original. Índice base 2004. Valores mensuales', 'JSON',
                'https://apis.datos.gob.ar/series/api/series/?ids=143.3_NO_PR_2004_A_21',
                'application/json', true
            )
            ON CONFLICT DO NOTHING
            """
        ).bindparams(id=RESOURCE_ID, dataset_id=DATASET_ID)
    )
    op.execute(
        sa.text(
            """
            INSERT INTO indicator (
                id, code, name, description, unit, methodology, frequency,
                source_series_id, source_url, methodology_url, license, source_id, topic
            ) VALUES (
                CAST(:id AS uuid), 'emae-original-2004',
                'Estimador Mensual de Actividad Económica',
                'Evolución mensual de la actividad económica de la Argentina. Serie original.',
                'Índice 2004=100',
                'Serie original publicada por el INDEC. No se mezcla con la serie '
                'desestacionalizada ni con la tendencia-ciclo.',
                'monthly', '143.3_NO_PR_2004_A_21',
                'https://apis.datos.gob.ar/series/api/series/?ids=143.3_NO_PR_2004_A_21',
                'https://www.indec.gob.ar/indec/web/Nivel4-Tema-3-9-48',
                'Creative Commons Attribution 4.0', CAST(:source_id AS uuid), 'Economía'
            )
            ON CONFLICT DO NOTHING
            """
        ).bindparams(id=INDICATOR_ID, source_id=SOURCE_ID)
    )


def downgrade() -> None:
    # Remove only artifacts owned by the reference series introduced here.
    op.execute(
        sa.text(
            "DELETE FROM indicator_observation WHERE indicator_id = CAST(:id AS uuid)"
        ).bindparams(id=INDICATOR_ID)
    )
    op.execute(
        sa.text(
            """
            DELETE FROM transformation_run
            WHERE snapshot_id IN (
                SELECT id FROM resource_snapshot WHERE resource_id = CAST(:resource_id AS uuid)
            )
            """
        ).bindparams(resource_id=RESOURCE_ID)
    )
    op.execute(
        sa.text(
            "DELETE FROM resource_snapshot WHERE resource_id = CAST(:resource_id AS uuid)"
        ).bindparams(resource_id=RESOURCE_ID)
    )
    op.execute(
        sa.text("DELETE FROM ingestion_run WHERE source_id = CAST(:source_id AS uuid)").bindparams(
            source_id=SOURCE_ID
        )
    )
    op.execute(sa.text("DELETE FROM indicator WHERE id = CAST(:id AS uuid)").bindparams(id=INDICATOR_ID))
    op.execute(
        sa.text("DELETE FROM dataset_resource WHERE id = CAST(:id AS uuid)").bindparams(
            id=RESOURCE_ID
        )
    )
    op.execute(sa.text("DELETE FROM dataset WHERE id = CAST(:id AS uuid)").bindparams(id=DATASET_ID))
    op.execute(
        sa.text("DELETE FROM data_source WHERE id = CAST(:id AS uuid)").bindparams(id=SOURCE_ID)
    )
    op.execute(
        sa.text("DELETE FROM organization WHERE id = CAST(:id AS uuid)").bindparams(
            id=ORGANIZATION_ID
        )
    )

    op.drop_column("transformation_run", "rejection_details")
    op.drop_column("transformation_run", "records_rejected")
    op.drop_index(
        "ix_indicator_observation_transformation_run_id", table_name="indicator_observation"
    )
    op.drop_constraint(
        "fk_indicator_observation_transformation_run",
        "indicator_observation",
        type_="foreignkey",
    )
    op.drop_column("indicator_observation", "published_at")
    op.drop_column("indicator_observation", "transformation_run_id")
    op.execute("DELETE FROM indicator_observation WHERE value IS NULL")
    op.alter_column(
        "indicator_observation",
        "value",
        existing_type=sa.Numeric(24, 12),
        type_=sa.Numeric(24, 6),
        nullable=False,
    )
    op.drop_column("indicator", "license")
    op.drop_column("indicator", "methodology_url")
    op.drop_column("indicator", "source_url")
    op.drop_column("indicator", "source_series_id")
    op.drop_column("indicator", "frequency")

    op.execute(
        "UPDATE ingestion_run SET run_type = 'resource_fetch' "
        "WHERE run_type::text = 'statistical_series'"
    )
    op.execute(
        "ALTER TABLE ingestion_run ALTER COLUMN run_type TYPE text USING run_type::text"
    )
    op.execute("DROP TYPE ingestion_run_type")
    op.execute(
        "CREATE TYPE ingestion_run_type AS ENUM ('catalog_discovery', 'resource_fetch')"
    )
    op.execute(
        "ALTER TABLE ingestion_run ALTER COLUMN run_type TYPE ingestion_run_type "
        "USING run_type::ingestion_run_type"
    )
