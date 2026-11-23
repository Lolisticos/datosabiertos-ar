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
from dataclasses import dataclass
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


@dataclass(frozen=True)
class ResolvedOutboundUrl:
    """A canonical URL plus the exact public addresses approved for the socket."""

    url: str
    scheme: str
    host: str
    port: int
    addresses: tuple[str, ...]


def is_blocked_address(raw_address: str) -> bool:
    """Return True when an IP literal must never be contacted."""
    try:
        address = ipaddress.ip_address(raw_address)
    except ValueError:
        return True
    # ``is_global`` also covers newly classified special-use ranges that may
    # not yet appear in our explicit defence-in-depth list.
    return not address.is_global or any(address in network for network in _BLOCKED_NETWORKS)


def _canonical_host(host: str) -> str:
    candidate = host.rstrip(".").lower()
    try:
        return str(ipaddress.ip_address(candidate))
    except ValueError:
        try:
            return candidate.encode("idna").decode("ascii")
        except UnicodeError as exc:
            raise UnsafeUrlError(f"invalid internationalized host {host!r}") from exc


def host_matches(host: str, allowed_hosts: Iterable[str]) -> bool:
    """True when ``host`` is an allowed host or one of its subdomains."""
    candidate = _canonical_host(host)
    for allowed in allowed_hosts:
        allowed_host = _canonical_host(allowed)
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


def _parse(
    url: str, *, allow_http: bool, allowed_hosts: frozenset[str]
) -> tuple[str, str, int, str, str]:
    if any(ord(char) < 32 or ord(char) == 127 for char in url):
        raise UnsafeUrlError("control characters are not allowed in outbound URLs")
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
    if parts.fragment:
        raise UnsafeUrlError("URL fragments are not allowed in outbound requests")
    if not parts.hostname:
        raise UnsafeUrlError(f"URL without host: {url!r}")
    host = _canonical_host(parts.hostname)
    port = parts.port or (443 if parts.scheme == "https" else 80)
    expected_scheme = _ALLOWED_PORTS.get(port)
    if expected_scheme is None:
        raise UnsafeUrlError(f"port {port} is not allowed for outbound requests")
    if expected_scheme != parts.scheme:
        raise UnsafeUrlError(f"scheme {parts.scheme!r} must use its standard port")
    if not allowed_hosts:
        raise UnsafeUrlError("at least one configured source host is required")
    if not host_matches(host, allowed_hosts):
        raise UnsafeUrlError(f"host {host!r} is not part of the configured source hosts")
    return parts.scheme, host, port, parts.path or "/", parts.query


async def resolve_outbound_url(
    url: str,
    *,
    allowed_hosts: Iterable[str],
    allow_http: bool = False,
    resolver: Resolver | None = None,
) -> ResolvedOutboundUrl:
    """Validate and resolve a URL once, returning addresses safe to pin.

    Callers must connect to one of ``addresses`` rather than resolving ``host``
    again. This closes the validation/use gap exploited by DNS rebinding.
    """

    allowed = frozenset(_canonical_host(host) for host in allowed_hosts)
    scheme, host, port, path, query = _parse(url, allow_http=allow_http, allowed_hosts=allowed)
    if _is_ip_literal(host):
        addresses = [host]
    else:
        addresses = await (resolver or _resolve)(host, port)
    if not addresses:
        raise UnsafeUrlError(f"host {host!r} resolved without usable addresses")

    canonical_addresses: set[str] = set()
    for raw_address in addresses:
        try:
            address = str(ipaddress.ip_address(raw_address))
        except ValueError as exc:
            raise UnsafeUrlError(f"resolver returned an invalid address {raw_address!r}") from exc
        if is_blocked_address(address):
            raise UnsafeUrlError(f"{host!r} resolves to the blocked address {address}")
        canonical_addresses.add(address)

    netloc = f"[{host}]" if ":" in host else host
    canonical_url = urlunsplit((scheme, netloc, path, query, ""))
    return ResolvedOutboundUrl(
        url=canonical_url,
        scheme=scheme,
        host=host,
        port=port,
        addresses=tuple(sorted(canonical_addresses)),
    )


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
    resolved = await resolve_outbound_url(
        url,
        allowed_hosts=allowed_hosts,
        allow_http=allow_http,
        resolver=resolver,
    )
    return resolved.url


def _is_ip_literal(host: str) -> bool:
    try:
        ipaddress.ip_address(host)
    except ValueError:
        return False
    return True


__all__ = [
    "ResolvedOutboundUrl",
    "host_matches",
    "is_blocked_address",
    "resolve_outbound_url",
    "validate_outbound_url",
]
