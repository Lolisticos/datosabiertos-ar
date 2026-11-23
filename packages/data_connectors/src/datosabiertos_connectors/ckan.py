"""Generic CKAN connector.

CKAN exposes its catalogue through the Action API. The connector only uses
documented endpoints (``package_search``) and never scrapes HTML, which keeps
the integration stable and respectful of the portal's usage policy.

CKAN instances differ in the extra fields they publish, so anything not part of
the base schema is preserved in ``SourceDataset.raw_metadata`` instead of being
guessed at.
"""

from __future__ import annotations

from collections.abc import AsyncIterator, Mapping
from datetime import UTC, date, datetime
from typing import Any
from urllib.parse import urlsplit

import structlog

from .errors import InvalidPayloadError, UpstreamTransportError
from .http import BytesPayload, HttpPolicy, JsonPayload, SafeHttpClient
from .types import (
    ConnectorMetadata,
    ConnectorPage,
    FetchResult,
    SourceDataset,
    SourceOrganization,
    SourceResource,
    SourceType,
    content_hash,
)

logger = structlog.get_logger(__name__)

PACKAGE_SEARCH_PATH = "/api/3/action/package_search"


class CkanConnector:
    """Connector for any CKAN portal reachable through its Action API."""

    def __init__(
        self,
        *,
        base_url: str,
        user_agent: str,
        client: SafeHttpClient | None = None,
        policy: HttpPolicy | None = None,
        # datos.gob.ar truncates responses above ~1 MB, so 50 is the largest
        # page size verified against the live catalogue (2026-11-23).
        page_size: int = 50,
        min_page_size: int = 10,
    ) -> None:
        self._base_url = base_url.rstrip("/")
        self._page_size = page_size
        self._min_page_size = min(min_page_size, page_size)
        self._owns_client = client is None
        self._client = client or SafeHttpClient(
            user_agent=user_agent,
            allowed_hosts=[self._host],
            policy=policy,
        )

    @property
    def _host(self) -> str:
        host = urlsplit(self._base_url).hostname
        if not host:
            raise InvalidPayloadError(f"CKAN base URL without host: {self._base_url!r}")
        return host

    def metadata(self) -> ConnectorMetadata:
        return ConnectorMetadata(
            name="ckan",
            version="1.0.0",
            source_type=SourceType.CKAN,
            description="Catálogo CKAN consultado a través de la Action API (package_search).",
        )

    async def aclose(self) -> None:
        if self._owns_client:
            await self._client.aclose()

    async def __aenter__(self) -> CkanConnector:
        return self

    async def __aexit__(self, *_: object) -> None:
        await self.aclose()

    async def discover(self) -> AsyncIterator[ConnectorPage]:
        offset = 0
        total: int | None = None
        page_size = self._page_size
        while True:
            response = await self._fetch_page(offset=offset, page_size=page_size)
            if response is None:
                # The upstream truncated the response: shrink the window against
                # the same offset instead of losing the rest of the catalogue.
                shrunk = self._shrunken(page_size)
                if shrunk is None:
                    raise InvalidPayloadError(
                        "catalogue page could not be retrieved even at the minimum page size"
                    )
                page_size = shrunk
                continue
            page_size = self._page_size
            result = _extract_result(response.payload)
            count = result.get("count")
            if isinstance(count, int):
                total = count
            raw_results = result.get("results")
            if not isinstance(raw_results, list):
                raise InvalidPayloadError("CKAN package_search response without a results list")

            if not raw_results:
                return

            datasets = tuple(_to_source_dataset(item) for item in raw_results)
            yield ConnectorPage(
                datasets=datasets,
                raw_payload=response.raw,
                media_type="application/json",
                content_hash=content_hash(response.raw),
                offset=offset,
                total_available=total,
                fetched_at=response.fetched_at,
            )
            offset += len(raw_results)
            if total is None or offset >= total:
                return

    def _shrunken(self, page_size: int) -> int | None:
        candidate = max(self._min_page_size, page_size // 2)
        return None if candidate >= page_size else candidate

    async def _fetch_page(self, *, offset: int, page_size: int) -> JsonPayload | None:
        try:
            return await self._client.get_json(
                f"{self._base_url}{PACKAGE_SEARCH_PATH}",
                params={
                    "rows": page_size,
                    "start": offset,
                    # A stable sort key keeps pagination consistent while the
                    # catalogue keeps changing (metadata_modified moves rows).
                    "sort": "name asc",
                },
            )
        except (InvalidPayloadError, UpstreamTransportError) as exc:
            if self._shrunken(page_size) is None:
                raise
            logger.warning(
                "ckan_page_retry_smaller",
                offset=offset,
                page_size=page_size,
                error=str(exc),
            )
            return None

    async def fetch(self, resource: SourceResource) -> FetchResult:
        payload = await self._client.get_bytes(resource.url)
        return _to_fetch_result(payload)


def _extract_result(payload: Mapping[str, Any]) -> Mapping[str, Any]:
    if payload.get("success") is False:
        error = payload.get("error") or {}
        raise InvalidPayloadError(f"CKAN reported an error: {error!r}")
    result = payload.get("result")
    if not isinstance(result, dict):
        raise InvalidPayloadError("CKAN package_search response without a result object")
    return result


def _to_fetch_result(payload: BytesPayload) -> FetchResult:
    return FetchResult(
        url=payload.url,
        status_code=payload.status_code,
        content=payload.content,
        content_hash=content_hash(payload.content),
        media_type=payload.media_type,
        source_last_modified=payload.source_last_modified,
        fetched_at=payload.fetched_at,
    )


def _to_source_dataset(item: dict[str, Any]) -> SourceDataset:
    if not isinstance(item, dict) or not item.get("id"):
        raise InvalidPayloadError("CKAN dataset without id")
    extras = item.get("extras") or []
    extras_map: dict[str, Any] = {}
    if isinstance(extras, list):
        for extra in extras:
            if isinstance(extra, dict) and isinstance(extra.get("key"), str) and extra["key"]:
                extras_map[extra["key"]] = extra.get("value")
    return SourceDataset(
        external_id=str(item["id"]),
        title=(item.get("title") or item.get("name") or str(item["id"])).strip(),
        description=_clean_text(item.get("notes")),
        organization=_to_organization(item.get("organization")),
        topic=_to_topic(item, extras_map),
        license=_dataset_license(item),
        coverage_start=_to_date(extras_map.get("dataset_issued") or item.get("dataset_issued")),
        coverage_end=_to_date(extras_map.get("dataset_modified") or item.get("dataset_modified")),
        last_source_update=_to_datetime(item.get("metadata_modified")),
        landing_url=item.get("url") or None,
        resources=tuple(
            parsed
            for parsed in (_to_resource_safe(resource) for resource in item.get("resources") or ())
            if parsed is not None
        ),
        raw_metadata=item,
    )


def _dataset_license(item: dict[str, Any]) -> str | None:
    """Dataset licence, falling back to a distribution licence shared by all files.

    ``datos.gob.ar`` publishes an empty dataset-level licence and states the
    licence on each distribution instead; the fallback only applies when every
    distribution agrees, so it never invents a licence.
    """
    declared = _clean_text(item.get("license_title")) or _clean_text(item.get("license_id"))
    if declared:
        return declared
    resource_licenses = {
        licence
        for resource in item.get("resources") or ()
        if isinstance(resource, dict)
        and (licence := _clean_text(resource.get("distribution_license")))
    }
    return resource_licenses.pop() if len(resource_licenses) == 1 else None


def _to_organization(raw: Any) -> SourceOrganization | None:
    if not isinstance(raw, dict):
        return None
    name = _clean_text(raw.get("title")) or _clean_text(raw.get("name"))
    external_id = _clean_text(raw.get("name")) or _clean_text(raw.get("id"))
    if not name or not external_id:
        return None
    return SourceOrganization(external_id=external_id, name=name)


def _to_topic(item: dict[str, Any], extras: Mapping[str, Any]) -> str | None:
    groups = item.get("groups") or []
    if isinstance(groups, list):
        for group in groups:
            if isinstance(group, dict):
                title = _clean_text(group.get("title")) or _clean_text(group.get("name"))
                if title:
                    return title
    return _clean_text(extras.get("dataset_theme")) or _clean_text(item.get("dataset_theme"))


def _to_resource_safe(raw: Any) -> SourceResource | None:
    """Skip a malformed distribution instead of losing the whole catalogue page."""
    try:
        return _to_resource(raw)
    except InvalidPayloadError as exc:
        logger.warning("ckan_resource_skipped", error=str(exc))
        return None


def _to_resource(raw: Any) -> SourceResource:
    if not isinstance(raw, dict) or not raw.get("url"):
        raise InvalidPayloadError("CKAN resource without url")
    external_id = _clean_text(raw.get("id")) or _clean_text(raw.get("name"))
    if not external_id:
        raise InvalidPayloadError("CKAN resource without id")
    byte_size = raw.get("distribution_byteSize") or raw.get("size")
    return SourceResource(
        external_id=external_id,
        name=_clean_text(raw.get("name")) or _clean_text(raw.get("description")),
        format=_clean_text(raw.get("format")),
        url=str(raw["url"]),
        mime_type=_clean_text(raw.get("mimetype")),
        checksum=_clean_text(raw.get("hash")),
        file_size=_to_int(byte_size),
        last_modified=_to_datetime(raw.get("last_modified")),
        description=_clean_text(raw.get("description")),
    )


def _clean_text(value: Any) -> str | None:
    """Scalar text only: lists/dicts are kept in RAW metadata, never stringified."""
    if value is None or isinstance(value, (list, tuple, dict, set)):
        return None
    text = str(value).strip()
    return text or None


def _to_int(value: Any) -> int | None:
    if value is None or value == "":
        return None
    try:
        parsed = int(str(value).strip())
    except (TypeError, ValueError):
        return None
    return parsed if parsed >= 0 else None


def _to_date(value: Any) -> date | None:
    parsed = _to_datetime(value)
    return None if parsed is None else parsed.date()


def _to_datetime(value: Any) -> datetime | None:
    text = _clean_text(value)
    if not text:
        return None
    candidate = text.replace("Z", "+00:00")
    for candidate_text in (candidate, candidate.replace(" ", "T")):
        try:
            parsed = datetime.fromisoformat(candidate_text)
        except ValueError:
            continue
        if parsed.tzinfo is None:
            return parsed.replace(tzinfo=UTC)
        return parsed.astimezone(UTC)
    return None


__all__ = ["CkanConnector"]
