"""Schemas for slide generator API."""
from datetime import datetime
from typing import List, Optional, Dict, Any
from uuid import UUID

from pydantic import BaseModel, Field


# Slide Content schemas
class SlideContentBase(BaseModel):
    """Base slide content."""
    bullets: List[str] = Field(default_factory=list)
    subtitle: Optional[str] = None
    details: Optional[str] = None


class SlideOut(BaseModel):
    """Output schema for a single slide."""
    id: UUID
    slide_number: int
    slide_type: str
    title: str
    content: Dict[str, Any]
    speaker_notes: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class SlideUpdate(BaseModel):
    """Request to update a slide."""
    title: Optional[str] = None
    content: Optional[Dict[str, Any]] = None
    speaker_notes: Optional[str] = None
    slide_type: Optional[str] = None


# Message schemas
class MessageOut(BaseModel):
    """Output schema for a chat message."""
    id: UUID
    role: str
    content: str
    created_at: datetime

    class Config:
        from_attributes = True


# Project schemas
class ProjectCreate(BaseModel):
    """Request to create a new project."""
    title: str
    source_text: str
    target_slide_count: Optional[int] = None
    key_points: Optional[str] = None
    template_id: Optional[UUID] = None
    style_id: Optional[UUID] = None


class ProjectSummary(BaseModel):
    """Summary of a project (for list view)."""
    id: UUID
    title: str
    status: str
    slide_count: int = 0
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class ProjectDetail(BaseModel):
    """Detailed project information."""
    id: UUID
    title: str
    source_text: str
    target_slide_count: Optional[int] = None
    key_points: Optional[str] = None
    template_id: Optional[UUID] = None
    style_id: Optional[UUID] = None
    status: str
    error_message: Optional[str] = None
    slides: List[SlideOut]
    messages: List[MessageOut]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class ProjectListResponse(BaseModel):
    """Response for project list."""
    items: List[ProjectSummary]
    total: int
    offset: int
    limit: int


class RefineRequest(BaseModel):
    """Request to refine slides."""
    instruction: str


class RefineResponse(BaseModel):
    """Response for slide refinement."""
    message: str
    slides: List[SlideOut]


# Template schemas
class TemplateOut(BaseModel):
    """Output schema for a template."""
    id: UUID
    name: str
    description: Optional[str] = None
    original_filename: str
    slide_count: int
    created_at: datetime

    class Config:
        from_attributes = True


class TemplateListResponse(BaseModel):
    """Response for template list."""
    items: List[TemplateOut]
    total: int


# Style schemas
class StyleSettingsColors(BaseModel):
    """Color settings for a style."""
    primary: str = "#1a73e8"
    secondary: str = "#5f6368"
    accent: str = "#ea4335"
    background: str = "#ffffff"
    text: str = "#202124"


class StyleSettingsFonts(BaseModel):
    """Font settings for a style."""
    title: str = "Yu Gothic UI"
    body: str = "Yu Gothic UI"


class StyleSettingsSizes(BaseModel):
    """Size settings for a style."""
    title: int = 44
    subtitle: int = 28
    body: int = 20


class StyleSettings(BaseModel):
    """Full style settings."""
    colors: StyleSettingsColors = Field(default_factory=StyleSettingsColors)
    fonts: StyleSettingsFonts = Field(default_factory=StyleSettingsFonts)
    sizes: StyleSettingsSizes = Field(default_factory=StyleSettingsSizes)
    layout_preference: str = "modern"  # modern, classic, minimal


class StyleCreate(BaseModel):
    """Request to create a style."""
    name: str
    description: Optional[str] = None
    settings: StyleSettings
    is_default: bool = False


class StyleUpdate(BaseModel):
    """Request to update a style."""
    name: Optional[str] = None
    description: Optional[str] = None
    settings: Optional[StyleSettings] = None
    is_default: Optional[bool] = None


class StyleOut(BaseModel):
    """Output schema for a style."""
    id: UUID
    name: str
    description: Optional[str] = None
    settings: Dict[str, Any]
    is_default: bool = False
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class StyleListResponse(BaseModel):
    """Response for style list."""
    items: List[StyleOut]
    total: int
