# Entorno local

## Requisitos

- Docker 29+ con Compose 2
- `uv` 0.13.9 y Python 3.13
- Node.js 22 y npm 9+

Los puertos por defecto son 55437 (PostgreSQL), 8008 (API) y 3100 (web).

## Bootstrap recomendado

```bash
cp .env.example .env
./scripts/dev-bootstrap.sh
make api   # terminal 1
make web   # terminal 2
```

El script inicia PostgreSQL/PostGIS, sincroniza dependencias, aplica migraciones
y crea la base de integración. API: `http://localhost:8008/docs`; web:
`http://localhost:3100`.

Para ejecutar todo en contenedores:

```bash
cp .env.example .env
make up
```

Dentro de Compose, la web usa `http://api:8000`; `localhost:8008` se reserva
para procesos nativos y el navegador.

## Cargar y comprobar el catálogo

```bash
make ingest-ckan
cd apps/api
uv run datosabiertos check
```

La ingesta puede repetirse: un catálogo equivalente no crea datasets, cambios
ni snapshots duplicados.

## Calidad

```bash
make check       # lint, tipos, 68 tests y build web
make test-e2e    # requiere API activa y base de desarrollo poblada
```

Para comprobar migraciones sin tocar datos de desarrollo:

```bash
cd apps/api
DATOSABIERTOS_DATABASE_URL="$DATOSABIERTOS_TEST_DATABASE_URL" uv run alembic downgrade base
DATOSABIERTOS_DATABASE_URL="$DATOSABIERTOS_TEST_DATABASE_URL" uv run alembic upgrade head
```

## Operación habitual

```bash
make migrate
make logs
make ps
make down
```

Los artefactos RAW y `.env` son locales y están excluidos de Git. Nunca use la
base de desarrollo para probar un `downgrade base`.

