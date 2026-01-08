"""Schemas for council note operations."""
from typing import Optional
from uuid import UUID
from pydantic import BaseModel, Field
from datetime import datetime


class CouncilNoteBase(BaseModel):
    """Base schema for council note."""
    title: str = Field(..., min_length=1, max_length=255, description="メモタイトル")
    content: str = Field(..., min_length=1, max_length=50000, description="メモ内容")


class CouncilNoteCreate(CouncilNoteBase):
    """Request schema for creating a council note."""
    council_id: UUID = Field(..., description="審議会ID")
    meeting_id: Optional[UUID] = Field(None, description="開催回ID（NULLで審議会レベルのメモ）")


class CouncilNoteUpdate(BaseModel):
    """Request schema for updating a council note."""
    title: Optional[str] = Field(None, min_length=1, max_length=255)
    content: Optional[str] = Field(None, min_length=1, max_length=50000)


class CouncilNoteOut(CouncilNoteBase):
    """Response schema for a council note."""
    id: UUID
    council_id: UUID
    meeting_id: Optional[UUID] = None
    user_id: UUID
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class CouncilNoteListItem(BaseModel):
    """Simplified response schema for note list."""
    id: UUID
    council_id: UUID
    meeting_id: Optional[UUID] = None
    meeting_number: Optional[int] = Field(None, description="開催回番号（meeting_idがある場合）")
    user_id: UUID
    user_display_name: str = Field(description="作成者表示名")
    title: str
    content_preview: str = Field(description="内容プレビュー（最初の100文字）")
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
