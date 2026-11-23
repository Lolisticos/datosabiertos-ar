"""Endpoint contracts over a deterministic catalogue (integration)."""

from __future__ import annotations

import uuid
from typing import Any

import pytest
from httpx import AsyncClient


async def test_health_and_readiness(client: AsyncClient) -> None:
    live = await client.get("/api/v1/health")
    assert live.status_code == 200
    assert live.json()["status"] == "ok"

    ready = await client.get("/api/v1/health/ready")
    assert ready.status_code == 200
    body = ready.json()
    assert body["status"] == "ok"
    assert body["database"] == "ok"
    assert body["details"]["storage"] == "writable"


async def test_root_describes_public_scope(client: AsyncClient) -> None:
    response = await client.get("/")
    assert response.status_code == 200
    assert response.json()["name"] == "DatosAbiertos AR API"


async def test_sources_expose_real_counts(
    client: AsyncClient, seeded_catalog: dict[str, Any]
) -> None:
    response = await client.get("/api/v1/sources")
    assert response.status_code == 200
    sources = response.json()
    assert len(sources) == 1
    source = sources[0]
    assert source["slug"] == "test-source"
    assert source["dataset_count"] == 2
    assert source["last_run_status"] == "succeeded"
    assert source["base_url"] == "https://example.test"


async def test_source_detail_and_missing_source(
    client: AsyncClient, seeded_catalog: dict[str, Any]
) -> None:
    found = await client.get("/api/v1/sources/test-source")
    assert found.status_code == 200
    assert found.json()["name"] == "Catálogo de prueba"

    missing = await client.get("/api/v1/sources/no-existe")
    assert missing.status_code == 404


async def test_dataset_search_is_accent_insensitive(
    client: AsyncClient, seeded_catalog: dict[str, Any]
) -> None:
    response = await client.get("/api/v1/datasets", params={"q": "educacion"})
    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 1
    assert body["items"][0]["title"].startswith("Educación")

    accented = await client.get("/api/v1/datasets", params={"q": "EDUCACIÓN"})
    assert accented.json()["total"] == 1


async def test_dataset_filters_and_availability(
    client: AsyncClient, seeded_catalog: dict[str, Any]
) -> None:
    by_topic = await client.get(
        "/api/v1/datasets", params={"topic": "Economía y Finanzas", "available_only": "false"}
    )
    assert by_topic.json()["total"] == 1

    available = await client.get("/api/v1/datasets", params={"available_only": "true"})
    assert available.json()["total"] == 1
    everything = await client.get("/api/v1/datasets", params={"available_only": "false"})
    assert everything.json()["total"] == 2

    by_format = await client.get("/api/v1/datasets", params={"format": "CSV"})
    assert by_format.json()["total"] == 1


async def test_pagination_limits_are_enforced(
    client: AsyncClient, seeded_catalog: dict[str, Any]
) -> None:
    page = await client.get(
        "/api/v1/datasets", params={"page_size": 1, "page": 1, "available_only": "false"}
    )
    body = page.json()
    assert body["page_size"] == 1
    assert body["pages"] == 2
    assert len(body["items"]) == 1

    too_large = await client.get("/api/v1/datasets", params={"page_size": 101})
    assert too_large.status_code == 422

    invalid_page = await client.get("/api/v1/datasets", params={"page": 0})
    assert invalid_page.status_code == 422


async def test_dataset_detail_includes_provenance_and_history(
    client: AsyncClient, seeded_catalog: dict[str, Any]
) -> None:
    dataset_id = seeded_catalog["dataset_id"]
    response = await client.get(f"/api/v1/datasets/{dataset_id}")
    assert response.status_code == 200
    body = response.json()

    assert body["id"] == str(dataset_id)
    assert body["organization"]["name"] == "Ministerio de Educación"
    assert body["source"]["slug"] == "test-source"
    assert body["resources"][0]["format"] == "CSV"
    assert body["provenance"]["raw_snapshot_count"] == 1
    assert body["quality_checks"][0]["check_type"] == "datasets_persisted"
    assert {change["change_type"] for change in body["changes"]} >= {
        "dataset_added",
        "resource_added",
    }
    assert body["latest_run"]["status"] == "succeeded"


async def test_dataset_detail_missing_and_invalid_ids(client: AsyncClient) -> None:
    missing = await client.get(f"/api/v1/datasets/{uuid.uuid4()}")
    assert missing.status_code == 404

    invalid = await client.get("/api/v1/datasets/no-es-uuid")
    assert invalid.status_code == 422


async def test_dataset_changes_endpoint(
    client: AsyncClient, seeded_catalog: dict[str, Any]
) -> None:
    dataset_id = seeded_catalog["dataset_id"]
    response = await client.get(f"/api/v1/datasets/{dataset_id}/changes")
    assert response.status_code == 200
    assert response.json()["total"] == 2

    filtered = await client.get(f"/api/v1/datasets/{dataset_id}/changes", params={"page_size": 1})
    assert len(filtered.json()["items"]) == 1


async def test_visualization_states_real_availability(
    client: AsyncClient, seeded_catalog: dict[str, Any]
) -> None:
    dataset_id = seeded_catalog["dataset_id"]
    response = await client.get(f"/api/v1/datasets/{dataset_id}/visualization")
    assert response.status_code == 200
    body = response.json()
    assert body["available"] is False
    assert body["visualizations"] == []
    assert body["reason"]


async def test_facets_and_explorer_filters(
    client: AsyncClient, seeded_catalog: dict[str, Any]
) -> None:
    facets = await client.get("/api/v1/facets")
    assert facets.status_code == 200
    body = facets.json()
    # Facets describe the discoverable (available) catalogue only.
    assert {facet["value"] for facet in body["topics"]} == {"Educación"}
    assert body["formats"] == [{"value": "CSV", "count": 1}]

    filters = await client.get("/api/v1/datasets/filters")
    assert filters.status_code == 200
    assert filters.json()["topics"]
    assert filters.json()["sources"][0]["slug"] == "test-source"


async def test_discovery_dimensions_are_bounded_and_counted(
    client: AsyncClient, seeded_catalog: dict[str, Any]
) -> None:
    organizations = await client.get("/api/v1/organizations", params={"page_size": 1})
    assert organizations.status_code == 200
    organization_page = organizations.json()
    assert organization_page["total"] == 1
    assert organization_page["items"][0]["dataset_count"] == 2
    assert organization_page["items"][0]["available_dataset_count"] == 1

    organization_id = organization_page["items"][0]["id"]
    detail = await client.get(f"/api/v1/organizations/{organization_id}")
    assert detail.status_code == 200
    missing = await client.get(f"/api/v1/organizations/{uuid.uuid4()}")
    assert missing.status_code == 404

    topics = await client.get("/api/v1/topics")
    assert topics.status_code == 200
    assert topics.json()["items"] == [{"name": "Educación", "dataset_count": 1}]

    jurisdictions = await client.get("/api/v1/jurisdictions")
    assert jurisdictions.status_code == 200
    assert jurisdictions.json()["total"] == 0


async def test_stats_overview_counts(client: AsyncClient, seeded_catalog: dict[str, Any]) -> None:
    response = await client.get("/api/v1/stats/overview")
    assert response.status_code == 200
    body = response.json()
    assert body["datasets"] == 2
    assert body["datasets_available"] == 1
    assert body["resources"] == 1
    assert body["sources"] == 1
    assert body["organizations"] == 1
    assert body["topics"] == 1
    assert body["raw_snapshots"] == 1
    assert body["changes_last_7_days"] == 2
    assert body["coverage_note"]


async def test_ingestion_runs_and_detail(
    client: AsyncClient, seeded_catalog: dict[str, Any]
) -> None:
    listing = await client.get("/api/v1/ingestion-runs")
    assert listing.status_code == 200
    body = listing.json()
    assert body["total"] == 1
    assert body["items"][0]["status"] == "succeeded"

    by_status = await client.get("/api/v1/ingestion-runs", params={"status": "failed"})
    assert by_status.json()["total"] == 0

    detail = await client.get(f"/api/v1/ingestion-runs/{seeded_catalog['run_id']}")
    assert detail.status_code == 200
    assert detail.json()["quality_checks"][0]["status"] == "passed"

    missing = await client.get(f"/api/v1/ingestion-runs/{uuid.uuid4()}")
    assert missing.status_code == 404


async def test_changes_endpoint_filters(
    client: AsyncClient, seeded_catalog: dict[str, Any]
) -> None:
    response = await client.get("/api/v1/changes")
    assert response.status_code == 200
    assert response.json()["total"] == 2

    added = await client.get("/api/v1/changes", params={"change_type": "resource_added"})
    assert added.json()["total"] == 1

    invalid = await client.get("/api/v1/changes", params={"change_type": "nope"})
    assert invalid.status_code == 422


async def test_cors_only_allows_frontend_origin(client: AsyncClient) -> None:
    allowed = await client.get("/api/v1/health", headers={"Origin": "http://localhost:3100"})
    assert allowed.headers.get("access-control-allow-origin") == "http://localhost:3100"

    blocked = await client.get("/api/v1/health", headers={"Origin": "https://evil.test"})
    assert "access-control-allow-origin" not in blocked.headers


@pytest.mark.parametrize("path", ["/api/v1/health", "/api/v1/sources", "/api/v1/datasets"])
async def test_openapi_routes_are_registered(client: AsyncClient, path: str) -> None:
    schema = await client.get("/openapi.json")
    assert schema.status_code == 200
    assert path in schema.json()["paths"]
