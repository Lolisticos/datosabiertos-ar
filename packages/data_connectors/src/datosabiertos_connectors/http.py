"""Bounded, safe HTTP access for connectors.

Wraps ``httpx.AsyncClient`` with the platform defaults that every connector must
share: timeouts, exponential-backoff retries for transient failures, a per-host
rate limit, a hard byte cap, and manual redirect handling so each hop is
validated by the SSRF guard.
"""

from __future__ import annotations

import asyncio
import json
import time
from collections.abc import Awaitable, Callable, Iterable, Mapping
from dataclasses import dataclass
from datetime import UTC, datetime
from email.utils import parsedate_to_datetime
from typing import Any

import httpx
import structlog
from tenacity import AsyncRetrying, RetryCallState, retry_if_exception_type, wait_exponential_jitter

from .errors import (
    DownloadTooLargeError,
    InvalidPayloadError,
    RetryableUpstreamError,
    UnsafeUrlError,
    UpstreamStatusError,
    UpstreamTransportError,
)
from .ssrf import ResolvedOutboundUrl, resolve_outbound_url

logger = structlog.get_logger(__name__)

Resolver = Callable[[str, int], Awaitable[list[str]]]

_REDIRECT_STATUSES = frozenset({301, 302, 303, 307, 308})
_RETRYABLE_STATUSES = frozenset({408, 425, 429, 500, 502, 503, 504})


@dataclass(frozen=True)
class HttpPolicy:
    timeout_seconds: float = 30.0
    max_bytes: int = 50 * 1024 * 1024
    max_redirects: int = 3
    retry_attempts: int = 3
    retry_initial_wait: float = 0.5
    retry_max_wait: float = 8.0
    requests_per_second: float = 4.0
    allow_http: bool = False

    def __post_init__(self) -> None:
        if self.timeout_seconds <= 0:
            raise ValueError("timeout_seconds must be positive")
        if self.max_bytes <= 0:
            raise ValueError("max_bytes must be positive")
        if self.retry_attempts < 1:
            raise ValueError("retry_attempts must be at least 1")


@dataclass(frozen=True)
class JsonPayload:
    payload: Mapping[str, Any]
    raw: bytes
    status_code: int
    url: str
    fetched_at: datetime


@dataclass(frozen=True)
class BytesPayload:
    content: bytes
    media_type: str | None
    source_last_modified: datetime | None
    status_code: int
    url: str
    fetched_at: datetime

    @property
    def size(self) -> int:
        return len(self.content)


class _RateLimiter:
    """Minimal per-host token spacing limiter (no external dependency)."""

    def __init__(
        self, requests_per_second: float, *, clock: Callable[[], float] = time.monotonic
    ) -> None:
        self._interval = 0.0 if requests_per_second <= 0 else 1.0 / requests_per_second
        self._clock = clock
        self._next_allowed: dict[str, float] = {}
        self._lock = asyncio.Lock()

    async def acquire(self, host: str) -> None:
        if self._interval <= 0:
            return
        async with self._lock:
            now = self._clock()
            wait_for = self._next_allowed.get(host, 0.0) - now
            if wait_for > 0:
                await asyncio.sleep(wait_for)
                now = self._clock()
            self._next_allowed[host] = now + self._interval


class SafeHttpClient:
    """HTTP client shared by every connector."""

    def __init__(
        self,
        *,
        user_agent: str,
        allowed_hosts: Iterable[str],
        policy: HttpPolicy | None = None,
        transport: httpx.AsyncBaseTransport | None = None,
        resolver: Resolver | None = None,
    ) -> None:
        self._policy = policy or HttpPolicy()
        self._allowed_hosts = tuple(sorted({host.lower() for host in allowed_hosts}))
        if not self._allowed_hosts:
            raise ValueError("at least one allowed host is required")
        self._resolver = resolver
        self._rate_limiter = _RateLimiter(self._policy.requests_per_second)
        self._client = httpx.AsyncClient(
            follow_redirects=False,
            timeout=httpx.Timeout(self._policy.timeout_seconds),
            headers={
                "User-Agent": user_agent,
                "Accept-Encoding": "gzip, deflate",
            },
            transport=transport,
        )

    async def __aenter__(self) -> SafeHttpClient:
        return self

    async def __aexit__(self, *_: object) -> None:
        await self.aclose()

    async def aclose(self) -> None:
        await self._client.aclose()

    async def get_json(
        self, url: str, *, params: Mapping[str, str | int | float | bool] | None = None
    ) -> JsonPayload:
        response = await self._get(url, params=params)
        try:
            payload = json.loads(response.content)
        except json.JSONDecodeError as exc:
            raise InvalidPayloadError(f"response from {response.url} is not valid JSON") from exc
        if not isinstance(payload, dict):
            raise InvalidPayloadError(f"response from {response.url} is not a JSON object")
        return JsonPayload(
            payload=payload,
            raw=response.content,
            status_code=response.status_code,
            url=str(response.url),
            fetched_at=datetime.now(UTC),
        )

    async def get_bytes(self, url: str) -> BytesPayload:
        response = await self._get(url)
        return BytesPayload(
            content=response.content,
            media_type=response.headers.get("content-type"),
            source_last_modified=_parse_http_date(response.headers.get("last-modified")),
            status_code=response.status_code,
            url=str(response.url),
            fetched_at=datetime.now(UTC),
        )

    async def _validate(self, url: str) -> ResolvedOutboundUrl:
        # A resolver can be injected so tests never depend on real DNS.
        return await resolve_outbound_url(
            url,
            allowed_hosts=self._allowed_hosts,
            allow_http=self._policy.allow_http,
            resolver=self._resolver,
        )

    async def _get(
        self, url: str, *, params: Mapping[str, str | int | float | bool] | None = None
    ) -> httpx.Response:
        transient = retry_if_exception_type(
            (httpx.TransportError, httpx.TimeoutException, RetryableUpstreamError)
        )
        retrying: AsyncRetrying = AsyncRetrying(
            retry=transient,
            stop=lambda state: state.attempt_number >= self._policy.retry_attempts,
            wait=wait_exponential_jitter(
                multiplier=self._policy.retry_initial_wait,
                max=self._policy.retry_max_wait,
                exp_base=2,
            ),
            reraise=True,
            before_sleep=_log_retry,
        )
        try:
            async for attempt in retrying:
                with attempt:
                    return await self._request_with_redirects(url, params=params)
        except (httpx.TransportError, httpx.TimeoutException) as exc:
            # Retries are exhausted: report a typed connector failure instead of
            # leaking a transport-specific exception to the ingestion core.
            raise UpstreamTransportError(url, type(exc).__name__) from exc
        raise AssertionError("unreachable")  # pragma: no cover - tenacity always returns/raises

    async def _request_with_redirects(
        self, url: str, *, params: Mapping[str, str | int | float | bool] | None = None
    ) -> httpx.Response:
        current = url
        for hop in range(self._policy.max_redirects + 1):
            validated = await self._validate(current)
            current = validated.url
            host = validated.host
            await self._rate_limiter.acquire(host)
            query = params if hop == 0 else None
            response = await self._stream(validated, params=query)
            if response.status_code in _REDIRECT_STATUSES:
                location = response.headers.get("location")
                if not location:
                    raise InvalidPayloadError(f"redirect without location from {current}")
                current = str(httpx.URL(current).join(location))
                logger.info("http_redirect", from_url=current, status_code=response.status_code)
                continue
            if response.status_code in _RETRYABLE_STATUSES:
                raise RetryableUpstreamError(str(response.url), response.status_code)
            if response.status_code >= 400:
                raise UpstreamStatusError(str(response.url), response.status_code)
            return response
        raise UnsafeUrlError(f"too many redirects while fetching {url}")

    async def _stream(
        self,
        validated: ResolvedOutboundUrl,
        *,
        params: Mapping[str, str | int | float | bool] | None = None,
    ) -> httpx.Response:
        original_url = httpx.URL(validated.url)
        if params:
            merged_query: list[tuple[str, str | int | float | bool | None]] = list(
                httpx.QueryParams(original_url.query).multi_items()
            )
            merged_query.extend(httpx.QueryParams(params).multi_items())
            encoded_query = str(httpx.QueryParams(merged_query)).encode("ascii")
            original_url = original_url.copy_with(query=encoded_query)
        original_request = self._client.build_request("GET", original_url)
        # Connect to the exact address approved above. The original hostname is
        # retained for HTTP Host and TLS SNI/certificate verification.
        pinned_url = original_request.url.copy_with(host=validated.addresses[0])
        pinned_request = httpx.Request(
            "GET",
            pinned_url,
            headers=original_request.headers,
            extensions={**original_request.extensions, "sni_hostname": validated.host},
        )
        response = await self._client.send(pinned_request, stream=True)
        try:
            declared = response.headers.get("content-length")
            if (
                declared is not None
                and declared.isdigit()
                and int(declared) > self._policy.max_bytes
            ):
                raise DownloadTooLargeError(str(response.url), self._policy.max_bytes)
            chunks: list[bytes] = []
            total = 0
            async for chunk in response.aiter_bytes():
                total += len(chunk)
                if total > self._policy.max_bytes:
                    raise DownloadTooLargeError(str(response.url), self._policy.max_bytes)
                chunks.append(chunk)
        finally:
            await response.aclose()
        # ``aiter_bytes`` already decoded the transport encoding, so the rebuilt
        # response must not advertise it again (httpx would decode twice).
        headers = [
            (name, value)
            for name, value in response.headers.multi_items()
            if name.lower() not in {"content-encoding", "content-length", "transfer-encoding"}
        ]
        return httpx.Response(
            status_code=response.status_code,
            headers=headers,
            content=b"".join(chunks),
            request=original_request,
        )


def _log_retry(state: RetryCallState) -> None:
    logger.warning(
        "http_retry",
        attempt=state.attempt_number,
        error=str(state.outcome.exception()) if state.outcome else None,
    )


def _parse_http_date(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        parsed = parsedate_to_datetime(value)
    except (TypeError, ValueError):
        return None
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=UTC)
    return parsed.astimezone(UTC)


__all__ = ["BytesPayload", "HttpPolicy", "JsonPayload", "SafeHttpClient"]
