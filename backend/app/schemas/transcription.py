"""
Pydantic schemas for YouTube transcription feature.
"""

import re
from datetime import datetime
from typing import List, Optional
from uuid import UUID

from pydantic import BaseModel, Field, field_validator


class TranscriptionCreate(BaseModel):
    """Schema for creating a new transcription request."""

    youtube_url: str = Field(
        ...,
        description="YouTube video URL",
        min_length=10,
        max_length=2048,
    )

    @field_validator("youtube_url")
    @classmethod
    def validate_youtube_url(cls, v: str) -> str:
        """Validate that the URL is a valid YouTube URL."""
        youtube_patterns = [
            r"^https?://(?:www\.)?youtube\.com/watch\?v=[\w-]+",
            r"^https?://youtu\.be/[\w-]+",
            r"^https?://(?:www\.)?youtube\.com/shorts/[\w-]+",
            r"^https?://(?:www\.)?youtube\.com/live/[\w-]+",
        ]
        if not any(re.match(pattern, v) for pattern in youtube_patterns):
            raise ValueError(
                "Invalid YouTube URL. Supported formats: "
                "youtube.com/watch?v=..., youtu.be/..., youtube.com/shorts/..., youtube.com/live/..."
            )
        return v


class TranscriptionResponse(BaseModel):
    """Schema for transcription response."""

    id: UUID
    user_id: UUID
    youtube_url: str
    video_id: str
    video_title: Optional[str] = None
    raw_transcript: Optional[str] = None
    formatted_transcript: Optional[str] = None
    processing_status: str
    processing_error: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class TranscriptionListItem(BaseModel):
    """Schema for transcription list item (lighter version)."""

    id: UUID
    youtube_url: str
    video_id: str
    video_title: Optional[str] = None
    processing_status: str
    created_at: datetime

    class Config:
        from_attributes = True


class TranscriptionListResponse(BaseModel):
    """Schema for paginated list of transcriptions."""

    items: List[TranscriptionListItem]
    total: int
    page: int
    per_page: int
    pages: int
