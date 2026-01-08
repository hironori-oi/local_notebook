from typing import Optional, List
from pydantic import BaseModel, Field


class NoteCreate(BaseModel):
    """ノート作成リクエスト"""
    message_id: str
    title: str = Field(..., min_length=1, max_length=200)


class NoteUpdate(BaseModel):
    """ノート更新リクエスト"""
    title: Optional[str] = Field(None, min_length=1, max_length=200)
    content: Optional[str] = None


class NoteOut(BaseModel):
    """ノート情報レスポンス"""
    id: str
    notebook_id: str
    message_id: str
    title: str
    # User-edited content (if set, overrides original message content)
    content: Optional[str] = None
    created_by: str
    created_at: str
    updated_at: Optional[str] = None
    # Original message content for reference
    question: Optional[str] = None
    answer: Optional[str] = None
    source_refs: Optional[List[str]] = None

    class Config:
        from_attributes = True


class NoteListResponse(BaseModel):
    """Paginated response for note list."""
    items: List[NoteOut]
    total: int = Field(..., ge=0, description="Total number of notes")
    offset: int = Field(..., ge=0, description="Number of items skipped")
    limit: int = Field(..., ge=1, description="Maximum items per page")
