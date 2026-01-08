"""
Common schema definitions for shared functionality across the API.

This module provides reusable schema components like pagination.
"""

from typing import Generic, List, TypeVar

from pydantic import BaseModel, Field

# Generic type for paginated items
T = TypeVar("T")


class PaginatedResponse(BaseModel, Generic[T]):
    """
    Generic paginated response wrapper.

    Provides consistent pagination metadata across all list endpoints.
    """

    items: List[T] = Field(..., description="List of items in the current page")
    total: int = Field(..., ge=0, description="Total number of items across all pages")
    offset: int = Field(..., ge=0, description="Number of items skipped")
    limit: int = Field(..., ge=1, description="Maximum items per page")

    class Config:
        json_schema_extra = {
            "example": {"items": [], "total": 100, "offset": 0, "limit": 50}
        }
