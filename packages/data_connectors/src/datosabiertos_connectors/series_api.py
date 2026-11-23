"""Connector for Argentina's official Time Series API.

The service is not CKAN: it exposes observations and statistical metadata in a
matrix response. This adapter keeps the official bytes and returns one explicit
series, preventing accidental mixing of seasonal variants.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from typing import Any, cast

from .errors import InvalidPayloadError
from .http import HttpPolicy, SafeHttpClient

SERIES_API_URL = "https://apis.datos.gob.ar/series/api/series/"


@dataclass(frozen=True)
class SeriesObservation:
    period: date
    value: Decimal | None


@dataclass(frozen=True)
class SeriesMetadata:
    series_id: str
    description: str
    units: str
    frequency: str
    dataset_title: str
    dataset_description: str | None
    source: str
    distribution_title: str
    download_url: str


@dataclass(frozen=True)
class SeriesFetchResult:
    metadata: SeriesMetadata
    observations: tuple[SeriesObservation, ...]
    raw: bytes
    fetched_at: datetime
    response_url: str


class SeriesApiConnector:
    """Fetch exactly one configured official statistical series."""

    def __init__(
        self,
        *,
        user_agent: str,
        policy: HttpPolicy | None = None,
        transport: Any | None = None,
        resolver: Any | None = None,
    ) -> None:
        self._http = SafeHttpClient(
            user_agent=user_agent,
            allowed_hosts=("apis.datos.gob.ar",),
            policy=policy,
            transport=transport,
            resolver=resolver,
        )

    async def aclose(self) -> None:
        await self._http.aclose()

    async def fetch(
        self,
        series_id: str,
        *,
        start_date: date | None = None,
        end_date: date | None = None,
        limit: int = 5_000,
    ) -> SeriesFetchResult:
        if not series_id or len(series_id) > 128:
            raise ValueError("series_id must contain between 1 and 128 characters")
        if limit < 1 or limit > 5_000:
            raise ValueError("limit must be between 1 and 5000")
        params: dict[str, str | int] = {
            "ids": series_id,
            "limit": limit,
            "representation_mode": "value",
        }
        if start_date:
            params["start_date"] = start_date.isoformat()
        if end_date:
            params["end_date"] = end_date.isoformat()
        response = await self._http.get_json(SERIES_API_URL, params=params)
        return _parse_response(
            response.raw,
            expected_series_id=series_id,
            fetched_at=response.fetched_at,
            response_url=response.url,
        )


def _mapping(value: object, context: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise InvalidPayloadError(f"{context} must be an object")
    return cast(dict[str, Any], value)


def _required_string(payload: dict[str, Any], key: str, context: str) -> str:
    value = payload.get(key)
    if not isinstance(value, str) or not value.strip():
        raise InvalidPayloadError(f"{context}.{key} must be a non-empty string")
    return value


def _parse_response(
    raw: bytes, *, expected_series_id: str, fetched_at: datetime, response_url: str
) -> SeriesFetchResult:
    try:
        payload = json.loads(raw, parse_float=Decimal, parse_int=Decimal)
    except (json.JSONDecodeError, UnicodeDecodeError) as exc:
        raise InvalidPayloadError("series response is not valid JSON") from exc
    root = _mapping(payload, "response")
    meta = root.get("meta")
    data = root.get("data")
    if not isinstance(meta, list) or len(meta) != 2:
        raise InvalidPayloadError("response.meta must contain query and series metadata")
    if not isinstance(data, list):
        raise InvalidPayloadError("response.data must be an array")

    query_meta = _mapping(meta[0], "response.meta[0]")
    series_meta = _mapping(meta[1], "response.meta[1]")
    field = _mapping(series_meta.get("field"), "response.meta[1].field")
    dataset = _mapping(series_meta.get("dataset"), "response.meta[1].dataset")
    distribution = _mapping(series_meta.get("distribution"), "response.meta[1].distribution")
    actual_series_id = _required_string(field, "id", "field")
    if actual_series_id != expected_series_id:
        raise InvalidPayloadError(
            f"series response id {actual_series_id!r} does not match requested id"
        )

    observations: list[SeriesObservation] = []
    previous_period: date | None = None
    for index, raw_row in enumerate(data):
        if not isinstance(raw_row, list) or len(raw_row) != 2:
            raise InvalidPayloadError(f"data[{index}] must contain period and one value")
        try:
            period = date.fromisoformat(str(raw_row[0]))
        except ValueError as exc:
            raise InvalidPayloadError(f"data[{index}] has an invalid period") from exc
        if previous_period is not None and period <= previous_period:
            raise InvalidPayloadError("series periods must be strictly increasing")
        previous_period = period
        raw_value = raw_row[1]
        try:
            value = None if raw_value is None else Decimal(str(raw_value))
        except InvalidOperation as exc:
            raise InvalidPayloadError(f"data[{index}] has an invalid numeric value") from exc
        observations.append(SeriesObservation(period=period, value=value))

    count = root.get("count")
    if not isinstance(count, Decimal) or count != Decimal(len(observations)):
        raise InvalidPayloadError("response.count is inconsistent with returned observations")

    metadata = SeriesMetadata(
        series_id=actual_series_id,
        description=_required_string(field, "description", "field"),
        units=_required_string(field, "units", "field"),
        frequency=_required_string(query_meta, "frequency", "meta[0]"),
        dataset_title=_required_string(dataset, "title", "dataset"),
        dataset_description=dataset.get("description")
        if isinstance(dataset.get("description"), str)
        else None,
        source=_required_string(dataset, "source", "dataset"),
        distribution_title=_required_string(distribution, "title", "distribution"),
        download_url=_required_string(distribution, "downloadURL", "distribution"),
    )
    return SeriesFetchResult(
        metadata=metadata,
        observations=tuple(observations),
        raw=raw,
        fetched_at=fetched_at,
        response_url=response_url,
    )


__all__ = [
    "SERIES_API_URL",
    "SeriesApiConnector",
    "SeriesFetchResult",
    "SeriesMetadata",
    "SeriesObservation",
]
