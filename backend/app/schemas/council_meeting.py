"""Schemas for council meeting (開催回) operations."""

from datetime import datetime
from typing import List, Optional
from uuid import UUID

from pydantic import BaseModel, Field

from .council_agenda import CouncilAgendaListItem, CouncilAgendaOut


class CouncilMeetingBase(BaseModel):
    """Base schema for council meeting."""

    meeting_number: int = Field(..., ge=1, description="開催回数（第X回）")
    title: Optional[str] = Field(None, max_length=255, description="開催名")
    scheduled_at: datetime = Field(..., description="開催日時")


class CouncilMeetingCreate(CouncilMeetingBase):
    """Request schema for creating a council meeting."""

    pass


class CouncilMeetingUpdate(BaseModel):
    """Request schema for updating a council meeting."""

    meeting_number: Optional[int] = Field(None, ge=1)
    title: Optional[str] = Field(None, max_length=255)
    scheduled_at: Optional[datetime] = None


class CouncilMeetingOut(CouncilMeetingBase):
    """Response schema for a council meeting."""

    id: UUID
    council_id: UUID
    agenda_count: int = Field(default=0, description="議題数")
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class CouncilMeetingListItem(BaseModel):
    """Simplified response schema for meeting list."""

    id: UUID
    council_id: UUID
    meeting_number: int
    title: Optional[str] = None
    scheduled_at: datetime
    agenda_count: int = Field(default=0, description="議題数")
    note_count: int = Field(default=0, description="メモ数")
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class CouncilMeetingDetailOut(CouncilMeetingOut):
    """Detailed response schema for a council meeting."""

    agendas: List[CouncilAgendaOut] = Field(
        default_factory=list, description="議題一覧"
    )
    note_count: int = Field(default=0, description="メモ数")

    class Config:
        from_attributes = True


class CalendarMeetingItem(BaseModel):
    """Meeting item for calendar view."""

    id: UUID
    meeting_number: int
    title: Optional[str] = None
    scheduled_at: datetime
    agenda_count: int = Field(default=0, description="議題数")

    class Config:
        from_attributes = True


class CalendarResponse(BaseModel):
    """Response schema for calendar view."""

    council_id: UUID
    view: str = Field(description="week or month")
    start_date: datetime
    end_date: datetime
    meetings: List[CalendarMeetingItem]


class GlobalCalendarMeetingItem(BaseModel):
    """Meeting item for global calendar view (includes council info)."""

    id: UUID
    council_id: UUID
    council_title: str = Field(description="審議会名")
    council_organization: Optional[str] = Field(None, description="所管省庁")
    meeting_number: int
    title: Optional[str] = None
    scheduled_at: datetime
    agenda_count: int = Field(default=0, description="議題数")

    class Config:
        from_attributes = True


class GlobalCalendarResponse(BaseModel):
    """Response schema for global calendar view (all councils)."""

    view: str = Field(description="week or month")
    start_date: datetime
    end_date: datetime
    meetings: List[GlobalCalendarMeetingItem]
    council_count: int = Field(description="表示されている審議会数")
