from __future__ import annotations

from datetime import date
from decimal import Decimal
from pathlib import Path

import httpx
import pytest

from datosabiertos_connectors import HttpPolicy, InvalidPayloadError, SeriesApiConnector

FIXTURE = Path(__file__).parent / "fixtures" / "series_emae.json"


async def public_resolver(host: str, port: int) -> list[str]:
    assert host == "apis.datos.gob.ar"
    assert port == 443
    return ["93.184.216.34"]


def connector_for(content: bytes) -> SeriesApiConnector:
    async def handler(request: httpx.Request) -> httpx.Response:
        assert request.headers["host"] == "apis.datos.gob.ar"
        assert request.url.params["ids"] == "143.3_NO_PR_2004_A_21"
        return httpx.Response(200, content=content, request=request)

    return SeriesApiConnector(
        user_agent="pytest",
        policy=HttpPolicy(retry_attempts=1, requests_per_second=0),
        transport=httpx.MockTransport(handler),
        resolver=public_resolver,
    )


async def test_fetches_one_series_preserving_decimals_and_missing_values() -> None:
    connector = connector_for(FIXTURE.read_bytes())
    try:
        result = await connector.fetch("143.3_NO_PR_2004_A_21")
    finally:
        await connector.aclose()

    assert result.metadata.description == "EMAE. Base 2004"
    assert result.metadata.frequency == "month"
    assert result.observations[0].value == Decimal("146.49668268147974")
    assert result.observations[1].value is None
    assert result.observations[2].period == date(2025, 3, 1)


async def test_rejects_unordered_periods() -> None:
    content = FIXTURE.read_text().replace('"2025-03-01"', '"2025-01-01"').encode()
    connector = connector_for(content)
    try:
        with pytest.raises(InvalidPayloadError, match="strictly increasing"):
            await connector.fetch("143.3_NO_PR_2004_A_21")
    finally:
        await connector.aclose()
