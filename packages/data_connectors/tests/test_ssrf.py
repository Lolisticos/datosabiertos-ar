from __future__ import annotations

import pytest

from datosabiertos_connectors.errors import UnsafeUrlError
from datosabiertos_connectors.ssrf import host_matches, is_blocked_address, validate_outbound_url

from .conftest import public_resolver


@pytest.mark.parametrize(
    "address",
    [
        "127.0.0.1",
        "10.1.2.3",
        "172.16.5.4",
        "192.168.1.10",
        "169.254.169.254",
        "100.64.0.1",
        "0.0.0.0",  # noqa: S104 - literal under test, never bound
        "224.0.0.1",
        "::1",
        "fe80::1",
        "fd00::1",
        "::ffff:8.8.8.8",
    ],
)
def test_private_and_reserved_addresses_are_blocked(address: str) -> None:
    assert is_blocked_address(address) is True


@pytest.mark.parametrize("address", ["1.1.1.1", "200.16.116.5", "2800:3f0:4001:81f::200e"])
def test_public_addresses_are_allowed(address: str) -> None:
    assert is_blocked_address(address) is False


def test_host_matches_accepts_subdomains_only() -> None:
    allowed = ("datos.gob.ar",)
    assert host_matches("datos.gob.ar", allowed)
    assert host_matches("apis.datos.gob.ar", allowed)
    assert not host_matches("datos.gob.ar.evil.test", allowed)
    assert not host_matches("evil-test", allowed)


async def test_url_outside_the_configured_source_is_rejected() -> None:
    with pytest.raises(UnsafeUrlError, match="not part of the configured source hosts"):
        await validate_outbound_url(
            "https://attacker.example/leak",
            allowed_hosts=["datos.gob.ar"],
            resolver=public_resolver,
        )


async def test_scheme_port_and_credentials_are_rejected() -> None:
    with pytest.raises(UnsafeUrlError, match="scheme"):
        await validate_outbound_url(
            "file:///etc/passwd", allowed_hosts=["datos.gob.ar"], resolver=public_resolver
        )
    with pytest.raises(UnsafeUrlError, match="port"):
        await validate_outbound_url(
            "https://datos.gob.ar:8443/api",
            allowed_hosts=["datos.gob.ar"],
            resolver=public_resolver,
        )
    with pytest.raises(UnsafeUrlError, match="credentials"):
        await validate_outbound_url(
            "https://user:pass@datos.gob.ar/api",
            allowed_hosts=["datos.gob.ar"],
            resolver=public_resolver,
        )
    with pytest.raises(UnsafeUrlError, match="scheme"):
        await validate_outbound_url(
            "http://datos.gob.ar/api", allowed_hosts=["datos.gob.ar"], resolver=public_resolver
        )


async def test_allow_http_is_opt_in() -> None:
    assert (
        await validate_outbound_url(
            "http://datos.gob.ar/api",
            allowed_hosts=["datos.gob.ar"],
            allow_http=True,
            resolver=public_resolver,
        )
        == "http://datos.gob.ar/api"
    )


async def test_hostname_resolving_to_a_private_address_is_rejected() -> None:
    async def private_resolver(_host: str, _port: int) -> list[str]:
        return ["169.254.169.254"]

    with pytest.raises(UnsafeUrlError, match="blocked address"):
        await validate_outbound_url(
            "https://datos.gob.ar/api",
            allowed_hosts=["datos.gob.ar"],
            resolver=private_resolver,
        )


async def test_private_ip_literal_is_rejected_without_dns() -> None:
    with pytest.raises(UnsafeUrlError, match="blocked address"):
        await validate_outbound_url(
            "https://127.0.0.1/admin",
            allowed_hosts=["127.0.0.1"],
        )


async def test_every_dns_answer_must_be_public() -> None:
    async def mixed_resolver(_host: str, _port: int) -> list[str]:
        return ["200.16.116.5", "10.0.0.8"]

    with pytest.raises(UnsafeUrlError, match="blocked address"):
        await validate_outbound_url(
            "https://datos.gob.ar/api",
            allowed_hosts=["datos.gob.ar"],
            resolver=mixed_resolver,
        )


async def test_empty_and_invalid_dns_answers_are_rejected() -> None:
    async def empty_resolver(_host: str, _port: int) -> list[str]:
        return []

    with pytest.raises(UnsafeUrlError, match="without usable addresses"):
        await validate_outbound_url(
            "https://datos.gob.ar/api",
            allowed_hosts=["datos.gob.ar"],
            resolver=empty_resolver,
        )


async def test_query_is_preserved_and_fragment_is_rejected() -> None:
    assert (
        await validate_outbound_url(
            "https://datos.gob.ar/api?rows=10&sort=name%20asc",
            allowed_hosts=["datos.gob.ar"],
            resolver=public_resolver,
        )
        == "https://datos.gob.ar/api?rows=10&sort=name%20asc"
    )
    with pytest.raises(UnsafeUrlError, match="fragments"):
        await validate_outbound_url(
            "https://datos.gob.ar/api#internal",
            allowed_hosts=["datos.gob.ar"],
            resolver=public_resolver,
        )


async def test_http_cannot_use_the_https_port() -> None:
    with pytest.raises(UnsafeUrlError, match="standard port"):
        await validate_outbound_url(
            "http://datos.gob.ar:443/api",
            allowed_hosts=["datos.gob.ar"],
            allow_http=True,
            resolver=public_resolver,
        )
