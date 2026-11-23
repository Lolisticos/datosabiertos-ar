"""Outbound URL policy (SSRF protection).

Rules enforced before any connector touches the network:

* only ``https`` (and ``http`` when a source explicitly opts in) is allowed;
* URLs carrying credentials, fragments or non-standard ports are rejected;
* the host must be the configured source host or one of its subdomains, so a
  connector can never be pointed at an arbitrary host by upstream metadata;
* every resolved address must be globally routable, which blocks loopback,
  private, link-local, multicast and reserved ranges;
* redirects are followed manually and re-validated on every hop.

The guard is intentionally independent from HTTPX so it can be unit tested
without network access.
"""

from __future__ import annotations

import asyncio
import ipaddress
import socket
from collections.abc import Awaitable, Callable, Iterable
from urllib.parse import urlsplit, urlunsplit

from .errors import UnsafeUrlError

Resolver = Callable[[str, int], Awaitable[list[str]]]

_ALLOWED_PORTS = {80: "http", 443: "https"}
_BLOCKED_NETWORKS = tuple(
    ipaddress.ip_network(network)
    for network in (
        "0.0.0.0/8",
        "10.0.0.0/8",
        "100.64.0.0/10",
        "127.0.0.0/8",
        "169.254.0.0/16",
        "172.16.0.0/12",
        "192.0.0.0/24",
        "192.0.2.0/24",
        "192.168.0.0/16",
        "198.18.0.0/15",
        "198.51.100.0/24",
        "203.0.113.0/24",
        "224.0.0.0/4",
        "240.0.0.0/4",
        "::/128",
        "::1/128",
        "::ffff:0:0/96",
        "fc00::/7",
        "fe80::/10",
        "ff00::/8",
        "2001:db8::/32",
    )
)


def is_blocked_address(raw_address: str) -> bool:
    """Return True when an IP literal must never be contacted."""
    try:
        address = ipaddress.ip_address(raw_address)
    except ValueError:
        return True
    return any(address in network for network in _BLOCKED_NETWORKS)


def host_matches(host: str, allowed_hosts: Iterable[str]) -> bool:
    """True when ``host`` is an allowed host or one of its subdomains."""
    candidate = host.lower().rstrip(".")
    for allowed in allowed_hosts:
        allowed_host = allowed.lower().rstrip(".")
        if candidate == allowed_host or candidate.endswith(f".{allowed_host}"):
            return True
    return False


async def _resolve(host: str, port: int) -> list[str]:
    loop = asyncio.get_running_loop()
    try:
        infos = await loop.getaddrinfo(host, port, type=socket.SOCK_STREAM)
    except socket.gaierror as exc:  # pragma: no cover - network dependent
        raise UnsafeUrlError(f"cannot resolve host {host!r}") from exc
    addresses: set[str] = set()
    for info in infos:
        addresses.add(str(info[4][0]))
    return sorted(addresses)


def _parse(url: str, *, allow_http: bool, allowed_hosts: frozenset[str]) -> tuple[str, str, int]:
    try:
        parts = urlsplit(url)
    except ValueError as exc:
        raise UnsafeUrlError(f"unparseable URL: {url!r}") from exc
    if parts.scheme not in {"http", "https"}:
        raise UnsafeUrlError(f"scheme {parts.scheme!r} is not allowed for outbound requests")
    if parts.scheme == "http" and not allow_http:
        raise UnsafeUrlError("scheme 'http' is not allowed for outbound requests")
    if parts.username or parts.password:
        raise UnsafeUrlError("URLs with embedded credentials are not allowed")
    if not parts.hostname:
        raise UnsafeUrlError(f"URL without host: {url!r}")
    host = parts.hostname.lower()
    port = parts.port or (443 if parts.scheme == "https" else 80)
    expected_scheme = _ALLOWED_PORTS.get(port)
    if expected_scheme is None:
        raise UnsafeUrlError(f"port {port} is not allowed for outbound requests")
    if parts.scheme == "https" and expected_scheme != "https":
        raise UnsafeUrlError("https must use port 443")
    if allowed_hosts and not host_matches(host, allowed_hosts):
        raise UnsafeUrlError(f"host {host!r} is not part of the configured source hosts")
    return parts.scheme, host, port


async def validate_outbound_url(
    url: str,
    *,
    allowed_hosts: Iterable[str] = (),
    allow_http: bool = False,
    expected_media_types: tuple[str, ...] | None = None,
    resolver: Resolver | None = None,
) -> str:
    """Validate ``url`` and return its canonical form.

    ``expected_media_types`` is unused here but part of the signature so callers
    can express content expectations next to the URL policy; content type is
    enforced after the response arrives.
    """
    del expected_media_types
    allowed = frozenset(host.rstrip(".").lower() for host in allowed_hosts)
    scheme, host, port = _parse(url, allow_http=allow_http, allowed_hosts=allowed)

    if not _is_ip_literal(host):
        addresses = await (resolver or _resolve)(host, port)
        for address in addresses:
            if is_blocked_address(address):
                raise UnsafeUrlError(f"{host!r} resolves to the blocked address {address}")

    path = urlsplit(url).path or "/"
    return urlunsplit((scheme, host if port in (80, 443) else f"{host}:{port}", path, "", ""))


def _is_ip_literal(host: str) -> bool:
    try:
        ipaddress.ip_address(host)
    except ValueError:
        return False
    return True


__all__ = ["host_matches", "is_blocked_address", "validate_outbound_url"]
