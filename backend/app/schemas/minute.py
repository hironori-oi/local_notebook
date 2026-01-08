"""Schemas for minute (meeting minutes) operations."""

from datetime import datetime
from typing import List, Optional
from uuid import UUID

from pydantic import BaseModel, Field


class MinuteCreate(BaseModel):
    """議事録作成リクエスト"""

    title: str = Field(..., min_length=1, max_length=255, description="議事録タイトル")
    content: str = Field(..., min_length=1, max_length=50000, description="議事録本文")
    document_ids: List[UUID] = Field(default_factory=list, description="関連資料ID")


class MinuteUpdate(BaseModel):
    """議事録更新リクエスト"""

    title: Optional[str] = Field(None, min_length=1, max_length=255)
    content: Optional[str] = Field(None, min_length=1, max_length=50000)


class MinuteSummaryUpdate(BaseModel):
    """議事録要約更新リクエスト"""

    formatted_content: Optional[str] = Field(None, description="整形されたコンテンツ")
    summary: Optional[str] = Field(None, description="要約")


class MinuteDocumentsUpdate(BaseModel):
    """議事録の関連資料更新リクエスト"""

    document_ids: List[UUID] = Field(..., description="関連資料ID一覧")


class MinuteOut(BaseModel):
    """議事録レスポンス"""

    id: UUID
    notebook_id: UUID
    title: str
    content: str
    document_ids: List[UUID] = Field(default_factory=list, description="関連資料ID一覧")
    processing_status: str = Field(
        default="pending", description="処理状態: pending/processing/completed/failed"
    )
    has_summary: bool = Field(default=False, description="要約が生成済みかどうか")
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class MinuteListItem(BaseModel):
    """議事録一覧用の簡略レスポンス"""

    id: UUID
    notebook_id: UUID
    title: str
    document_count: int = Field(description="関連資料数")
    processing_status: str = Field(default="pending", description="処理状態")
    has_summary: bool = Field(default=False, description="要約生成済み")
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class MinuteDetailOut(BaseModel):
    """議事録詳細レスポンス（要約情報含む）"""

    id: UUID
    notebook_id: UUID
    title: str
    content: str
    document_ids: List[UUID] = Field(default_factory=list, description="関連資料ID一覧")
    processing_status: str = Field(
        default="pending", description="処理状態: pending/processing/completed/failed"
    )
    processing_error: Optional[str] = Field(None, description="処理エラーメッセージ")
    formatted_content: Optional[str] = Field(
        None, description="LLMで整形されたコンテンツ"
    )
    summary: Optional[str] = Field(None, description="LLMで生成された要約")
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
