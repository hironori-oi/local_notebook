"""Schemas for document checker API."""
from datetime import datetime
from typing import List, Optional, Dict, Any
from uuid import UUID

from pydantic import BaseModel, Field


class CheckTypeInfo(BaseModel):
    """Information about a check type."""
    id: str
    name: str
    description: str
    default_enabled: bool


class DocumentCheckIssueOut(BaseModel):
    """Output schema for a document check issue."""
    id: UUID
    category: str
    severity: str
    page_or_slide: Optional[int] = None
    line_number: Optional[int] = None
    original_text: str
    suggested_text: Optional[str] = None
    explanation: Optional[str] = None
    is_accepted: Optional[bool] = None
    created_at: datetime

    class Config:
        from_attributes = True


class DocumentCheckSummary(BaseModel):
    """Summary of a document check (for list view)."""
    id: UUID
    filename: str
    file_type: str
    status: str
    issue_count: int = 0
    error_count: int = 0
    warning_count: int = 0
    info_count: int = 0
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class DocumentCheckDetail(BaseModel):
    """Detailed document check result."""
    id: UUID
    filename: str
    file_type: str
    original_text: str
    page_count: Optional[int] = None
    status: str
    error_message: Optional[str] = None
    check_types: List[str]
    issues: List[DocumentCheckIssueOut]
    issue_count: int = 0
    error_count: int = 0
    warning_count: int = 0
    info_count: int = 0
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class DocumentCheckUploadResponse(BaseModel):
    """Response for document upload."""
    id: UUID
    filename: str
    file_type: str
    status: str
    message: str


class DocumentCheckListResponse(BaseModel):
    """Response for document list."""
    items: List[DocumentCheckSummary]
    total: int
    offset: int
    limit: int


class IssueUpdateRequest(BaseModel):
    """Request to update an issue's status."""
    is_accepted: bool


class IssueUpdateResponse(BaseModel):
    """Response for issue update."""
    id: UUID
    is_accepted: bool
    message: str


class UserCheckPreferenceOut(BaseModel):
    """Output schema for user check preferences."""
    default_check_types: List[str]
    custom_terminology: Optional[Dict[str, str]] = None

    class Config:
        from_attributes = True


class UserCheckPreferenceUpdate(BaseModel):
    """Request to update user check preferences."""
    default_check_types: Optional[List[str]] = None
    custom_terminology: Optional[Dict[str, str]] = None


class CheckTypesResponse(BaseModel):
    """Response for check types list."""
    check_types: List[CheckTypeInfo]
