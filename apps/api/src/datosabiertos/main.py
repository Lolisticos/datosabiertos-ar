"""FastAPI application factory."""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response
from starlette.middleware.base import RequestResponseEndpoint

from . import __version__
from .api.router import api_router
from .api.schemas.common import ApiInfo
from .core.config import Settings, get_settings
from .core.errors import register_exception_handlers
from .core.logging import configure_logging, get_logger, request_context
from .db.session import dispose_engine

logger = get_logger(__name__)

DESCRIPTION = """
API pública de **DatosAbiertos AR**.

Expone el catálogo normalizado de fuentes oficiales argentinas, su procedencia
(organismo, fuente, URL de origen), el historial de sincronizaciones y los
resultados de validación de cada ingesta.

Toda cifra o metadato publicado aquí puede rastrearse hasta el artefacto original
descargado de la fuente oficial. Esta fase publica metadatos de catálogo; las
observaciones estadísticas se incorporan cuando exista un indicador verificado.
"""


def create_app(settings: Settings | None = None) -> FastAPI:
    config = settings or get_settings()
    configure_logging(config.log_level, json_logs=config.is_production)

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        logger.info(
            "api_started",
            version=__version__,
            environment=config.environment,
            api_prefix=config.api_v1_prefix,
        )
        yield
        await dispose_engine()
        logger.info("api_stopped")

    app = FastAPI(
        title="DatosAbiertos AR API",
        description=DESCRIPTION,
        version=__version__,
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
        lifespan=lifespan,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=config.cors_origin_list,
        allow_credentials=False,
        allow_methods=["GET"],
        allow_headers=["Accept", "Content-Type"],
        max_age=600,
    )

    @app.middleware("http")
    async def add_request_context(request: Request, call_next: RequestResponseEndpoint) -> Response:
        with request_context(request.headers.get("x-request-id")):
            logger.debug("request", method=request.method, path=request.url.path)
            response = await call_next(request)
            response.headers["X-Request-ID"] = request.headers.get("x-request-id") or ""
            return response

    register_exception_handlers(app)
    app.include_router(api_router, prefix=config.api_v1_prefix)

    @app.get("/", response_model=ApiInfo, tags=["meta"], summary="Service information")
    async def root() -> ApiInfo:
        return ApiInfo(
            name="DatosAbiertos AR API",
            version=__version__,
            environment=config.environment,
            docs_url="/docs",
            openapi_url="/openapi.json",
            coverage_note=(
                "Cobertura de esta fase: metadatos de catálogos oficiales; no se publican "
                "indicadores estadísticos sin observaciones verificadas."
            ),
        )

    return app


app = create_app()
