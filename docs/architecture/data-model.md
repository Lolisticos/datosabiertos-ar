# Modelo de datos

Catorce tablas de aplicación en el schema `public`, creadas por la migración
`403adb281215` y enriquecidas por `5b1e2c9d7a10` (`dataset.search_text`).
Convenciones generales (`db/base.py`):

- PK `id uuid` con default `gen_random_uuid()` (`UuidPrimaryKeyMixin`).
- `created_at`/`updated_at` con timezone en las entidades de catálogo
  (`TimestampMixin`). Los tiempos de negocio (publicación, observación,
  descarga, procesamiento) son columnas explícitas, ver abajo.
- Convención de nombres para constraints (`ix_/uq_/ck_/fk_/pk_`).
- Enums de Postgres con los valores del `StrEnum` de Python.
- Valores monetarios/estadísticos siempre `Numeric`, nunca `float`.

## Diagrama ER (simplificado)

```
                        jurisdiction ──┐ (autorreferencia parent_id)
                             │ 1      │
                             │        │ n  jurisdiction_code (scheme, code)
organization ────────────────┤        ▼
   │ 1                       └── data_source ──< dataset ──< dataset_resource
   │                            │ 1        │ 1          │ 1        │ 1
   └── n (datasets, sources)    │          │            │          │
                                ▼          ▼            ▼          ▼
                         ingestion_run  data_change  resource_snapshot
                                │          │            │ 1
                                │          │            │
                                ▼          └────────────┼── transformation_run
                      data_quality_check                │
indicator ──< indicator_observation >── (snapshot_id) ──┘
```

## Tablas

### `jurisdiction` — unidad territorial (`modules/jurisdictions/models.py`)

`name`, `type` (`country|province|department|municipality|locality`),
`parent_id` (autorreferencia, `ON DELETE RESTRICT`), `official_code`,
`geometry` PostGIS `GEOMETRY, 4326` (nullable). Único
`(parent_id, type, name)` + índice parcial único `(type, name)` para raíces
(`parent_id IS NULL`), porque en SQL un unique común ignora los NULL.

### `jurisdiction_code` — códigos por esquema

`scheme` + `code`, único `(scheme, code)`. Argentina no tiene un único sistema
oficial (INDEC, GeoRef, ISO, códigos provinciales): cada jurisdicción acumula
esquemas sin decidir cuál es "el canónico". Semilla: `Argentina/country` +
`iso-3166-1-alpha-2 = AR` (migración `7f6c1d2ab9e4`).

### `organization` — organismo publicador

`name` (único case-insensitive vía índice funcional `lower(name)`), `acronym`,
`jurisdiction_id` (SET NULL), `official_url`. La deduplicación es por nombre
entre fuentes: los ids de organización de cada catálogo son locales a ese
catálogo; el payload original queda en el snapshot RAW.

### `data_source` — fuente autorizada

`slug` único, `name`, `base_url` única, `source_type`
(`ckan|dkan|rest_api|file_download|html|other`), `license`, `notes`,
`is_active`, FKs a `organization` y `jurisdiction` (ambas SET NULL). **Toda
ingesta requiere una fila previa aquí**; los conectores nunca reciben una URL
arbitraria (regla "solo fuentes configuradas", ver
[ingestion](ingestion.md)). Semilla: `datos-gob-ar` (CKAN nacional).

### `dataset` — dataset lógico normalizado

`source_id` (CASCADE), `organization_id` (SET NULL), `external_id`,
único `(source_id, external_id)`; `title` (512), `description`, `topic`,
`license`; `coverage_start/end` (publicación), `last_source_update`,
`last_successful_sync`, `landing_url`; `search_text` (proyección sin acentos
para búsqueda, migración `5b1e2c9d7a10`); `metadata_hash` (SHA-256 para
detección de cambios); `is_available`; `raw_metadata` JSONB (payload upstream
íntegro). Índices sobre `topic`, `last_source_update`, `metadata_hash`,
`search_text` + GIN trigram sobre `title`, `description` y `search_text`
(pg_trgm).

### `dataset_resource` — distribución de un dataset

`dataset_id` (CASCADE), `external_id`, único `(dataset_id, external_id)`;
`name`, `format`, `url` (2048), `mime_type`, `checksum`, `file_size`
(BigInteger), `last_modified`, `is_available`.

### `ingestion_run` — una ejecución de conector

`source_id` (CASCADE), `dataset_id`/`resource_id` (SET NULL, para corridas a
nivel recurso), `run_type` (`catalog_discovery|resource_fetch`), `status`
(`running|succeeded|partial|failed`), `triggered_by`, `transformation_version`,
`started_at`/`finished_at`, contadores `records_read/accepted/rejected`,
`error_summary` (acotado a 2.000 caracteres).

### `resource_snapshot` — artefacto RAW inmutable

`kind` (`catalog_payload|resource_file`), `source_id` (para catálogos) o
`resource_id` (para archivos), `ingestion_run_id` (SET NULL), `content_hash`
(SHA-256), `storage_key`, `media_type`, `file_size`, `schema_fingerprint`,
`fetched_at` (descarga), `source_last_modified` (publicación). Dos índices
parciales únicos: `(resource_id, content_hash)` cuando hay recurso y
`(source_id, content_hash)` cuando es payload de catálogo — la deduplicación de
snapshots es la base de la idempotencia.

### `snapshot_metadata` — metadata auxiliar del snapshot

PK = `snapshot_id` (CASCADE), `payload` JSONB. Separada para que headers de
respuesta o evidencia futura del conector no obliguen a migrar la tabla
principal.

### `data_quality_check` — validación determinística

`ingestion_run_id` (CASCADE), `check_type`, `status`
(`passed|warning|failed|skipped`), `details` JSONB, `checked_at`. La sincronización
registra hoy tres chequeos por run: `catalog_pages_fetched`,
`datasets_persisted`, `records_read_matches_persisted`
(`modules/ingestion/service.py`).

### `data_change` — cambio factual detectado

`change_type` (`dataset_added|dataset_removed|resource_added|resource_removed|
content_changed|schema_changed|metadata_changed|fetch_failed|recovered`),
FKs a run/dataset/resource/snapshots (previo y actual), `change_summary` JSONB
con los campos afectados, `detected_at`. Es un hecho explicable, nunca un
juicio de irregularidad.

### `transformation_run` — proveniencia de transformaciones

`snapshot_id` (CASCADE), `name`, `version`, `status`
(`running|succeeded|failed`), contadores `records_in/out`, `error_summary`;
único `(snapshot_id, name, version)`: qué versión de transformación produjo
cada resultado, para reprocesar RAW sin descargar de nuevo.

### `indicator` — definición semántica

`code` único, `name`, `description`, `unit`, `methodology`, `source_id`
(SET NULL), `topic`.

### `indicator_observation` — valor observado

`indicator_id` (CASCADE), `jurisdiction_id` (RESTRICT, nullable),
`period_start`/`period_end`, `value Numeric(24,6)`, `unit`,
`dimensions` JSONB + `dimension_hash`, `snapshot_id` (SET NULL),
`review_status` (`draft|reviewed|published`).

## Separación temporal (cuatro relojes)

| Momento | Columna(s) |
| --- | --- |
| Publicación en origen | `dataset.coverage_start/end`, `dataset.last_source_update`, `resource_snapshot.source_last_modified` |
| Observación (período del dato) | `indicator_observation.period_start/period_end` |
| Descarga | `resource_snapshot.fetched_at`, `ingestion_run.started_at` |
| Procesamiento | `transformation_run.started_at/finished_at`, `dataset.last_successful_sync`, `created_at/updated_at` |

## Diseño de observaciones con dimensiones extensibles

Problema: agregar una dimensión (sexo, rango etario, sector, moneda) no debe
exigir una migración por dataset (spec S8). Solución implementada en
`modules/indicators/models.py:113`:

- `dimensions`: JSONB **canónico** (claves ordenadas, encoding determinista,
  misma técnica que `canonical_json` en los conectores).
- `dimension_hash`: SHA-256 del JSON canónico.
- Clave única `(indicator_id, jurisdiction_id, period_start, dimension_hash)`
  con `NULLS NOT DISTINCT` (PostgreSQL 15+): dos observaciones sin jurisdicción
  (nivel nacional) con igual indicador/período/dimensiones colisionan como
  deben, en vez de tratarse como distintas por el NULL.

Una dimensión nueva implica una observación nueva, no una columna nueva.

## Por qué no una tabla JSONB ancha para datasets heterogéneos

Los datasets del catálogo comparten un contrato fijo y relacional (las columnas
de arriba); lo heterogéneo se preserva íntegro en el snapshot RAW y en
`dataset.raw_metadata`, sin fingir tipado. Cuando existan datos tabulares
reales, el lugar tipado para valores es `indicator_observation`
(`Numeric(24,6)`), no columnas `float` ni JSONB de valores. Así el catálogo se
consulta con SQL e índices reales y el payload original permanece disponible
para reprocesar.

Ver también: [arquitectura](overview.md) · [ingesta](ingestion.md) ·
[ADR-002](../decisions/ADR-002-data-ingestion.md)
