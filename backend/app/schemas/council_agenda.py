"""Schemas for council agenda item operations."""
from typing import Optional, List
from uuid import UUID
from pydantic import BaseModel, Field
from datetime import datetime


# ============================================================
# Material schemas (for multiple materials per agenda item)
# ============================================================


class CouncilAgendaMaterialBase(BaseModel):
    """Base schema for council agenda material."""
    material_number: int = Field(..., ge=1, description="資料番号")
    title: Optional[str] = Field(None, max_length=255, description="資料タイトル")
    url: str = Field(..., max_length=2048, description="資料URL")


class CouncilAgendaMaterialCreate(CouncilAgendaMaterialBase):
    """Request schema for creating a council agenda material."""
    pass


class CouncilAgendaMaterialUpdate(BaseModel):
    """Request schema for updating a council agenda material."""
    material_number: Optional[int] = Field(None, ge=1)
    title: Optional[str] = Field(None, max_length=255)
    url: Optional[str] = Field(None, max_length=2048)


class CouncilAgendaMaterialOut(CouncilAgendaMaterialBase):
    """Response schema for a council agenda material."""
    id: UUID
    agenda_id: UUID
    processing_status: str = Field(default="pending", description="処理状態")
    has_summary: bool = Field(default=False, description="要約生成済み")
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class CouncilAgendaMaterialDetailOut(CouncilAgendaMaterialOut):
    """Detailed response schema for a council agenda material."""
    text: Optional[str] = Field(None, description="取得した資料テキスト")
    summary: Optional[str] = Field(None, description="資料要約")
    processing_error: Optional[str] = Field(None, description="処理エラーメッセージ")

    class Config:
        from_attributes = True


# ============================================================
# Agenda schemas
# ============================================================


class CouncilAgendaBase(BaseModel):
    """Base schema for council agenda item."""
    agenda_number: int = Field(..., ge=1, description="議題番号")
    title: Optional[str] = Field(None, max_length=255, description="議題タイトル")
    materials_url: Optional[str] = Field(None, max_length=2048, description="資料URL（レガシー用）")
    minutes_url: Optional[str] = Field(None, max_length=2048, description="議事録URL")


class CouncilAgendaCreate(CouncilAgendaBase):
    """Request schema for creating a council agenda item."""
    materials: Optional[List[CouncilAgendaMaterialCreate]] = Field(
        None, description="資料リスト（複数登録可）"
    )


class CouncilAgendaUpdate(BaseModel):
    """Request schema for updating a council agenda item."""
    agenda_number: Optional[int] = Field(None, ge=1)
    title: Optional[str] = Field(None, max_length=255)
    materials_url: Optional[str] = Field(None, max_length=2048)
    minutes_url: Optional[str] = Field(None, max_length=2048)


class CouncilAgendaOut(CouncilAgendaBase):
    """Response schema for a council agenda item."""
    id: UUID
    meeting_id: UUID
    materials_processing_status: str = Field(default="pending", description="資料処理状態（レガシー用）")
    minutes_processing_status: str = Field(default="pending", description="議事録処理状態")
    has_materials_summary: bool = Field(default=False, description="資料要約生成済み（レガシー用）")
    has_minutes_summary: bool = Field(default=False, description="議事録要約生成済み")
    materials_count: int = Field(default=0, description="登録資料数")
    materials: List[CouncilAgendaMaterialOut] = Field(default=[], description="資料リスト")
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class CouncilAgendaListItem(BaseModel):
    """Simplified response schema for agenda list."""
    id: UUID
    meeting_id: UUID
    agenda_number: int
    title: Optional[str] = None
    has_materials_url: bool = Field(description="資料URLあり（レガシー用）")
    has_minutes_url: bool = Field(description="議事録URLあり")
    materials_processing_status: str
    minutes_processing_status: str
    has_materials_summary: bool
    has_minutes_summary: bool
    materials_count: int = Field(default=0, description="登録資料数")
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class CouncilAgendaDetailOut(BaseModel):
    """Detailed response schema for a council agenda item."""
    id: UUID
    meeting_id: UUID
    agenda_number: int
    title: Optional[str] = None
    materials_url: Optional[str] = Field(None, description="資料URL（レガシー用）")
    minutes_url: Optional[str] = Field(None, description="議事録URL")
    materials_text: Optional[str] = Field(None, description="取得した資料テキスト（レガシー用）")
    minutes_text: Optional[str] = Field(None, description="取得した議事録テキスト")
    materials_summary: Optional[str] = Field(None, description="資料要約（レガシー用）")
    minutes_summary: Optional[str] = Field(None, description="議事録要約")
    materials_processing_status: str = Field(default="pending", description="資料処理状態（レガシー用）")
    minutes_processing_status: str = Field(default="pending", description="議事録処理状態")
    has_materials_summary: bool = Field(default=False, description="資料要約生成済み（レガシー用）")
    has_minutes_summary: bool = Field(default=False, description="議事録要約生成済み")
    processing_error: Optional[str] = Field(None, description="処理エラーメッセージ")
    materials_count: int = Field(default=0, description="登録資料数")
    materials: List[CouncilAgendaMaterialDetailOut] = Field(default=[], description="資料リスト（詳細）")
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class CouncilAgendaSummaryUpdate(BaseModel):
    """Request schema for updating agenda summaries."""
    materials_summary: Optional[str] = Field(None, description="資料要約（レガシー用）")
    minutes_summary: Optional[str] = Field(None, description="議事録要約")


class CouncilAgendaMaterialSummaryUpdate(BaseModel):
    """Request schema for updating a material's summary."""
    summary: Optional[str] = Field(None, description="資料要約")
