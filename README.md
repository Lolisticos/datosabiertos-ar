# DatosAbiertos AR

Plataforma argentina de datos públicos abiertos. Obtiene, preserva y expone
información oficial verificable con trazabilidad histórica completa: cada cifra
y metadato publicado puede rastrearse hasta el artefacto original descargado de
la fuente oficial.

Monorepo: API FastAPI + app web Next.js + PostgreSQL/PostGIS, orquestados con
Docker Compose. Estado del repositorio: rama `feat/platform-foundation` (Fase 0
+ Fase 1 + primer recorrido vertical de Fase 2, según
`odd/tasks/platform-foundation.md`).

## Cobertura real al 2026-11-23

Verificado contra la base de datos de desarrollo y la API en vivo:

| Magnitud | Valor |
| --- | --- |
| Fuente integrada | Catálogo Nacional de Datos Abiertos (`datos.gob.ar`, CKAN) |
| Datasets | 1.293 |
| Recursos (distribuciones) | 7.694 |
| Organismos | 38 |
| Temas | 13 |
| Snapshots RAW preservados | 42 (todos `catalog_payload`) |
| Primera sincronización completa | 1.293 datasets en 26 páginas, ~14 s, estado `succeeded` |
| Re-ejecución inmediata | 0 creados, 0 actualizados, 0 cambios, 0 snapshots nuevos (idempotencia) |

Esta fase publica **metadatos de catálogo** (título, descripción, organismo,
licencia, formatos, URL de origen, fechas). No se importaron todavía las tablas
de datos de cada recurso (alcance metadata-only, ver
[ADR-002](docs/decisions/ADR-002-data-ingestion.md)).

## Arquitectura en una mirada

Monolito modular: una sola API y un solo proceso de ingesta (CLI), con módulos
de dominio aislados (`sources`, `catalog`, `ingestion`, `jurisdictions`,
`organizations`, `provenance`, `quality`, `history`, `indicators`, `search`).
Sin microservicios, sin colas, sin Kubernetes: la simplicidad es una decisión
deliberada.

```
┌────────────┐   HTTP/JSON   ┌──────────────────────────────────────┐
│  apps/web  │ ────────────▶ │            apps/api (FastAPI)        │
│  (Next.js) │               │  api/ → modules/ → db/ (async)       │
└────────────┘               └───────┬───────────────────┬──────────┘
                                     │ SQL (psycopg 3)   │ RAW fs
                              ┌──────▼──────┐     ┌──────▼─────────┐
                              │ PostgreSQL  │     │ data/storage/  │
                              │ 17 +PostGIS │     │ (snapshots RAW)│
                              └─────────────┘     └────────────────┘
```

Detalle completo en [docs/architecture/overview.md](docs/architecture/overview.md).

## Estructura del repositorio

```
apps/api                  API FastAPI + CLI `datosabiertos` (uv workspace)
  src/datosabiertos/api/      routers, schemas, mappers, deps
  src/datosabiertos/modules/  un módulo por dominio
  src/datosabiertos/db/       base, sesión, registro de modelos
  src/datosabiertos/core/     config, logging, errores, texto
  alembic/                    migraciones (head: 5b1e2c9d7a10)
apps/web                  app Next.js: catálogo, fuentes, detalle e historial
packages/data_connectors  conectores de fuentes (CKAN hoy), paquete independiente
infra/docker              Dockerfile.api, Dockerfile.web
docs/                     arquitectura, decisiones, investigación, fuentes, desarrollo
scripts/dev-bootstrap.sh  aprovisionamiento inicial idempotente
odd/tasks/                especificación y log de la ejecución (ODD)
```

## Inicio rápido

Requisitos: Docker con Compose, [uv](https://docs.astral.sh/uv/) 0.13.9
(gestiona Python 3.13), y Node 22 + npm 9 para la app web.

### Opción A — script de bootstrap

```bash
./scripts/dev-bootstrap.sh   # .env + db + uv sync + migraciones + db de test
```

### Opción B — todo en contenedores

```bash
cp .env.example .env
make up          # db + api + web (Compose)
```

### Opción C — nativo (desarrollo)

```bash
cp .env.example .env
docker compose up -d db
uv sync --all-packages
make migrate     # alembic upgrade head
make api         # http://localhost:8008  (uvicorn --reload)
make web         # http://localhost:3100
```

Puertos elegidos para no colisionar con otros servicios locales: API **8008**,
web **3100**, PostgreSQL **55437** (configurables en `.env`).

## Comandos de operador

```bash
cd apps/api
uv run datosabiertos ingest sources                     # fuentes configuradas
uv run datosabiertos ingest sync --source datos-gob-ar  # sincronizar catálogo
uv run datosabiertos catalog reindex-search             # reconstruir proyección de búsqueda
uv run datosabiertos check                              # verificación de DB y storage
```

Alias de Makefile: `make ingest-ckan` (sync de datos.gob.ar), `make migrate`,
`make revision m="descripción"`, `make test`, `make lint`, `make typecheck`,
`make check` y `make test-e2e` (requiere API y catálogo local en ejecución). El
CLI solo opera contra fuentes registradas en la base; nunca
acepta una URL arbitraria (ver
[docs/architecture/ingestion.md](docs/architecture/ingestion.md)).

## API

Documentación interactiva en `/docs` (Swagger) y `/redoc`; esquema en
`/openapi.json`. Raíz de la API: `/api/v1`. Solo lectura (GET), paginación
acotada (`page_size` ≤ 100), CORS restringido al origen del frontend.

| Endpoint | Descripción |
| --- | --- |
| `GET /api/v1/health`, `/health/ready` | Liveness y readiness (DB + storage) |
| `GET /api/v1/sources`, `/sources/{slug}` | Fuentes configuradas y su último estado |
| `GET /api/v1/datasets` | Búsqueda con filtros (`q`, `source`, `topic`, `format`, `organization_id`, `jurisdiction_id`, `updated_since`) |
| `GET /api/v1/search` | Alias de búsqueda con `q` obligatorio |
| `GET /api/v1/facets`, `/datasets/filters` | Opciones de filtrado con conteos |
| `GET /api/v1/datasets/{id}` | Detalle con procedencia y validaciones |
| `GET /api/v1/datasets/{id}/changes` | Historial de cambios del dataset |
| `GET /api/v1/datasets/{id}/visualization` | Disponibilidad real de visualización |
| `GET /api/v1/stats/overview` | Cobertura del catálogo |
| `GET /api/v1/ingestion-runs`, `/ingestion-runs/{id}` | Historial de ejecuciones y sus chequeos |
| `GET /api/v1/changes` | Cambios detectados recientes |

Las respuestas y ejemplos reales están en `/docs`. La app web se sirve de esta
API; nunca accede a las estructuras internas de las fuentes originales.

## Lo que NO está implementado en esta fase

- **Dashboards con indicadores y visualizaciones estadísticas** (Fase 4): las
  tablas `indicator`/`indicator_observation` existen, pero no hay indicadores
  cargados ni gráficos publicados.
- **IA / agentes / LLM**: no hay dependencia de modelos pagos ni embeddings en
  el núcleo.
- **Autenticación y usuarios**: la API es pública de solo lectura.
- **Motor de búsqueda dedicado**: la búsqueda usa PostgreSQL (`ILIKE` + pg_trgm
  sobre una proyección sin acentos), sin Elasticsearch/OpenSearch/pgvector.
- **Importación de tablas de datos** (contenido de los recursos): alcance
  metadata-only; el recorrido `fetch()` de recursos está implementado pero no
  se ejecuta masivamente.
- **Visualizaciones de recursos**: la app web informa la disponibilidad real,
  pero no dibuja gráficos hasta que exista contenido tabular compatible y
  verificable; hoy el recorrido integrado es de metadatos.

## Verificación ejecutada

El cierre de esta fase ejecutó Ruff, mypy, ESLint, TypeScript, 42 tests del
paquete de conectores, 26 tests de API, el build de producción de Next.js y 3
recorridos Playwright contra el catálogo real. `make check` y
`make test-e2e` permiten repetir esas validaciones; el segundo requiere los
servicios y la base poblada.

## Documentación

- [docs/architecture/overview.md](docs/architecture/overview.md) — arquitectura y flujos
- [docs/architecture/data-model.md](docs/architecture/data-model.md) — modelo de datos
- [docs/architecture/ingestion.md](docs/architecture/ingestion.md) — sistema de ingesta
- [docs/decisions/ADR-001-technology-stack.md](docs/decisions/ADR-001-technology-stack.md) — stack
- [docs/decisions/ADR-002-data-ingestion.md](docs/decisions/ADR-002-data-ingestion.md) — ingesta
- [docs/research/openarg-benchmark.md](docs/research/openarg-benchmark.md) — benchmark OpenArg
- [docs/sources/source-inventory.md](docs/sources/source-inventory.md) — inventario de fuentes
- [docs/development/local-setup.md](docs/development/local-setup.md) — entorno local
