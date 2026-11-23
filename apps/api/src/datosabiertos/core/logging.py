"""Structured logging configuration.

Logs are JSON in production (machine readable, no credential leakage) and a
readable console renderer in development.
"""

from __future__ import annotations

import logging
import sys
import uuid
from collections.abc import Iterator, Mapping, MutableMapping
from contextlib import contextmanager
from contextvars import ContextVar
from typing import Any

import structlog

_request_id: ContextVar[str | None] = ContextVar("request_id", default=None)


def current_request_id() -> str | None:
    return _request_id.get()


@contextmanager
def request_context(request_id: str | None = None) -> Iterator[str]:
    """Attach a request id to every log line produced inside the block."""
    value = request_id or uuid.uuid4().hex
    token = _request_id.set(value)
    try:
        yield value
    finally:
        _request_id.reset(token)


def _add_request_id(
    _logger: Any, _method: str, event_dict: MutableMapping[str, Any]
) -> Mapping[str, Any]:
    request_id = _request_id.get()
    if request_id is not None:
        event_dict.setdefault("request_id", request_id)
    return event_dict


def configure_logging(level: str = "INFO", *, json_logs: bool = True) -> None:
    numeric_level = getattr(logging, level.upper(), logging.INFO)
    logging.basicConfig(format="%(message)s", stream=sys.stdout, level=numeric_level, force=True)
    for noisy in ("httpx", "httpcore"):
        logging.getLogger(noisy).setLevel(logging.WARNING)

    renderer: structlog.types.Processor = (
        structlog.processors.JSONRenderer()
        if json_logs
        else structlog.dev.ConsoleRenderer(colors=False)
    )
    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            _add_request_id,
            structlog.processors.add_log_level,
            structlog.processors.TimeStamper(fmt="iso", utc=True),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            renderer,
        ],
        wrapper_class=structlog.make_filtering_bound_logger(numeric_level),
        logger_factory=structlog.PrintLoggerFactory(),
        cache_logger_on_first_use=True,
    )


def get_logger(name: str) -> structlog.stdlib.BoundLogger:
    return structlog.get_logger(name)  # type: ignore[no-any-return]
