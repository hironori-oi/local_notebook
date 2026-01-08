from typing import List, Optional
from uuid import UUID
from pydantic import BaseModel, Field
from datetime import datetime


class SpeakerOpinion(BaseModel):
    """発言者別の意見"""
    speaker: str
    opinions: List[str]


class EmailContent(BaseModel):
    """構造化されたメール内容"""
    document_summary: str = Field(default="", description="資料の要約")
    speaker_opinions: List[SpeakerOpinion] = Field(default_factory=list, description="発言者別意見")
    additional_notes: Optional[str] = Field(default=None, description="補足事項")


class EmailGenerateRequest(BaseModel):
    """メール生成リクエスト"""
    topic: str = Field(..., min_length=1, max_length=500, description="メールの主題")
    document_source_ids: List[UUID] = Field(default_factory=list, description="資料ソースID")
    minute_ids: List[UUID] = Field(default_factory=list, description="議事録ID")


class EmailGenerateResponse(BaseModel):
    """メール生成レスポンス"""
    topic: str
    email_body: str
    content: EmailContent
    sources_used: int
    generated_at: datetime


class GeneratedEmailCreate(BaseModel):
    """保存用メール作成リクエスト"""
    title: str = Field(..., min_length=1, max_length=255)
    topic: Optional[str] = Field(None, max_length=500)
    email_body: str = Field(..., min_length=1)
    structured_content: Optional[EmailContent] = None
    document_source_ids: List[UUID] = Field(default_factory=list)
    minute_ids: List[UUID] = Field(default_factory=list)


class GeneratedEmailUpdate(BaseModel):
    """保存済みメール更新リクエスト"""
    title: Optional[str] = Field(None, min_length=1, max_length=255)
    email_body: Optional[str] = Field(None, min_length=1)


class GeneratedEmailOut(BaseModel):
    """保存済みメールレスポンス"""
    id: UUID
    notebook_id: UUID
    title: str
    topic: Optional[str]
    email_body: str
    structured_content: Optional[dict] = None
    document_source_ids: Optional[List[UUID]] = None
    minute_ids: Optional[List[UUID]] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
