"""Shared schema types."""

from __future__ import annotations

import math
from typing import Annotated, Any, Generic, TypeVar

from fastapi import Query
from pydantic import BaseModel, ConfigDict, Field

from app.core.config import settings

T = TypeVar("T")


class ORMModel(BaseModel):
    """Base for responses read directly from ORM objects."""

    model_config = ConfigDict(from_attributes=True)


class PaginationParams(BaseModel):
    """Validated, bounded pagination. A client cannot ask for the whole table."""

    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=settings.DEFAULT_PAGE_SIZE, ge=1, le=settings.MAX_PAGE_SIZE)

    @property
    def offset(self) -> int:
        return (self.page - 1) * self.page_size

    @property
    def limit(self) -> int:
        return self.page_size


class PaginatedResponse(BaseModel, Generic[T]):
    """A page of results plus everything a client needs to navigate."""

    items: list[T]
    total: int = Field(description="Total rows matching the query, ignoring pagination.")
    page: int
    page_size: int
    total_pages: int
    has_next: bool
    has_previous: bool

    @classmethod
    def build(
        cls, items: list[T], *, total: int, params: PaginationParams
    ) -> "PaginatedResponse[T]":
        """Assemble a page, deriving every navigation field from the totals."""
        total_pages = math.ceil(total / params.page_size) if total else 0
        return cls(
            items=items,
            total=total,
            page=params.page,
            page_size=params.page_size,
            total_pages=total_pages,
            has_next=params.page < total_pages,
            has_previous=params.page > 1 and total > 0,
        )


def pagination(
    page: Annotated[int, Query(ge=1, description="1-based page number.")] = 1,
    page_size: Annotated[
        int,
        Query(ge=1, le=settings.MAX_PAGE_SIZE, description="Rows per page."),
    ] = settings.DEFAULT_PAGE_SIZE,
) -> PaginationParams:
    """FastAPI dependency supplying validated pagination parameters."""
    return PaginationParams(page=page, page_size=page_size)


class Message(BaseModel):
    """Envelope for endpoints whose only output is a human-readable result."""

    message: str


class ErrorDetail(BaseModel):
    code: str
    message: str
    details: dict[str, Any] = Field(default_factory=dict)


class ErrorResponse(BaseModel):
    """The single error shape every endpoint returns on failure."""

    error: ErrorDetail


class HealthResponse(BaseModel):
    """Liveness probe payload."""

    status: str
    service: str
    version: str
    environment: str


class ReadinessResponse(BaseModel):
    """Readiness probe payload, one field per dependency."""

    status: str
    database: str
    ml_model: str


class ServiceInfoResponse(BaseModel):
    """Service identity returned at the API root."""

    status: str
    service: str
    version: str
    docs: str
