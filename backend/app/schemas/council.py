"""Schemas for council (審議会) operations."""
from typing import Optional
from uuid import UUID
from pydantic import BaseModel, Field
from datetime import datetime


class CouncilBase(BaseModel):
    """Base schema for council."""
    title: str = Field(..., min_length=1, max_length=255, description="審議会名")
    description: Optional[str] = Field(None, max_length=5000, description="説明")
    organization: Optional[str] = Field(None, max_length=255, description="所管省庁")
    council_type: Optional[str] = Field(None, max_length=100, description="種別（部会/審議会/委員会など）")
    official_url: Optional[str] = Field(None, max_length=2048, description="公式ページURL")


class CouncilCreate(CouncilBase):
    """Request schema for creating a council."""
    pass  # 審議会は常に公開（is_public=True）


class CouncilUpdate(BaseModel):
    """Request schema for updating a council."""
    title: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = Field(None, max_length=5000)
    organization: Optional[str] = Field(None, max_length=255)
    council_type: Optional[str] = Field(None, max_length=100)
    official_url: Optional[str] = Field(None, max_length=2048)
    # is_public は削除（審議会は常に公開）


class CouncilOut(CouncilBase):
    """Response schema for a council."""
    id: UUID
    owner_id: UUID
    is_public: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class CouncilListOut(BaseModel):
    """Extended council schema for list view with owner info and counts."""
    id: UUID
    title: str
    description: Optional[str] = None
    organization: Optional[str] = None
    council_type: Optional[str] = None
    official_url: Optional[str] = None
    is_public: bool
    owner_id: UUID
    owner_display_name: str
    meeting_count: int = Field(description="開催回数")
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class CouncilDetailOut(CouncilOut):
    """Detailed response schema for a council."""
    owner_display_name: str
    meeting_count: int = Field(description="開催回数")
    note_count: int = Field(description="メモ数")

    class Config:
        from_attributes = True
