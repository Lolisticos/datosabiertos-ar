from __future__ import annotations

import json
from collections.abc import Awaitable, Callable
from pathlib import Path
from typing import Any

import httpx
import pytest

from datosabiertos_connectors.http import HttpPolicy, SafeHttpClient

FIXTURES = Path(__file__).parent / "fixtures"


def load_fixture(name: str) -> dict[str, Any]:
    return json.loads((FIXTURES / name).read_text(encoding="utf-8"))


async def public_resolver(_host: str, _port: int) -> list[str]:
    """Deterministic stand-in for DNS: every test host is a public address."""
    return ["200.16.116.5"]


Handler = Callable[[httpx.Request], Awaitable[httpx.Response]]


@pytest.fixture
def make_client() -> Callable[..., SafeHttpClient]:
    def factory(
        handler: Handler, *, allowed_hosts: tuple[str, ...] = ("datos.gob.ar",), **kwargs: Any
    ) -> SafeHttpClient:
        policy: HttpPolicy = kwargs.pop(
            "policy",
            HttpPolicy(
                retry_attempts=3,
                retry_initial_wait=0.0,
                retry_max_wait=0.0,
                requests_per_second=0,
            ),
        )
        return SafeHttpClient(
            user_agent="DatosAbiertosAR-Test/0.1",
            allowed_hosts=allowed_hosts,
            policy=policy,
            transport=httpx.MockTransport(handler),
            resolver=public_resolver,
            **kwargs,
        )

    return factory
