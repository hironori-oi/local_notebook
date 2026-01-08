from datetime import datetime
from typing import List, Optional
from uuid import UUID

from pydantic import BaseModel, Field


class SourceUpdate(BaseModel):
    """ソース更新リクエスト"""

    title: Optional[str] = Field(None, min_length=1, max_length=255)


class SourceSummaryUpdate(BaseModel):
    """ソース要約更新リクエスト"""

    formatted_text: Optional[str] = Field(None, description="整形されたテキスト")
    summary: Optional[str] = Field(None, description="要約")


class SourceOut(BaseModel):
    """ソースレスポンス（一覧用）"""

    id: UUID
    notebook_id: UUID
    title: str
    file_type: str
    folder_id: Optional[UUID] = Field(None, description="フォルダID")
    folder_name: Optional[str] = Field(None, description="フォルダ名")
    processing_status: str = Field(
        default="pending", description="処理状態: pending/processing/completed/failed"
    )
    has_summary: bool = Field(default=False, description="要約が生成済みかどうか")
    created_at: datetime

    class Config:
        from_attributes = True


class SourceDetailOut(BaseModel):
    """ソース詳細レスポンス（要約情報含む）"""

    id: UUID
    notebook_id: UUID
    title: str
    file_type: str
    processing_status: str = Field(
        default="pending", description="処理状態: pending/processing/completed/failed"
    )
    processing_error: Optional[str] = Field(None, description="処理エラーメッセージ")
    full_text: Optional[str] = Field(None, description="抽出された全テキスト")
    formatted_text: Optional[str] = Field(None, description="LLMで整形されたテキスト")
    summary: Optional[str] = Field(None, description="LLMで生成された要約")
    created_at: datetime

    class Config:
        from_attributes = True


class SourceUploadResponse(BaseModel):
    """ソースアップロードレスポンス"""

    source: SourceOut
    chunks_created: int


class SourceListResponse(BaseModel):
    """Paginated response for source list."""

    items: List[SourceOut]
    total: int = Field(..., ge=0, description="Total number of sources")
    offset: int = Field(..., ge=0, description="Number of items skipped")
    limit: int = Field(..., ge=1, description="Maximum items per page")
