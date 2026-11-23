"""RAW artifact storage behind a small abstraction.

The platform never assumes a concrete storage medium: local filesystem today,
object storage later, without touching ingestion logic.
"""

from __future__ import annotations

import contextlib
import hashlib
import os
import tempfile
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path, PurePosixPath
from typing import Protocol


@dataclass(frozen=True)
class StoredObject:
    key: str
    size: int
    content_hash: str


class StorageBackend(Protocol):
    """Minimal contract: content-addressed, immutable writes."""

    async def put_bytes(self, key: str, content: bytes) -> StoredObject: ...

    async def exists(self, key: str) -> bool: ...

    async def read_bytes(self, key: str) -> bytes: ...


def build_raw_key(
    *,
    source_slug: str,
    kind: str,
    content_hash: str,
    fetched_at: datetime,
    suffix: str = ".json",
) -> str:
    """Deterministic, collision-resistant RAW key: date partition + hash."""
    safe_slug = "".join(char if char.isalnum() or char in "-_" else "-" for char in source_slug)
    return str(
        PurePosixPath(
            "raw",
            safe_slug,
            kind,
            f"{fetched_at:%Y}",
            f"{fetched_at:%m}",
            f"{fetched_at:%Y%m%dT%H%M%SZ}-{content_hash[:16]}{suffix}",
        )
    )


class LocalFileSystemStorage:
    """Writes RAW artifacts under ``root`` with atomic renames."""

    def __init__(self, root: Path) -> None:
        self._root = root

    @property
    def root(self) -> Path:
        return self._root

    def _resolve(self, key: str) -> Path:
        candidate = (self._root / key).resolve()
        root = self._root.resolve()
        if not candidate.is_relative_to(root):
            raise ValueError(f"storage key escapes the storage root: {key!r}")
        return candidate

    async def put_bytes(self, key: str, content: bytes) -> StoredObject:
        digest = hashlib.sha256(content).hexdigest()
        target = self._resolve(key)
        target.parent.mkdir(parents=True, exist_ok=True)
        if target.exists() and target.stat().st_size == len(content):
            return StoredObject(key=key, size=len(content), content_hash=digest)
        handle, temp_name = tempfile.mkstemp(dir=target.parent, prefix=".tmp-")
        try:
            with os.fdopen(handle, "wb") as stream:
                stream.write(content)
                stream.flush()
                os.fsync(stream.fileno())
            os.replace(temp_name, target)
        except BaseException:
            with contextlib.suppress(FileNotFoundError):
                os.unlink(temp_name)
            raise
        return StoredObject(key=key, size=len(content), content_hash=digest)

    async def exists(self, key: str) -> bool:
        return self._resolve(key).is_file()

    async def read_bytes(self, key: str) -> bytes:
        return self._resolve(key).read_bytes()


class InMemoryStorage:
    """Storage double used by tests."""

    def __init__(self) -> None:
        self.objects: dict[str, bytes] = {}

    async def put_bytes(self, key: str, content: bytes) -> StoredObject:
        self.objects[key] = content
        return StoredObject(
            key=key, size=len(content), content_hash=hashlib.sha256(content).hexdigest()
        )

    async def exists(self, key: str) -> bool:
        return key in self.objects

    async def read_bytes(self, key: str) -> bytes:
        try:
            return self.objects[key]
        except KeyError as exc:  # pragma: no cover - defensive
            raise FileNotFoundError(key) from exc


__all__ = [
    "InMemoryStorage",
    "LocalFileSystemStorage",
    "StorageBackend",
    "StoredObject",
    "build_raw_key",
]
