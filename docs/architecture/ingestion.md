# Sistema de ingesta

La ingesta tiene dos piezas separadas: el **paquete de conectores**
(`packages/data_connectors`, sin dependencias del núcleo) y el **servicio de
sincronización** (`apps/api/.../modules/ingestion/service.py`). Todo conector
implementa un único protocolo.

## Contrato `SourceConnector`

`packages/data_connectors/src/datosabiertos_connectors/types.py:154`:

```python
@runtime_checkable
class SourceConnector(Protocol):
    def metadata(self) -> ConnectorMetadata: ...
    def discover(self) -> AsyncIterator[ConnectorPage]: ...
    async def fetch(self, resource: SourceResource) -> FetchResult: ...
```

- `metadata()`: nombre, versión y tipo de fuente del conector.
- `discover()`: stream de páginas (`ConnectorPage`) — un catálogo de 1.000+
  datasets nunca se carga entero en memoria. Cada página incluye
  `raw_payload` (bytes intactos), `media_type`, `content_hash`, `offset`,
  `total_available`, `fetched_at` y los `SourceDataset` canónicos.
- `fetch()`: descarga de un recurso individual (hoy no se usa masivamente;
  alcance metadata-only, ver [ADR-002](../decisions/ADR-002-data-ingestion.md)).

Tipos canónicos (`types.py`): `SourceDataset`, `SourceResource`,
`SourceOrganization` (Pydantic inmutables), más `canonical_json` /
`canonical_hash` / `content_hash` (SHA-256). `SourceDataset.metadata_hash()`
(`types.py:82`) es la huella estable de metadatos: ignora orden de claves y
formato, así una variación cosmética upstream no produce un falso cambio.

## HTTP seguro y acotado (`http.py`)

`SafeHttpClient` (`http.py:108`) envuelve `httpx.AsyncClient` con políticas
obligatorias (`HttpPolicy`, `http.py:43`; los valores por defecto entre
paréntesis):

- **Timeout** (`30 s`) y **tope de bytes** (`50 MiB`), verificado sobre
  `Content-Length` y sobre el stream real.
- **Reintentos** con backoff exponencial y jitter (tenacity) ante timeouts,
  errores de transporte y estados 408/425/429/500/502/503/504
  (`http.py:39`); `retry_attempts` (3).
- **Rate limit por host** (`http.py:85`): espaciado mínimo entre requests;
  la CLI lo configura en 2 req/s desde `Settings`.
- **Redirects manuales** (máx. 3): cada salto se revalida por el guard SSRF.
- Todo error se traduce a tipos de `errors.py` (`UnsafeUrlError`,
  `UpstreamStatusError`, `RetryableUpstreamError`, `DownloadTooLargeError`,
  `UpstreamTransportError`, `InvalidPayloadError`).

## Guard SSRF (`ssrf.py`)

Se valida **antes** de cada request y en cada redirect (`ssrf.py:114`):

1. Esquema `https` solamente (`http` si la fuente lo habilita explícitamente);
   puertos estándar 443/80 únicamente.
2. Rechazo de URLs con credenciales embebidas o fragmentos.
3. El host debe ser el host configurado de la fuente o un subdominio suyo
   (`host_matches`).
4. Resolución DNS y rechazo de toda IP no enrutable globalmente: loopback,
   privadas RFC-1918, link-local, CGNAT, multicast y rangos reservados
   (`ssrf.py:30`).
5. Combinado con la regla "solo fuentes configuradas": la CLI construye el
   conector desde `data_source.base_url` almacenada; ningún endpoint ni comando
   acepta una URL arbitraria (spec S15).

## Conector CKAN (`ckan.py`)

Usa únicamente la Action API documentada `GET /api/3/action/package_search`
— nunca scraping HTML.

- **Tamaño de página 50, mínimo 10**: datos.gob.ar trunca respuestas por encima
  de ~1 MB; 50 es el mayor tamaño verificado contra el catálogo en vivo
  (`ckan.py:49`).
- **Reducción de ventana**: si una página llega truncada o falla el transporte,
  el conector reintenta el mismo offset con la mitad de filas; si ni el mínimo
  alcanza, `InvalidPayloadError`.
- **Orden estable** `sort=name asc`: evita filas duplicadas o perdidas mientras
  el catálogo cambia (`metadata_modified` reordena filas).
- **Recursos sin URL** se omiten con warning (`ckan_resource_skipped`) en vez
  de perder la página entera.
- **Licencia**: usa `license_title`/`license_id` del dataset; si está vacía
  (caso frecuente en datos.gob.ar) y todas las distribuciones declaran la misma
  `distribution_license`, se adopta esa; si difieren, queda `NULL` — nunca se
  inventa una licencia.
- **Tema** desde `groups[].title` (fallback `dataset_theme` de extras).
- Todo campo no base se preserva en `SourceDataset.raw_metadata` (payload
  íntegro).

## Servicio de sincronización (`service.py`)

`CatalogSyncService` (`service.py:98`), recorrido por run:

1. Crea `IngestionRun(running)` con `transformation_version`
   (`catalog-normalizer-1.1.0`, `service.py:46`).
2. Por cada `ConnectorPage`:
   - `_schema_fingerprint` (`service.py:549`): huella del conjunto de claves del
     payload; si difiere de la del último snapshot previo, registra
     `schema_changed`.
   - Guarda RAW solo si el `content_hash` es nuevo (dedup por hash): storage
     filesystem con rename atómico (`storage.py:57`) tras la abstracción
     `StorageBackend` (`storage.py:20`).
   - Upsert por `(source_id, external_id)`: compara `metadata_hash`.
     - Nuevo → `dataset_added`. Distinto → `metadata_changed` con lista de
       campos (`title`, `description`, `topic`, `license`, cobertura,
       `last_source_update`, `landing_url`, `organization_id`).
       Igual → sin cambios.
   - Recursos: `resource_added` / `resource_removed` (soft: `is_available=false`).
   - Páginas solapadas por reintentos de reducción se deduplican por
     `external_id` dentro del run.
   - **Commit por página**: una falla posterior no pierde lo ya procesado.
3. Datasets de la fuente ausentes en esta corrida → `dataset_removed`
   (`is_available=false`); si reaparecen, `recovered`.
4. Tres `DataQualityCheck`: `catalog_pages_fetched`, `datasets_persisted`,
   `records_read_matches_persisted`.
5. Estado final: `succeeded` (sin errores), `partial` (con errores o
   `ConnectorError` con páginas procesadas), `failed` (sin páginas). El
   `error_summary` se acota a 2.000 caracteres. La CLI sale con código 0 solo
   si `succeeded`.

### Esquema de claves RAW

`build_raw_key` (`storage.py:35`):
`raw/<slug>/<kind>/<AAAA>/<MM>/<AAAAMMDDTHHMMSSZ>-<hash16>.json`.
Ejemplo real de la corrida 2026-11-23:
`raw/datos-gob-ar/catalog/2026/11/20261123T192756Z-3f9a1c…json`.

### Tipos de cambio

`dataset_added`, `dataset_removed`, `resource_added`, `resource_removed`,
`content_changed` (reservado para `resource_fetch`), `schema_changed`,
`metadata_changed`, `fetch_failed`, `recovered` (`modules/history/models.py`).

### Idempotencia (verificada)

- Primera sync completa (2026-11-23): 1.293 datasets, 7.694 recursos, 26
  páginas, 26 snapshots RAW, `succeeded`, ~14 s.
- Re-ejecución inmediata: 1.293 leídos, 0 creados, 0 actualizados, 0 cambios, 0
  snapshots nuevos.
- Mecanismo: dedup de snapshots por `content_hash`, upsert por clave natural y
  comparación de `metadata_hash`.

### Fallos parciales

Un `ConnectorError` a mitad de corrida deja el run `partial` con las páginas ya
comiteadas consultables; un proceso muerto deja el run `running` hasta que el
reaper (60 min, `cli.py:59`) lo marca `failed` con
`error_summary="interrupted: run abandoned without finishing (stale run reaper)"`.

## Cómo incorporar una nueva fuente

1. **Verificá el acceso** y completá la ficha de
   [docs/sources/source-inventory.md](../sources/source-inventory.md)
   (ninguna celda inventada: lo no verificado se marca "no verificado").
2. **Registrá la fuente** en `data_source`. Para datos de referencia usamos una
   migración Alembic (ver `7f6c1d2ab9e4`); en local también vale SQL directo:
   ```sql
   INSERT INTO data_source (slug, name, base_url, source_type, jurisdiction_id, license, notes, is_active)
   VALUES ('gba-catalogo', 'Catálogo Provincia de Buenos Aires',
           'https://catalogo.datos.gba.gob.ar', 'ckan', NULL, 'CC-BY-4.0', '…', true);
   ```
3. **Elegí el conector**: si es CKAN, `CkanConnector` ya funciona; la CLI lo
   construye por `source_type`. Para un tipo nuevo (`rest_api`, `dkan`, …),
   implementá el protocolo `SourceConnector` en `data_connectors` y cablealo en
   `cli.py:_build_connector` — el núcleo de ingesta no se modifica (spec S9).
4. **Ejecutá** `uv run datosabiertos ingest sync --source <slug>`.
5. **Verificá**: `GET /api/v1/ingestion-runs?source=<slug>` (estado y
   contadores), `GET /api/v1/sources/<slug>` (último éxito) y los
   `DataQualityCheck` del run.

## Cómo diagnosticar una ingesta fallida

1. `uv run datosabiertos ingest sources` — ¿existe y está activa la fuente?
   (`unknown source` / `is disabled` salen ahí).
2. `GET /api/v1/ingestion-runs?source=<slug>&status=failed` → tomá el run y
   abrí `GET /api/v1/ingestion-runs/{id}`: `error_summary` + `quality_checks`.
3. Log estructurado del CLI (JSON por línea): eventos
   `catalog_sync_connector_error`, `ckan_page_retry_smaller`, `http_retry`,
   `stale_runs_reaped`.
4. Causas frecuentes:
   - **Truncamiento upstream** → reducción de ventana automática; si persiste,
     revisá el tamaño de página configurado.
   - **DNS/timeout** → `UpstreamTransportError` tras agotar reintentos
     (¿portal caído? ver inventario de fuentes).
   - **4xx** → `UpstreamStatusError`, no se reintenta; revisá `base_url`.
   - **Host bloqueado** → `UnsafeUrlError`: la URL no pertenece a la fuente
     configurada o resuelve a IP privada.
   - **Run `running` viejo** → el reaper lo marca `failed` al superar 60 min;
     si el reaper no corrió, ejecutá cualquier `ingest sync` (lo dispara).

Ver también: [arquitectura](overview.md) · [modelo de datos](data-model.md) ·
[ADR-002](../decisions/ADR-002-data-ingestion.md) ·
[inventario de fuentes](../sources/source-inventory.md)
