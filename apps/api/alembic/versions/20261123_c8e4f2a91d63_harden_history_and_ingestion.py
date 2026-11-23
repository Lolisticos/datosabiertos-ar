"""Harden historical retention and atomic ingestion metadata.

Revision ID: c8e4f2a91d63
Revises: 5b1e2c9d7a10
Create Date: 2026-11-23 22:30:00+00:00
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "c8e4f2a91d63"
down_revision: str | None = "5b1e2c9d7a10"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _replace_fk(
    table: str,
    name: str,
    local: str,
    remote_table: str,
    remote: str,
    *,
    ondelete: str,
) -> None:
    op.drop_constraint(name, table, type_="foreignkey")
    op.create_foreign_key(name, table, remote_table, [local], [remote], ondelete=ondelete)


def upgrade() -> None:
    op.add_column("ingestion_run", sa.Column("schema_fingerprint", sa.String(64)))
    op.add_column("resource_snapshot", sa.Column("normalized_hash", sa.String(64)))
    op.add_column("dataset", sa.Column("removed_at", sa.DateTime(timezone=True)))
    op.add_column("dataset_resource", sa.Column("removed_at", sa.DateTime(timezone=True)))

    op.create_index("ix_dataset_removed_at", "dataset", ["removed_at"])
    op.create_index("ix_dataset_resource_removed_at", "dataset_resource", ["removed_at"])
    op.create_index(
        "uq_resource_snapshot_storage_key", "resource_snapshot", ["storage_key"], unique=True
    )
    op.create_index(
        "ix_resource_snapshot_normalized_hash", "resource_snapshot", ["normalized_hash"]
    )
    op.create_check_constraint(
        "ck_resource_snapshot_owner",
        "resource_snapshot",
        "(kind = 'catalog_payload' AND source_id IS NOT NULL AND resource_id IS NULL) "
        "OR (kind = 'resource_file' AND source_id IS NULL AND resource_id IS NOT NULL)",
    )

    _replace_fk(
        "dataset",
        "fk_dataset_source_id_data_source",
        "source_id",
        "data_source",
        "id",
        ondelete="RESTRICT",
    )
    _replace_fk(
        "dataset_resource",
        "fk_dataset_resource_dataset_id_dataset",
        "dataset_id",
        "dataset",
        "id",
        ondelete="RESTRICT",
    )
    _replace_fk(
        "ingestion_run",
        "fk_ingestion_run_source_id_data_source",
        "source_id",
        "data_source",
        "id",
        ondelete="RESTRICT",
    )
    _replace_fk(
        "resource_snapshot",
        "fk_resource_snapshot_source_id_data_source",
        "source_id",
        "data_source",
        "id",
        ondelete="RESTRICT",
    )
    _replace_fk(
        "resource_snapshot",
        "fk_resource_snapshot_resource_id_dataset_resource",
        "resource_id",
        "dataset_resource",
        "id",
        ondelete="RESTRICT",
    )
    _replace_fk(
        "data_change",
        "fk_data_change_dataset_id_dataset",
        "dataset_id",
        "dataset",
        "id",
        ondelete="SET NULL",
    )
    _replace_fk(
        "data_change",
        "fk_data_change_resource_id_dataset_resource",
        "resource_id",
        "dataset_resource",
        "id",
        ondelete="SET NULL",
    )
    _replace_fk(
        "transformation_run",
        "fk_transformation_run_snapshot_id_resource_snapshot",
        "snapshot_id",
        "resource_snapshot",
        "id",
        ondelete="RESTRICT",
    )
    _replace_fk(
        "indicator_observation",
        "fk_indicator_observation_indicator_id_indicator",
        "indicator_id",
        "indicator",
        "id",
        ondelete="RESTRICT",
    )

    op.execute("ALTER TYPE change_type ADD VALUE IF NOT EXISTS 'resource_unavailable'")
    op.execute("ALTER TYPE change_type ADD VALUE IF NOT EXISTS 'resource_recovered'")
    op.execute("ALTER TYPE change_type ADD VALUE IF NOT EXISTS 'methodology_changed'")


def downgrade() -> None:
    op.execute(
        "UPDATE data_change SET change_type = 'fetch_failed' "
        "WHERE change_type::text = 'resource_unavailable'"
    )
    op.execute(
        "UPDATE data_change SET change_type = 'recovered' "
        "WHERE change_type::text = 'resource_recovered'"
    )
    op.execute(
        "UPDATE data_change SET change_type = 'metadata_changed' "
        "WHERE change_type::text = 'methodology_changed'"
    )
    op.execute("ALTER TABLE data_change ALTER COLUMN change_type TYPE text USING change_type::text")
    op.execute("DROP TYPE change_type")
    op.execute(
        "CREATE TYPE change_type AS ENUM ("
        "'dataset_added', 'dataset_removed', 'resource_added', 'resource_removed', "
        "'content_changed', 'schema_changed', 'metadata_changed', 'fetch_failed', 'recovered')"
    )
    op.execute(
        "ALTER TABLE data_change ALTER COLUMN change_type TYPE change_type "
        "USING change_type::change_type"
    )

    _replace_fk(
        "indicator_observation",
        "fk_indicator_observation_indicator_id_indicator",
        "indicator_id",
        "indicator",
        "id",
        ondelete="CASCADE",
    )
    _replace_fk(
        "transformation_run",
        "fk_transformation_run_snapshot_id_resource_snapshot",
        "snapshot_id",
        "resource_snapshot",
        "id",
        ondelete="CASCADE",
    )
    _replace_fk(
        "data_change",
        "fk_data_change_resource_id_dataset_resource",
        "resource_id",
        "dataset_resource",
        "id",
        ondelete="CASCADE",
    )
    _replace_fk(
        "data_change",
        "fk_data_change_dataset_id_dataset",
        "dataset_id",
        "dataset",
        "id",
        ondelete="CASCADE",
    )
    _replace_fk(
        "resource_snapshot",
        "fk_resource_snapshot_resource_id_dataset_resource",
        "resource_id",
        "dataset_resource",
        "id",
        ondelete="CASCADE",
    )
    _replace_fk(
        "resource_snapshot",
        "fk_resource_snapshot_source_id_data_source",
        "source_id",
        "data_source",
        "id",
        ondelete="CASCADE",
    )
    _replace_fk(
        "ingestion_run",
        "fk_ingestion_run_source_id_data_source",
        "source_id",
        "data_source",
        "id",
        ondelete="CASCADE",
    )
    _replace_fk(
        "dataset_resource",
        "fk_dataset_resource_dataset_id_dataset",
        "dataset_id",
        "dataset",
        "id",
        ondelete="CASCADE",
    )
    _replace_fk(
        "dataset",
        "fk_dataset_source_id_data_source",
        "source_id",
        "data_source",
        "id",
        ondelete="CASCADE",
    )

    op.drop_constraint("ck_resource_snapshot_owner", "resource_snapshot", type_="check")
    op.drop_index("ix_resource_snapshot_normalized_hash", table_name="resource_snapshot")
    op.drop_index("uq_resource_snapshot_storage_key", table_name="resource_snapshot")
    op.drop_index("ix_dataset_resource_removed_at", table_name="dataset_resource")
    op.drop_index("ix_dataset_removed_at", table_name="dataset")
    op.drop_column("dataset_resource", "removed_at")
    op.drop_column("dataset", "removed_at")
    op.drop_column("resource_snapshot", "normalized_hash")
    op.drop_column("ingestion_run", "schema_fingerprint")
