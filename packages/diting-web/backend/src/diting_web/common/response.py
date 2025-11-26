"""Unified response models."""

from typing import Any, Generic, Optional, TypeVar

from pydantic import BaseModel, Field

T = TypeVar("T")


class APIResponse(BaseModel, Generic[T]):
    """Unified API response model."""

    code: int = Field(default=200, description="Status code")
    msg: str = Field(default="success", description="Message")
    data: Optional[T] = Field(default=None, description="Response data")


class ErrorResponse(BaseModel):
    """Error response model."""

    code: int = Field(description="Error code")
    msg: str = Field(default="error", description="Error message")
    error: str = Field(description="Error type")
    detail: Optional[str] = Field(default=None, description="Error detail")


class PaginatedResponse(BaseModel, Generic[T]):
    """Paginated response model."""

    items: list[T] = Field(description="List of items")
    total: int = Field(description="Total count")
    page: int = Field(description="Current page")
    page_size: int = Field(description="Page size")
    pages: int = Field(description="Total pages")

    @classmethod
    def create(
        cls,
        items: list[T],
        total: int,
        page: int,
        page_size: int,
    ) -> "PaginatedResponse[T]":
        """Create paginated response."""
        pages = (total + page_size - 1) // page_size if page_size > 0 else 0
        return cls(
            items=items,
            total=total,
            page=page,
            page_size=page_size,
            pages=pages,
        )


def success_response(data: Any = None, msg: str = "success", code: int = 200) -> dict[str, Any]:
    """Create success response."""
    return {"code": code, "msg": msg, "data": data}


def error_response(
    error: str,
    detail: Optional[str] = None,
    msg: str = "error",
    code: int = 400,
) -> dict[str, Any]:
    """Create error response."""
    response = {"code": code, "msg": msg, "error": error}
    if detail:
        response["detail"] = detail
    return response

