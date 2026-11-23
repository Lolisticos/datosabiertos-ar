"""Text normalization shared by ingestion and search.

Argentine users type "educacion" as often as "educación". Search therefore works
on an accent-free, lower-cased projection stored alongside the dataset, which
keeps ILIKE queries index-backed and predictable.
"""

from __future__ import annotations

import re
import unicodedata

_WHITESPACE = re.compile(r"\s+")
MAX_QUERY_LENGTH = 200


def strip_accents(value: str) -> str:
    decomposed = unicodedata.normalize("NFKD", value)
    return "".join(char for char in decomposed if not unicodedata.combining(char))


def normalize_text(value: str | None) -> str:
    if not value:
        return ""
    collapsed = _WHITESPACE.sub(" ", strip_accents(value).lower())
    return collapsed.strip()


def normalize_query(value: str | None, *, limit: int = MAX_QUERY_LENGTH) -> str | None:
    normalized = normalize_text(value)
    if not normalized:
        return None
    return normalized[:limit]


def build_search_text(*parts: str | None) -> str:
    return normalize_text(" ".join(part for part in parts if part))


__all__ = [
    "MAX_QUERY_LENGTH",
    "build_search_text",
    "normalize_query",
    "normalize_text",
    "strip_accents",
]
