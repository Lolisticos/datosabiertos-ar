from __future__ import annotations

import copy
from collections.abc import AsyncIterator
from datetime import UTC, datetime
from typing import Any

import httpx
import pytest

from datosabiertos_connectors.ckan import CkanConnector
from datosabiertos_connectors.errors import InvalidPayloadError, UpstreamStatusError
from datosabiertos_connectors.types import (
    SourceDataset,
    SourceResource,
    content_hash,
)

from .conftest import load_fixture

BASE_URL = "https://datos.gob.ar"


def _connector(client: Any) -> CkanConnector:
    return CkanConnector(
        base_url=BASE_URL,
        user_agent="DatosAbiertosAR-Test/0.1",
        client=client,
        page_size=2,
    )


def _catalogue_handler(fixture: dict[str, Any], page_size: int = 2) -> Any:
    async def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/api/3/action/package_search"
        start = int(request.url.params.get("start", 0))
        rows = int(request.url.params.get("rows", page_size))
        available = fixture["result"]["results"]
        window = available[start : start + rows]
        payload = {
            "help": "test",
            "success": True,
            "result": {"count": len(available), "results": window},
        }
        return httpx.Response(200, json=payload)

    return handler


async def test_discover_maps_a_real_ckan_payload(make_client: Any) -> None:
    fixture = load_fixture("ckan_package_search.json")
    client = make_client(_catalogue_handler(fixture))
    pages = [page async for page in _connector(client).discover()]

    assert len(pages) == 1
    page = pages[0]
    assert page.total_available == 2
    assert page.offset == 0
    assert page.content_hash == content_hash(page.raw_payload)
    assert len(page.datasets) == 2

    dataset = page.datasets[0]
    assert dataset.external_id == fixture["result"]["results"][0]["id"]
    assert dataset.title.startswith("Indice de producción minero")
    assert dataset.organization is not None
    assert dataset.organization.name == "Secretaría de Minería"
    assert dataset.topic == "Economía y Finanzas"
    assert dataset.license == "Creative Commons Attribution 4.0"
    assert dataset.resources, "CKAN datasets must expose their resources"
    assert dataset.resources[0].format in {"CSV", "XLS", "XLSX", "ZIP", "JSON"}
    assert dataset.resources[0].url.startswith("http")


async def test_discover_paginates_until_the_catalogue_is_exhausted(make_client: Any) -> None:
    fixture = load_fixture("ckan_package_search.json")
    base = fixture["result"]["results"]
    third = copy.deepcopy(base[1])
    third["id"] = "00000000-0000-0000-0000-0000000000aa"
    third["title"] = "Conjunto de prueba de paginación"
    fixture["result"]["results"] = [base[0], base[1], third]

    client = make_client(_catalogue_handler(fixture))
    pages = [page async for page in _connector(client).discover()]

    assert [len(page.datasets) for page in pages] == [2, 1]
    assert [page.offset for page in pages] == [0, 2]
    assert all(page.total_available == 3 for page in pages)
    assert len({page.content_hash for page in pages}) == 2


async def test_discover_stops_when_the_catalogue_is_empty(make_client: Any) -> None:
    empty = {"success": True, "result": {"count": 0, "results": []}}
    client = make_client(_catalogue_handler(empty))
    pages = [page async for page in _connector(client).discover()]
    assert pages == []


async def test_discover_rejects_an_error_payload(make_client: Any) -> None:
    async def handler(_request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"success": False, "error": {"message": "boom"}})

    with pytest.raises(InvalidPayloadError):
        [page async for page in _connector(make_client(handler)).discover()]


async def test_fetch_returns_bytes_and_a_content_hash(make_client: Any) -> None:
    body = b"jurisdiccion,periodo,valor\nAR-C,2024,10\n"

    async def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.host == "datos.gob.ar"
        return httpx.Response(200, content=body, headers={"content-type": "text/csv"})

    resource = SourceResource(
        external_id="res-1",
        url="https://datos.gob.ar/dataset/mineria/archivo/ipim.csv",
        format="CSV",
    )
    result = await _connector(make_client(handler)).fetch(resource)

    assert result.content == body
    assert result.content_hash == content_hash(body)
    assert result.media_type == "text/csv"
    assert result.size == len(body)


async def test_fetch_propagates_upstream_failures(make_client: Any) -> None:
    async def handler(_request: httpx.Request) -> httpx.Response:
        return httpx.Response(404, content=b"not found")

    resource = SourceResource(external_id="res-1", url="https://datos.gob.ar/missing.csv")
    with pytest.raises(UpstreamStatusError):
        await _connector(make_client(handler)).fetch(resource)


def _dataset(**overrides: Any) -> SourceDataset:
    resources = overrides.pop(
        "resources",
        (
            SourceResource(external_id="a", url="https://datos.gob.ar/a.csv", format="CSV"),
            SourceResource(external_id="b", url="https://datos.gob.ar/b.csv", format="JSON"),
        ),
    )
    values: dict[str, Any] = {
        "external_id": "ds-1",
        "title": "Producto Bruto Geográfico",
        "description": "Serie provincial",
        "topic": "Economía y Finanzas",
        "license": "CC-BY-4.0",
        "coverage_start": datetime(2010, 1, 1, tzinfo=UTC).date(),
        "last_source_update": datetime(2026, 1, 2, tzinfo=UTC),
        "resources": resources,
    }
    values.update(overrides)
    return SourceDataset(**values)


def test_metadata_hash_is_stable_and_order_independent() -> None:
    dataset = _dataset()
    reordered = _dataset(resources=tuple(reversed(dataset.resources)))
    assert dataset.metadata_hash() == reordered.metadata_hash()


def test_metadata_hash_changes_when_content_relevant_fields_change() -> None:
    base = _dataset().metadata_hash()
    assert _dataset(title="Otro título").metadata_hash() != base
    assert _dataset(description=None).metadata_hash() != base
    assert (
        _dataset(
            resources=(
                SourceResource(
                    external_id="a", url="https://datos.gob.ar/a.csv", format="CSV", checksum="1"
                ),
            )
        ).metadata_hash()
        != base
    )


def test_connector_metadata_declares_ckan() -> None:
    connector = CkanConnector(base_url=BASE_URL, user_agent="test-agent")
    metadata = connector.metadata()
    assert metadata.name == "ckan"
    assert metadata.source_type.value == "ckan"
    assert metadata.version


async def test_connector_satisfies_the_protocol() -> None:
    from datosabiertos_connectors.types import SourceConnector

    connector = CkanConnector(base_url=BASE_URL, user_agent="test-agent")
    assert isinstance(connector, SourceConnector)
    assert isinstance(connector.discover(), AsyncIterator)  # type: ignore[arg-type]


async def test_discover_shrinks_the_page_when_upstream_truncates(make_client: Any) -> None:
    """datos.gob.ar truncates responses above ~1 MB; the walk must not lose pages."""
    fixture = load_fixture("ckan_package_search.json")
    requests: list[int] = []

    async def handler(request: httpx.Request) -> httpx.Response:
        rows = int(request.url.params.get("rows", 0))
        requests.append(rows)
        if rows > 1:
            raise httpx.RemoteProtocolError("peer closed connection")
        window = fixture["result"]["results"][:rows]
        return httpx.Response(
            200,
            json={
                "success": True,
                "result": {"count": len(fixture["result"]["results"]), "results": window},
            },
        )

    connector = CkanConnector(
        base_url=BASE_URL,
        user_agent="DatosAbiertosAR-Test/0.1",
        client=make_client(handler),
        page_size=4,
        min_page_size=1,
    )
    pages = [page async for page in connector.discover()]

    assert requests[0] == 4
    assert 2 in requests and 1 in requests, "the connector must retry with smaller windows"
    assert pages, "the walk must still yield the pages it could retrieve"


async def test_default_page_size_matches_the_verified_upstream_limit() -> None:
    connector = CkanConnector(base_url=BASE_URL, user_agent="test-agent")
    assert connector._page_size == 50
