"""FastAPI dependencies shared by the routers."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Annotated

from fastapi import Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from ..core.config import Settings, get_settings
from ..db.session import get_session

SessionDep = Annotated[AsyncSession, Depends(get_session)]
SettingsDep = Annotated[Settings, Depends(get_settings)]


@dataclass(frozen=True)
class Pagination:
    page: int
    page_size: int

    @property
    def offset(self) -> int:
        return (self.page - 1) * self.page_size


def pagination(
    page: Annotated[int, Query(ge=1, le=10_000, description="Página, desde 1")] = 1,
    page_size: Annotated[
        int, Query(ge=1, le=100, description="Elementos por página (máx. 100)")
    ] = 20,
) -> Pagination:
    """Hard pagination limits: the API can never be asked for unbounded data."""
    return Pagination(page=page, page_size=page_size)


PaginationDep = Annotated[Pagination, Depends(pagination)]

__all__ = ["Pagination", "PaginationDep", "SessionDep", "SettingsDep", "pagination"]
