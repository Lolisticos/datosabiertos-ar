"""Centralized HTTP error handling.

Clients only ever see a stable, non-sensitive error envelope; internals (SQL,
stack traces, upstream payloads) stay in the logs.
"""

from __future__ import annotations

from typing import Any

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from .logging import current_request_id, get_logger

logger = get_logger(__name__)


class ApiError(Exception):
    """Base class for expected API failures with a safe public message."""

    status_code: int = status.HTTP_400_BAD_REQUEST
    code: str = "api_error"

    def __init__(self, message: str, *, details: dict[str, Any] | None = None) -> None:
        super().__init__(message)
        self.message = message
        self.details = details or {}


class NotFoundError(ApiError):
    status_code = status.HTTP_404_NOT_FOUND
    code = "not_found"


class ConflictError(ApiError):
    status_code = status.HTTP_409_CONFLICT
    code = "conflict"


def _envelope(code: str, message: str, details: dict[str, Any] | None = None) -> dict[str, Any]:
    body: dict[str, Any] = {"error": {"code": code, "message": message}}
    if details:
        body["error"]["details"] = details
    request_id = current_request_id()
    if request_id:
        body["error"]["request_id"] = request_id
    return body


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(ApiError)
    async def _handle_api_error(_request: Request, exc: ApiError) -> JSONResponse:
        logger.info("api_error", code=exc.code, status_code=exc.status_code)
        return JSONResponse(
            status_code=exc.status_code, content=_envelope(exc.code, exc.message, exc.details)
        )

    @app.exception_handler(RequestValidationError)
    async def _handle_validation_error(
        _request: Request, exc: RequestValidationError
    ) -> JSONResponse:
        details = {
            "fields": [
                {"location": ".".join(str(part) for part in error["loc"]), "message": error["msg"]}
                for error in exc.errors()
            ]
        }
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content=_envelope("validation_error", "Parámetros inválidos.", details),
        )

    @app.exception_handler(StarletteHTTPException)
    async def _handle_http_error(_request: Request, exc: StarletteHTTPException) -> JSONResponse:
        return JSONResponse(
            status_code=exc.status_code,
            content=_envelope("http_error", str(exc.detail)),
        )

    @app.exception_handler(Exception)
    async def _handle_unexpected(_request: Request, exc: Exception) -> JSONResponse:
        logger.exception("unhandled_exception", error_type=type(exc).__name__)
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content=_envelope("internal_error", "Error interno del servidor."),
        )
