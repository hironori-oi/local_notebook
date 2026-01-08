"""Schemas for source folder management."""
from typing import Optional, List
from uuid import UUID
from pydantic import BaseModel, Field
from datetime import datetime


class FolderCreate(BaseModel):
    """フォルダ作成リクエスト"""
    name: str = Field(..., min_length=1, max_length=255)


class FolderUpdate(BaseModel):
    """フォルダ更新リクエスト"""
    name: Optional[str] = Field(None, min_length=1, max_length=255)


class FolderOut(BaseModel):
    """フォルダレスポンス"""
    id: UUID
    notebook_id: UUID
    name: str
    position: int
    source_count: int = Field(default=0, description="フォルダ内の資料数")
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class FolderReorder(BaseModel):
    """フォルダ並び替えリクエスト"""
    folder_ids: List[UUID] = Field(..., description="新しい順序でのフォルダIDリスト")


class SourceMoveRequest(BaseModel):
    """資料移動リクエスト"""
    folder_id: Optional[UUID] = Field(None, description="移動先フォルダID（nullでルートへ）")
