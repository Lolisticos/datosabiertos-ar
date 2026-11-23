from __future__ import annotations

import asyncio
import socket
from typing import Any

import httpx
import pytest

from datosabiertos_connectors.errors import (
    DownloadTooLargeError,
    UnsafeUrlError,
    UpstreamStatusError,
)
from datosabiertos_connectors.http import HttpPolicy

from .conftest import public_resolver


async def test_transient_failures_are_retried(make_client: Any) -> None:
    attempts: list[int] = []

    async def handler(_request: httpx.Request) -> httpx.Response:
        attempts.append(1)
        if len(attempts) < 3:
            return httpx.Response(503, content=b"unavailable")
        return httpx.Response(200, json={"success": True, "result": {}})

    payload = await make_client(handler).get_json(
        "https://datos.gob.ar/api/3/action/package_search"
    )

    assert payload.payload["success"] is True
    assert len(attempts) == 3


async def test_client_errors_are_not_retried(make_client: Any) -> None:
    attempts: list[int] = []

    async def handler(_request: httpx.Request) -> httpx.Response:
        attempts.append(1)
        return httpx.Response(404, content=b"missing")

    with pytest.raises(UpstreamStatusError):
        await make_client(handler).get_bytes("https://datos.gob.ar/missing.csv")
    assert len(attempts) == 1


async def test_downloads_are_capped_by_content_length(make_client: Any) -> None:
    async def handler(_request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, content=b"x" * 64)

    client = make_client(handler, policy=HttpPolicy(max_bytes=8, requests_per_second=0))
    with pytest.raises(DownloadTooLargeError):
        await client.get_bytes("https://datos.gob.ar/big.csv")


async def test_downloads_are_capped_while_streaming(make_client: Any) -> None:
    async def handler(_request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, content=b"y" * 64, headers={})

    client = make_client(handler, policy=HttpPolicy(max_bytes=8, requests_per_second=0))
    with pytest.raises(DownloadTooLargeError):
        await client.get_bytes("https://datos.gob.ar/streamed.csv")


async def test_redirects_are_followed_only_to_allowed_hosts(make_client: Any) -> None:
    async def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/start":
            return httpx.Response(302, headers={"location": "https://attacker.example/leak"})
        return httpx.Response(200, content=b"secret")

    with pytest.raises(UnsafeUrlError):
        await make_client(handler).get_bytes("https://datos.gob.ar/start")


async def test_redirects_to_allowed_hosts_are_followed(make_client: Any) -> None:
    async def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/start":
            return httpx.Response(302, headers={"location": "https://datos.gob.ar/next"})
        return httpx.Response(200, content=b"ok")

    assert (await make_client(handler).get_bytes("https://datos.gob.ar/start")).content == b"ok"


async def test_redirect_loops_are_bounded(make_client: Any) -> None:
    async def handler(_request: httpx.Request) -> httpx.Response:
        return httpx.Response(302, headers={"location": "https://datos.gob.ar/loop"})

    with pytest.raises(UnsafeUrlError, match="too many redirects"):
        await make_client(handler).get_bytes("https://datos.gob.ar/loop")


async def test_non_json_payloads_are_rejected(make_client: Any) -> None:
    async def handler(_request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, content=b"<html>not json</html>")

    from datosabiertos_connectors.errors import InvalidPayloadError

    with pytest.raises(InvalidPayloadError):
        await make_client(handler).get_json("https://datos.gob.ar/api/3/action/package_search")


async def test_dns_resolution_is_used_when_no_resolver_is_injected(
    make_client: Any, monkeypatch: pytest.MonkeyPatch
) -> None:
    # A host that resolves to a private address must be blocked even when the
    # caller did not inject a resolver. Stub only the operating-system lookup so
    # this test is deterministic in network-restricted CI sandboxes.
    async def fake_getaddrinfo(*_args: object, **_kwargs: object) -> list[tuple[object, ...]]:
        return [
            (socket.AF_INET, socket.SOCK_STREAM, socket.IPPROTO_TCP, "", ("127.0.0.1", 443))
        ]

    monkeypatch.setattr(asyncio.BaseEventLoop, "getaddrinfo", fake_getaddrinfo)
    client = make_client(
        lambda _request: None,  # type: ignore[arg-type]
        allowed_hosts=("localhost",),
    )
    client._resolver = None  # exercise the real DNS path
    with pytest.raises(UnsafeUrlError):
        await client.get_bytes("https://localhost/admin")


async def test_public_resolver_contract() -> None:
    assert await public_resolver("datos.gob.ar", 443) == ["200.16.116.5"]


async def test_gzipped_responses_are_decoded_once(make_client: Any) -> None:
    import gzip

    body = b'{"success": true, "result": {"count": 1, "results": []}}'
    compressed = gzip.compress(body)

    async def handler(_request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            content=compressed,
            headers={"content-encoding": "gzip", "content-type": "application/json"},
        )

    payload = await make_client(handler).get_json(
        "https://datos.gob.ar/api/3/action/package_search"
    )
    assert payload.raw == body
    assert payload.payload["success"] is True


async def test_connection_is_pinned_to_the_validated_address(make_client: Any) -> None:
    seen: list[tuple[str, str, str]] = []

    async def handler(request: httpx.Request) -> httpx.Response:
        seen.append((request.url.host, request.headers["host"], request.url.query.decode()))
        return httpx.Response(200, json={"success": True, "result": {}})

    payload = await make_client(handler).get_json(
        "https://datos.gob.ar/api/3/action/package_search?existing=1",
        params={"rows": 10},
    )

    assert seen == [("200.16.116.5", "datos.gob.ar", "existing=1&rows=10")]
    assert payload.url == "https://datos.gob.ar/api/3/action/package_search?existing=1&rows=10"
