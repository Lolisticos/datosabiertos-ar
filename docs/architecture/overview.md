# Arquitectura

DatosAbiertos AR es un **monolito modular**: una sola aplicación FastAPI, un
solo proceso de ingesta (CLI Typer) y una sola base PostgreSQL/PostGIS. La
modularidad es interna, por dominio; no hay microservicios ni se planean (spec
S6: "Los módulos no deben convertirse en microservicios").

## Módulos

`apps/api/src/datosabiertos/modules/` contiene un paquete por dominio:

| Módulo | Responsabilidad |
| --- | --- |
| `sources` | Fuentes autorizadas (`DataSource`), registro previo a toda ingesta |
| `catalog` | `Dataset` y `DatasetResource` normalizados |
| `ingestion` | Ejecuciones (`IngestionRun`), snapshots RAW, servicio de sincronización, storage |
| `organizations` | Organismos publicadores, deduplicados por nombre |
| `jurisdictions` | Entidades territoriales y sus códigos por esquema (INDEC, GeoRef, ISO…) |
| `provenance` | `TransformationRun`: qué versión de transformación produjo cada resultado |
| `quality` | `DataQualityCheck`: validaciones determinísticas por ejecución |
| `history` | `DataChange`: diferencias factuales detectadas entre estados |
| `indicators` | `Indicator` e `IndicatorObservation` (estructura lista, sin datos aún) |
| `search` | Búsqueda del catálogo solo sobre PostgreSQL |

La especificación nombra `geography` y `data_quality`; en la implementación esas
responsabilidades viven en `jurisdictions` y `quality` respectivamente.

## Límites entre capas

```
api/        routers + schemas (Pydantic) + mappers + deps   ← contrato HTTP
modules/    models (SQLAlchemy) + queries (SELECT) + services (escritura)
db/         Base, sesiones async, registro central de modelos
```

Reglas efectivas en el código:

- Los routers no ejecutan SQL: delegan en `modules/*/queries.py` (lectura) o en
  servicios como `modules/ingestion/service.py:98` (`CatalogSyncService`).
- `api/mappers.py` traduce entidades a schemas; el frontend nunca ve las
  estructuras internas de la fuente original (spec S13). El payload upstream se
  preserva en RAW y en `dataset.raw_metadata`.
- `api/deps.py:41` impone paginación acotada (`page` ≤ 10.000, `page_size` ≤
  100, default 20): la API nunca devuelve colecciones sin límite.
- Los conectores (`packages/data_connectors`) son un paquete independiente del
  workspace uv; el núcleo de ingesta depende del protocolo `SourceConnector`
  (`types.py:154`), no de conectores concretos.

## Flujo de una request HTTP

```
request → middleware X-Request-ID (main.py:70)
        → router (api/routers/*)
        → deps: get_session (una AsyncSession por request) + Pagination
        → modules/*/queries.py (SELECT con SQLAlchemy async + psycopg 3)
        → mappers → schema Pydantic → JSON
```

Errores: sobre constante `{"error": {code, message, details?, request_id?}}`
(`core/errors.py`). Los 500 inesperados se loguean con stack trace pero
responden "Error interno del servidor."; nunca se filtran internals.

## Flujo de ingesta y proveniencia RAW

```
CLI `datosabiertos ingest sync --source <slug>`
  → DataSource por slug (solo fuentes configuradas, cli.py:84)
  → conector construido desde la config almacenada
  → IngestionRun (status=running)
  → discover() → AsyncIterator[ConnectorPage]
      │  página (payload intacto + datasets canónicos)
      ▼
  RAW: hash del payload → ¿ya existe snapshot igual?
      sí → se reutiliza (dedup)          no → LocalFileSystemStorage
      │                                     raw/<slug>/catalog/AAAA/MM/…json
      ▼                                     + ResourceSnapshot (hash, key)
  upsert Dataset/Resource (metadata_hash → cambios)
  DataChange (added/removed/changed/recovered) + DataQualityCheck (3 por run)
  commit por página
  → run final: succeeded | partial | failed (error_summary acotado)
```

Cada hecho publicado encadena: `Dataset` → `IngestionRun` → `ResourceSnapshot`
(RAW, inmutable, hash SHA-256) → bytes originales en `data/storage/`. La versión
de transformación se registra en el run (`TRANSFORMATION_VERSION` en
`service.py:46`).

## Por qué no microservices ni colas (todavía)

- El volumen real (1 catálogo, 1.293 datasets, sync completa en ~14 s) no
  justifica workers ni brokers; una corrida es una llamada de CLI.
- Las decisiones diferidas y sus condiciones de activación están en
  [ADR-001](../decisions/ADR-001-technology-stack.md) y
  [ADR-002](../decisions/ADR-002-data-ingestion.md).
- La separación api/modules/db y el contrato de conectores dejan el camino
  abierto: un módulo podría extraerse sin reescribir el dominio.

## Modos de fallo

| Fallo | Comportamiento |
| --- | --- |
| Respuesta upstream truncada (>~1 MB en datos.gob.ar) | El conector CKAN reduce la ventana de página a la mitad y reintenta el mismo offset (mínimo 10) |
| Recurso CKAN sin URL | Se omite con warning `ckan_resource_skipped`; el resto de la página sigue |
| HTTP transitorio (408/425/429/5xx) o timeout | Reintento con backoff exponencial y jitter (hasta `retry_attempts`) |
| HTTP no recuperable (4xx) | `UpstreamStatusError`: run `failed` o `partial` si ya había páginas |
| Página procesada y luego error | Commit por página ya aplicado; el run queda `partial` con `error_summary` |
| Proceso muerto a mitad de corrida | El reaper marca `failed` los runs `running` con más de 60 minutos (cli.py:59) |
| Re-ejecución sin cambios | 0 filas nuevas, 0 cambios, 0 snapshots: idempotencia por hashes |
| Host/URL no autorizado | `UnsafeUrlError` antes de tocar la red (guard SSRF) |

Estado real al 2026-11-23 en la base de desarrollo: 6 ejecuciones registradas
(2 `succeeded`, 1 `partial`, 2 `failed`, 1 `running` vieja), evidencia de que
los estados de fallo se persisten y son consultables vía
`GET /api/v1/ingestion-runs`.

## Observabilidad

- **Logs estructurados** con structlog: JSON en producción, consola en
  desarrollo (`core/logging.py`). Eventos clave: `catalog_sync_finished`,
  `ckan_page_retry_smaller`, `http_retry`, `http_redirect`, `stale_runs_reaped`.
- **Correlación**: middleware propaga `X-Request-ID` y lo anexa a cada log y al
  sobre de error.
- **Salud**: `GET /api/v1/health` (liveness) y `GET /api/v1/health/ready`
  (readiness: DB alcanzable + storage RAW escribible).
- **Métricas de negocio**: contadores por ejecución
  (`records_read/accepted/rejected`), chequeos de calidad por run y
  `GET /api/v1/stats/overview` con la cobertura agregada.
- No hay aún métricas tipo Prometheus ni tracing distribuido (diferido; el
  volumen actual no lo requiere).

## Decisiones deliberadamente diferidas

Colas y scheduler (Celery/Redis/Kafka/Airflow), almacenamiento de objetos S3
(hoy filesystem local tras `StorageBackend`, `storage.py:20`), motor de búsqueda
dedicado, autenticación, pipeline de indicadores con datos reales y despliegue
multi-host. Cada una tiene su condición de activación en los ADRs. La app web
del recorrido de catálogo sí forma parte de esta fase.

Ver también: [modelo de datos](data-model.md) ·
[sistema de ingesta](ingestion.md) ·
[ADR-001 stack](../decisions/ADR-001-technology-stack.md) ·
[ADR-002 ingesta](../decisions/ADR-002-data-ingestion.md)
