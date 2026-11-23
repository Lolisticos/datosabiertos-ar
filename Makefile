# DatosAbiertos AR — Makefile
#
# Development helpers. Containers use ports 8008/3100/55437 so they do not
# collide with other local services.

SHELL := /bin/bash
COMPOSE := docker compose
UV := uv
API_DIR := apps/api
WEB_DIR := apps/web
TEST_DB_URL ?= postgresql+psycopg://datosabiertos:datosabiertos@localhost:55437/datosabiertos_test

.PHONY: help env up down logs ps build db api web migrate revision \
	ingest-ckan ingest-sources sync test test-backend test-frontend test-e2e \
	lint typecheck check clean test-db

help:
	@echo "DatosAbiertos AR"
	@echo ""
	@echo "  make env              Create .env from .env.example if missing"
	@echo "  make up               Start PostgreSQL/PostGIS + API + web (Docker Compose)"
	@echo "  make down             Stop containers"
	@echo "  make logs             Follow container logs"
	@echo "  make db               Start only PostgreSQL/PostGIS"
	@echo "  make migrate          Apply Alembic migrations to the dev database"
	@echo "  make revision m=...   Autogenerate a new Alembic revision"
	@echo "  make api              Run the API natively with uv (reload)"
	@echo "  make web              Run the web app natively with npm"
	@echo "  make ingest-ckan      Sync the national CKAN catalogue (datos.gob.ar)"
	@echo "  make test             Backend + frontend checks"
	@echo "  make test-e2e         Playwright against running API + populated DB"
	@echo "  make lint             Ruff + ESLint"
	@echo "  make typecheck        mypy + tsc"
	@echo "  make check            lint + typecheck + tests + web build"

env:
	@test -f .env || (cp .env.example .env && echo "created .env")

up: env
	$(COMPOSE) up -d --build db api web

down:
	$(COMPOSE) down

logs:
	$(COMPOSE) logs -f --tail=100

ps:
	$(COMPOSE) ps

build:
	$(COMPOSE) build

db: env
	$(COMPOSE) up -d db

migrate:
	cd $(API_DIR) && $(UV) run alembic upgrade head

revision:
	cd $(API_DIR) && $(UV) run alembic revision --autogenerate -m "$(m)"

ingest-ckan: env
	cd $(API_DIR) && $(UV) run datosabiertos ingest sync --source datos-gob-ar

api: env
	cd $(API_DIR) && $(UV) run uvicorn datosabiertos.main:app --reload --port 8008

web:
	cd $(WEB_DIR) && npm run dev

test-db: env
	-docker exec datosabiertos-db psql -U datosabiertos -d postgres -c "CREATE DATABASE datosabiertos_test"

test: test-backend test-frontend

test-backend: env
	cd packages/data_connectors && $(UV) run pytest -q
	cd $(API_DIR) && DATOSABIERTOS_TEST_DATABASE_URL=$(TEST_DB_URL) $(UV) run pytest -q

test-frontend:
	cd $(WEB_DIR) && npm run typecheck && npm run lint

test-e2e:
	cd $(WEB_DIR) && npm run test:e2e

lint:
	cd packages/data_connectors && $(UV) run ruff check src tests
	cd $(API_DIR) && $(UV) run ruff check src tests
	cd $(WEB_DIR) && npm run lint

typecheck:
	cd packages/data_connectors && $(UV) run mypy src
	cd $(API_DIR) && $(UV) run mypy src
	cd $(WEB_DIR) && npm run typecheck

check: lint typecheck test-frontend test-backend
	cd $(WEB_DIR) && npm run build

clean:
	$(COMPOSE) down -v
	rm -rf apps/web/.next apps/web/node_modules
