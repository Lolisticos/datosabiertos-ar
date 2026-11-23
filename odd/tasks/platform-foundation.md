# Feature: DatosAbiertos AR platform foundation (Fase 0 + Fase 1 + vertical slice Fase 2)

Alcance de esta ejecución: monorepo ejecutable (API FastAPI + web Next.js + PostgreSQL/PostGIS en Compose), documentación de investigación y decisiones, y un primer recorrido vertical de ingesta de un catálogo oficial CKAN real hasta su exposición en la API y el explorador web.
Fuera de alcance: dashboards con indicadores (Fase 4), IA, autenticación, búsqueda vectorial, microservicios, colas.

## Specs

S1 — Investigación de referencia obligatoria: "El resultado será un documento `docs/research/openarg-benchmark.md`." Debe basarse en evidencia verificable de los repositorios y el sitio de OpenArg, sin afirmar ausencia de funcionalidades sin comprobarla, y sin copiar código ni identidad visual.

S2 — Inventario de fuentes: "Para cada fuente registrar: Organismo. Jurisdicción. URL. Tipo de acceso. Formatos. Licencia y términos. Catálogo disponible. Fecha de última actualización conocida. Frecuencia de publicación, cuando sea verificable. Identificadores territoriales. Restricciones. Calidad observable. Posibilidad de integración." en `docs/sources/source-inventory.md`.

S3 — Stack backend: "Framework: FastAPI.", "Pydantic v2 para validación y esquemas.", "SQLAlchemy 2 para persistencia.", "Alembic para migraciones.", "psycopg 3 para PostgreSQL.", "pytest para pruebas.", "Ruff para lint y formato.", "mypy para validación estática.", "uv para dependencias, entornos y ejecución."

S4 — Stack frontend: "Next.js con App Router + React + TypeScript.", "Tailwind CSS.", "Zod para validaciones de frontend."; sin bibliotecas adicionales cuando el framework alcance ("No utilizar una biblioteca adicional cuando las capacidades nativas del framework sean suficientes.").

S5 — Infraestructura inicial en Compose: "Docker.", "Docker Compose.", "PostgreSQL/PostGIS.", "Backend FastAPI.", "Frontend Next.js."; entorno reproducible; sin Kubernetes, microservicios, Kafka, Airflow, Celery ni Redis.

S6 — Arquitectura: "Adoptar inicialmente un **monolito modular con separación entre API, dominio, persistencia e ingesta de datos**." con módulos `sources`, `catalog`, `ingestion`, `geography`, `indicators`, `data_quality`, `provenance`, `history`, `search`; "Los módulos no deben convertirse en microservicios."

S7 — Entidades mínimas persistentes: Organization, Jurisdiction, DataSource, Dataset, DatasetResource, IngestionRun, ResourceSnapshot, Indicator, IndicatorObservation, DataQualityCheck, DataChange, con "UUID cuando resulte conveniente.", "Restricciones de integridad.", "Migraciones Alembic.", y "Evitar usar `float` para valores monetarios." (valores numéricos con `Numeric`).

S8 — Separación temporal y de dimensiones: "Separación entre fecha de publicación, fecha de observación, fecha de descarga y fecha de procesamiento." y "Diseñar un mecanismo de almacenamiento de observaciones que permita agregar dimensiones sin realizar una migración por cada dataset." (dimensiones en JSONB canónico + hash de dimensiones en la clave única, no una columna por dimensión).

S9 — Contrato de conectores: `SourceConnector` con `discover`, `fetch`, `metadata`; "La interfaz debe permitir incorporar conectores adicionales sin modificar el núcleo de ingesta."; "Empezar por CKAN y una fuente oficial verificable."

S10 — Robustez de ingesta: "Reintentos con backoff.", "Timeouts.", "Manejo de respuestas HTTP erróneas.", "Rate limiting por fuente.", "Paginación.", "Validación de formato.", "Detección de cambios mediante hashes.", "Idempotencia.", "Registro estructurado de ejecuciones.", "Control de tamaño de descargas.", "Protección frente a URLs arbitrarias, SSRF y redirecciones inseguras."

S11 — RAW y NORMALIZED: "Cada descarga debe conservarse como artefacto original siempre que las condiciones de uso lo permitan."; "Registrar qué versión de la transformación produjo cada resultado."; "Mantener la posibilidad de reprocesar datos originales sin volver a descargarlos."

S12 — Historial de cambios: reconocer nuevos recursos, eliminados del catálogo, modificación de contenido, cambio de esquema, cambio de metadatos, fallos y recuperaciones; "Distinguir una modificación efectiva de contenido de una variación de formato o del orden de los registros."

S13 — API de exploración: listado de fuentes, listado y detalle de datasets, filtros, paginación con límites, búsqueda en PostgreSQL (sin Elasticsearch/OpenSearch/vectorial), procedencia e historial de sincronización; "El frontend nunca deberá conocer directamente las estructuras internas de las fuentes originales."

S14 — Primer recorrido funcional (criterio de éxito): "1. Ingresar al sitio. 2. Consultar las fuentes oficiales disponibles. 3. Seleccionar una fuente. 4. Explorar los datasets importados. 5. Abrir el detalle de un dataset. 6. Consultar sus metadatos. 7. Identificar su organismo y URL de origen. 8. Ver la fecha de última sincronización. 9. Consultar el resultado de las validaciones. 10. Abrir una visualización real cuando el dataset sea compatible." y "desde el entorno de desarrollo deberá poder ejecutarse una ingesta y verificar que los datos quedan registrados correctamente."

S15 — Seguridad mínima: "Configuración mediante variables de entorno.", "CORS restringido.", "Límites de paginación.", "Protección SSRF.", "Manejo centralizado de excepciones.", "Respuestas sin filtración de información sensible.", "Los conectores deben utilizar fuentes previamente configuradas y autorizadas.", "No habilitar la descarga arbitraria de URLs proporcionadas por usuarios anónimos."

S16 — Calidad y CI: tests unitarios, de integración, de conectores con fixtures/mocks, de endpoints, de idempotencia, de detección de cambios, de migraciones; CI con lint, type checking, tests backend, tests frontend y build; "No afirmar que una prueba pasó si no se ejecutó realmente."

S17 — Documentación mínima ejecutable: `README.md`, `docs/architecture/overview.md`, `docs/architecture/data-model.md`, `docs/architecture/ingestion.md`, `docs/research/openarg-benchmark.md`, `docs/sources/source-inventory.md`, `docs/development/local-setup.md`, `docs/decisions/ADR-001-technology-stack.md`, `docs/decisions/ADR-002-data-ingestion.md`; sin documentación que no refleje la implementación real.

S18 — No fabricar datos: "No utilizar datos ficticios como si fueran información pública real."; "Nunca inventar indicadores para completar visualmente una pantalla."; mostrar cobertura y disponibilidad real.

S19 — Repositorio: reutilizar `Lolisticos/datosabiertos-ar`; "No crear repositorios duplicados."; "No eliminar ni sobrescribir archivos existentes sin inspeccionarlos."

## Tasks

| ID | Tarea | Specs | Ruta | Commit |
| --- | --- | --- | --- | --- |
| T1 | Investigación: benchmark OpenArg + inventario de fuentes oficiales | S1, S2 | inline + explore | (docs slice) |
| T2 | Scaffold monorepo, ADRs, .env.example, Makefile, pyproject/uv, lint y type config | S3, S17, S19 | inline | wu1 |
| T3 | Modelo de datos SQLAlchemy + migración Alembic inicial + Compose PostGIS | S6, S7, S8, S5 | inline | wu2 |
| T4 | Núcleo de ingesta: contrato de conectores, storage RAW, SSRF guard, reintentos, hashing, ejecuciones | S9, S10, S11 | inline | wu3 |
| T5 | Conector CKAN + tests con fixtures | S9, S10, S16 | inline | wu3 |
| T6 | Servicio de ingesta (discover/sync de catálogo, idempotencia, DataChange) + CLI | S10, S11, S12 | inline | wu4 |
| T7 | API de exploración (fuentes, datasets, detalle, ejecuciones, calidad, historial, search, health) + tests | S13, S14, S15 | inline | wu5 |
| T8 | Ingesta real de datos.gob.ar y verificación en base | S10, S14, S18 | inline | wu5 |
| T9 | Frontend Next.js: home, fuentes, explorador, detalle, historial, estados vacío/error | S4, S14, S18 | inline | wu6 |
| T10 | Tests de frontend (typecheck, lint, build) + Playwright del recorrido | S4, S16 | inline | wu6 |
| T11 | CI GitHub Actions + documentación final (arquitectura, modelo, ingesta, local-setup, README) | S17, S16 | inline | wu7 |
| T12 | Verificación final integral y reporte | S14, S16 | inline | — |

## Log

L1 (usuario, verbatim): "# PROMPT MAESTRO — DATOSABIERTOS AR ... Objetivo final de esta ejecución: dejar establecidos los cimientos técnicos de DatosAbiertos AR y demostrar que puede obtener, almacenar y exponer información oficial verificable de Argentina. No busco una copia de OpenArg. Busco desarrollar una plataforma argentina de datos públicos con una arquitectura propia, un sistema de ingesta sólido, dashboards útiles, trazabilidad histórica y capacidad real de crecimiento." (prompt completo de 21 secciones, ver sesión; instrucción de ejecución: "Comenzá inmediatamente con la investigación, preparación e implementación de las fases 0 y 1. Después, si el entorno y las dependencias están disponibles, continuá con un primer recorrido vertical de la fase 2: descubrimiento de un catálogo oficial CKAN, recuperación de metadatos, almacenamiento y consulta mediante API. No implementes toda la visión del producto en una única entrega.")

L2 (evidencia, entorno): repo `Lolisticos/datosabiertos-ar` con un único commit `db161ad Initial commit` y README de 3 líneas; rama `main` limpia. Toolchain host: Python 3.14.4 (+ uv 0.13.9 instalado), Node 22.22.1, npm 9.2.0, Docker 29 con Compose 2.40, gh autenticado. Sin `psql` en host: la base corre en Compose. Puertos libres elegidos: 8008 (API), 3100 (web), 55437 (Postgres), para no colisionar con servicios ya escuchando en 3001/3002/3003/5432.

L3 (evidencia, fuentes verificadas 2026-11-23): `datos.gob.ar/api/3/action/package_search` HTTP 200, 1293 datasets, organización ejemplo "Secretaría de Minería", recursos CSV con licencia CC-BY 4.0. CKAN operativos: datos.gob.ar (1293), catalogo.datos.gba.gob.ar (105), datosabiertos.mendoza.gov.ar (204), data.buenosaires.gob.ar (463). `apis.datos.gob.ar/series/api/series` responde series reales (EMAE, frecuencia mensual) con metadatos de catálogo/dataset/distribución. No operativos como CKAN desde este entorno: datos.santafe.gob.ar (responde HTTP/0.9, servidor antiguo), datos.rosario.gob.ar (timeout de conexión), datosgestionabierta.cba.gov.ar (404) y gobiernoabierto.cordoba.gob.ar (404 en /api/v2/datasets, portal sin API CKAN).

L4 (decisión): fuente de la primera integración real = catálogo CKAN nacional `datos.gob.ar` (mayor cobertura, API oficial documentada, licencia abierta). Metadata-only en esta fase: no se importan tablas de recursos heterogéneos.

L5 (evidencia, infraestructura): PostGIS `postgis/postgis:17-3.5` en Compose, PostgreSQL 17.5. Puertos definitivos API 8008, web 3100, Postgres 55437 (el 55432 estaba ocupado por otro servicio del host; verificado con bind de socket antes de elegir).

L6 (evidencia, ingesta real 2026-11-23): primera sincronización completa de `datos.gob.ar` → 1293 datasets, 7694 recursos, 38 organismos, 26 páginas de catálogo, 26 snapshots RAW, estado `succeeded`, sin errores. Segunda ejecución inmediata → 1293 leídos, 0 creados, 0 actualizados, 0 cambios, 0 snapshots nuevos: idempotencia verificada. Tercera ejecución con `search_text` reindexado (1293 filas).

L7 (restricciones reales del upstream descubiertas, no documentadas por el portal): `package_search` con `rows=100` devuelve una respuesta truncada (`RemoteProtocolError`, ~1,3 MB esperados) — se usa `page_size=50` con reducción automática de ventana hasta 10 elementos; algunos recursos CKAN no tienen `url` y se omiten con warning sin perder la página; `sort=metadata_modified desc` produce duplicados/faltantes mientras el catálogo cambia, se usa `sort=name asc` estable más deduplicación defensiva por `external_id`.

L8 (decisión, búsqueda): la búsqueda usa una proyección `dataset.search_text` sin acentos y en minúsculas, mantenida por la aplicación, con índices GIN/pg_trgm. Motivo: la función `unaccent` de PostgreSQL no es IMMUTABLE y no puede indexarse directamente; el usuario argentino escribe tanto "educacion" como "educación". Backfill operativo: `datosabiertos catalog reindex-search`.

L9 (decisión, alcance de dashboards): no se incorporan ECharts, MapLibre ni TanStack Query en esta fase porque todavía no existen indicadores con observaciones verificadas; el endpoint `/datasets/{id}/visualization` declara `available=false` con el motivo real en lugar de dibujar un gráfico vacío.

L10 (frontend): recorrido server-rendered implementado en Next.js para portada, fuentes, explorador con filtros, detalle con procedencia/validaciones, historial de ingestas y estados vacío/error. Zod valida todos los contratos recibidos de la API; no se agregaron bibliotecas de estado ni visualización sin necesidad.

L11 (Compose): la web usa `http://api:8000` como URL server-side dentro de la red de Compose y espera el healthcheck de la API. El desarrollo nativo conserva `http://localhost:8008`. Esto evita que `localhost` dentro del contenedor web apunte al propio contenedor.

L12 (verificación final ejecutada 2026-11-23): `make check` pasó Ruff y mypy en conectores/API, ESLint y TypeScript en web, 42 tests de conectores, 26 tests de API y build de producción Next.js. Playwright pasó 3/3 recorridos contra la API y el catálogo real: navegación completa hasta detalle/procedencia, búsqueda con estado vacío e historial con detalle de ejecución. La cadena Alembic completa también pasó `downgrade base` + `upgrade head` sobre `datosabiertos_test`.

L13 (estado): T1–T12 completadas dentro del alcance declarado. Quedan deliberadamente fuera de esta entrega los dashboards/indicadores, importación masiva del contenido tabular de recursos, IA, autenticación y arquitectura distribuida.
