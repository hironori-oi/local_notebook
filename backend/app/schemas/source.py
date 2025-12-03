from typing import Optional
from uuid import UUID
from pydantic import BaseModel, Field
from datetime import datetime


class SourceUpdate(BaseModel):
    """ソース更新リクエスト"""
    title: str = Field(..., min_length=1, max_length=255)


class SourceOut(BaseModel):
    id: UUID
    notebook_id: UUID
    title: str
    file_type: str
    created_at: datetime

    class Config:
        from_attributes = True


class SourceUploadResponse(BaseModel):
    source: SourceOut
    chunks_created: int
