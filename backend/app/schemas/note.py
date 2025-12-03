from typing import Optional, List
from pydantic import BaseModel, Field


class NoteCreate(BaseModel):
    """ノート作成リクエスト"""
    message_id: str
    title: str = Field(..., min_length=1, max_length=200)


class NoteUpdate(BaseModel):
    """ノート更新リクエスト"""
    title: str = Field(..., min_length=1, max_length=200)


class NoteOut(BaseModel):
    """ノート情報レスポンス"""
    id: str
    notebook_id: str
    message_id: str
    title: str
    created_by: str
    created_at: str
    # Include message content for display
    question: Optional[str] = None
    answer: Optional[str] = None
    source_refs: Optional[List[str]] = None

    class Config:
        from_attributes = True
