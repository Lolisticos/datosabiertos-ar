#!/usr/bin/env bash
# First-run bootstrap for a local development environment.
#
# It never touches the network except for the package installs and the optional
# ingestion step, and it never overwrites an existing .env or database.
set -euo pipefail

cd "$(dirname "$0")/.."
export PATH="$HOME/.local/bin:$PATH"

if [[ ! -f .env ]]; then
  cp .env.example .env
  echo "created .env from .env.example"
fi

# shellcheck disable=SC1091
set -a && source .env && set +a

echo "== starting PostgreSQL/PostGIS =="
docker compose up -d db

echo "== waiting for the database =="
for _ in $(seq 1 60); do
  if docker exec datosabiertos-db pg_isready -U "${POSTGRES_USER:-datosabiertos}" \
    -d "${POSTGRES_DB:-datosabiertos}" >/dev/null 2>&1; then
    break
  fi
  sleep 1
done

echo "== installing Python workspace =="
uv sync --all-packages

echo "== applying migrations =="
(cd apps/api && uv run alembic upgrade head)

echo "== creating the test database (idempotent) =="
docker exec datosabiertos-db psql -U "${POSTGRES_USER:-datosabiertos}" -d postgres \
  -tAc "SELECT 1 FROM pg_database WHERE datname = 'datosabiertos_test'" \
  | grep -q 1 \
  || docker exec datosabiertos-db createdb -U "${POSTGRES_USER:-datosabiertos}" datosabiertos_test

echo "== installing web dependencies =="
(cd apps/web && npm install)

cat <<'EOF'

Bootstrap complete.

  make api          # http://localhost:8008/docs
  make web          # http://localhost:3100
  make ingest-ckan  # real metadata ingest from datos.gob.ar
  make test         # backend + frontend checks

EOF
