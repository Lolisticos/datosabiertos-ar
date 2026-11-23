# ADR-001: stack tecnológico inicial

- Estado: aceptado
- Fecha: 2026-11-23
- Alcance: Fases 0, 1 y recorrido vertical de Fase 2

## Contexto

DatosAbiertos AR necesita integrar fuentes oficiales heterogéneas, conservar
procedencia e historial y ofrecer un catálogo público. En esta etapa importa
más una base operable y verificable que una arquitectura distribuida.

## Decisión

Se adopta un monorepo con un monolito modular:

- API y CLI en Python 3.13, FastAPI, Pydantic v2, SQLAlchemy 2, Alembic y
  psycopg 3; dependencias y workspace administrados con `uv`.
- Web server-rendered con Next.js App Router, React, TypeScript, Tailwind CSS y
  Zod. No se añade una biblioteca de estado o gráficos sin un caso real.
- PostgreSQL 17 + PostGIS como sistema de registro; `pg_trgm` y una proyección
  normalizada resuelven la búsqueda inicial.
- Docker Compose para desarrollo reproducible; Ruff, mypy, pytest, ESLint,
  TypeScript y Playwright para calidad.

Los módulos de dominio permanecen separados dentro de una sola aplicación. No
se introducen Kubernetes, Kafka, Redis, Celery, Airflow ni microservicios.

## Consecuencias

La solución se despliega y depura con pocas piezas, mantiene transacciones
locales y permite extraer servicios más adelante si existen métricas que lo
justifiquen. A cambio, el escalado inicial es por réplica de la aplicación y la
ingesta se ejecuta como CLI, no mediante una cola distribuida.

## Alternativas descartadas

- Microservicios desde el inicio: aumentan contratos, observabilidad y operación
  sin una carga que lo requiera.
- Elasticsearch/OpenSearch o búsqueda vectorial: PostgreSQL cubre el catálogo
  actual y evita otro sistema de estado.
- SPA con acceso directo a fuentes: rompería el contrato estable de la API y
  expondría al frontend a diferencias entre portales.

