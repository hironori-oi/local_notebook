from typing import List, Optional
from uuid import UUID
from pydantic import BaseModel, Field
from datetime import datetime


class NotebookBase(BaseModel):
    title: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = Field(None, max_length=2000)


class NotebookCreate(NotebookBase):
    is_public: bool = False


class NotebookUpdate(BaseModel):
    title: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = Field(None, max_length=2000)
    is_public: Optional[bool] = None


class NotebookOut(NotebookBase):
    id: UUID
    owner_id: UUID
    is_public: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class NotebookListOut(BaseModel):
    """Extended notebook schema for list view with owner info and counts."""
    id: UUID
    title: str
    description: Optional[str] = None
    is_public: bool
    owner_id: UUID
    owner_display_name: str
    source_count: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class NotebookListResponse(BaseModel):
    """Paginated response for notebook list."""
    items: List[NotebookListOut]
    total: int = Field(..., ge=0, description="Total number of notebooks")
    offset: int = Field(..., ge=0, description="Number of items skipped")
    limit: int = Field(..., ge=1, description="Maximum items per page")
