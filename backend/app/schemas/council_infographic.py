"""
Council Infographic schemas for request/response validation.

Defines the structure for council infographic generation and display.
"""
from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, Field

# Reuse the infographic structure from main infographics
from app.schemas.infographic import InfographicStructure


# =============================================================================
# API Request/Response Schemas
# =============================================================================

class CouncilInfographicCreateRequest(BaseModel):
    """Request schema for creating a new council infographic."""
    topic: str = Field(
        ...,
        min_length=1,
        max_length=500,
        description="Topic or prompt describing what the infographic should cover"
    )
    agenda_ids: List[str] = Field(
        default_factory=list,
        description="Agenda item IDs to use for context. Empty means all agendas in the meeting."
    )
    style_preset: str = Field(
        "default",
        description="Style preset for the infographic"
    )


class CouncilInfographicResponse(BaseModel):
    """Response schema for a complete council infographic."""
    id: str
    council_id: str
    meeting_id: Optional[str] = None
    title: str
    topic: Optional[str] = None
    structure: InfographicStructure
    style_preset: str = "default"
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class CouncilInfographicListItem(BaseModel):
    """Response schema for listing council infographics (without full structure)."""
    id: str
    council_id: str
    meeting_id: Optional[str] = None
    title: str
    topic: Optional[str] = None
    style_preset: str = "default"
    created_at: datetime

    class Config:
        from_attributes = True


class CouncilInfographicListResponse(BaseModel):
    """Response schema for listing council infographics."""
    infographics: List[CouncilInfographicListItem]
    total: int
