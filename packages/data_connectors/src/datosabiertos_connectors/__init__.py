"""Connectors that read official Argentine open-data sources.

The public surface is deliberately small: the ingestion core depends on
``SourceConnector`` and the canonical types, never on a concrete connector.
"""

from .ckan import CkanConnector
from .errors import (
    ConnectorError,
    DownloadTooLargeError,
    InvalidPayloadError,
    RetryableUpstreamError,
    UnsafeUrlError,
    UpstreamStatusError,
    UpstreamTransportError,
)
from .http import HttpPolicy, SafeHttpClient
from .ssrf import validate_outbound_url
from .types import (
    ConnectorMetadata,
    ConnectorPage,
    FetchResult,
    SourceConnector,
    SourceDataset,
    SourceOrganization,
    SourceResource,
    SourceType,
    canonical_hash,
    canonical_json,
    content_hash,
)

__all__ = [
    "CkanConnector",
    "ConnectorError",
    "ConnectorMetadata",
    "ConnectorPage",
    "DownloadTooLargeError",
    "FetchResult",
    "HttpPolicy",
    "InvalidPayloadError",
    "RetryableUpstreamError",
    "SafeHttpClient",
    "SourceConnector",
    "SourceDataset",
    "SourceOrganization",
    "SourceResource",
    "SourceType",
    "UnsafeUrlError",
    "UpstreamStatusError",
    "UpstreamTransportError",
    "canonical_hash",
    "canonical_json",
    "content_hash",
    "validate_outbound_url",
]
