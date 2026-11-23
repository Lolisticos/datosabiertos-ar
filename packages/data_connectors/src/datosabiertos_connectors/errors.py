"""Connector error hierarchy.

Every failure is represented by a narrow type so the ingestion core can decide
between retrying, marking a partial run, or stopping with a diagnostic.
"""

from __future__ import annotations


class ConnectorError(Exception):
    """Base class for every expected connector failure."""


class UnsafeUrlError(ConnectorError):
    """The URL violates the outbound request policy (SSRF guard, scheme, host)."""


class UpstreamStatusError(ConnectorError):
    """The upstream service answered with a non-retryable status code."""

    def __init__(self, url: str, status_code: int) -> None:
        super().__init__(f"upstream returned HTTP {status_code} for {url}")
        self.url = url
        self.status_code = status_code


class RetryableUpstreamError(ConnectorError):
    """A transient upstream failure (5xx, 429, timeout) worth retrying."""

    def __init__(self, url: str, status_code: int) -> None:
        super().__init__(f"upstream returned retryable HTTP {status_code} for {url}")
        self.url = url
        self.status_code = status_code


class DownloadTooLargeError(ConnectorError):
    """The response exceeded the configured byte cap."""

    def __init__(self, url: str, limit: int) -> None:
        super().__init__(f"response from {url} exceeded the {limit} byte limit")
        self.url = url
        self.limit = limit


class UpstreamTransportError(ConnectorError):
    """The connection failed or the response was truncated after retries."""

    def __init__(self, url: str, reason: str) -> None:
        super().__init__(f"transport failure for {url}: {reason}")
        self.url = url
        self.reason = reason


class InvalidPayloadError(ConnectorError):
    """The upstream payload does not match the contract the connector expects."""


__all__ = [
    "ConnectorError",
    "DownloadTooLargeError",
    "InvalidPayloadError",
    "RetryableUpstreamError",
    "UnsafeUrlError",
    "UpstreamStatusError",
    "UpstreamTransportError",
]
