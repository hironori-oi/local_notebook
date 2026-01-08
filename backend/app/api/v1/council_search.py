"""
Council search API endpoints.

Provides search functionality across councils and meetings.
"""
from typing import List, Optional
from uuid import UUID
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy import or_, func
from sqlalchemy.orm import Session

from app.core.deps import get_db, get_current_user, check_council_access
from app.models.council import Council
from app.models.council_meeting import CouncilMeeting
from app.models.council_note import CouncilNote
from app.models.user import User

router = APIRouter(prefix="/council-search", tags=["council-search"])


class CouncilSearchResult(BaseModel):
    """Search result item."""
    id: str
    type: str = Field(description="council, meeting, or note")
    title: str
    description: Optional[str] = None
    council_id: Optional[str] = None
    council_title: Optional[str] = None
    meeting_id: Optional[str] = None
    meeting_number: Optional[int] = None
    relevance_score: float = Field(description="Relevance score (higher is better)")
    created_at: datetime
    match_context: Optional[str] = Field(None, description="Text excerpt showing the match")


class CouncilSearchResponse(BaseModel):
    """Search response."""
    query: str
    council_id: Optional[str] = None
    results: List[CouncilSearchResult]
    total: int


def _parse_uuid_optional(value: Optional[str], name: str = "ID") -> Optional[UUID]:
    """Parse optional string to UUID."""
    if not value:
        return None
    try:
        return UUID(value)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"無効な{name}です",
        )


def _calculate_relevance(text: str, query: str, field_weight: float = 1.0) -> float:
    """Calculate relevance score based on text match."""
    if not text or not query:
        return 0.0

    text_lower = text.lower()
    query_lower = query.lower()

    # Exact match
    if query_lower == text_lower:
        return 3.0 * field_weight

    # Contains query
    if query_lower in text_lower:
        # Boost if query is at the start
        if text_lower.startswith(query_lower):
            return 2.5 * field_weight
        return 2.0 * field_weight

    # Check for individual words
    query_words = query_lower.split()
    matched_words = sum(1 for word in query_words if word in text_lower)
    if matched_words > 0:
        return (1.0 + (matched_words / len(query_words))) * field_weight

    return 0.0


def _extract_match_context(text: str, query: str, context_length: int = 100) -> Optional[str]:
    """Extract context around the matched query."""
    if not text or not query:
        return None

    text_lower = text.lower()
    query_lower = query.lower()

    pos = text_lower.find(query_lower)
    if pos == -1:
        # Try to find any word
        for word in query_lower.split():
            pos = text_lower.find(word)
            if pos != -1:
                break

    if pos == -1:
        return text[:context_length] + "..." if len(text) > context_length else text

    start = max(0, pos - context_length // 2)
    end = min(len(text), pos + len(query) + context_length // 2)

    context = text[start:end]
    if start > 0:
        context = "..." + context
    if end < len(text):
        context = context + "..."

    return context


@router.get("", response_model=CouncilSearchResponse)
def search_councils(
    q: str = Query(..., min_length=1, max_length=200, description="Search query"),
    council_id: Optional[str] = Query(None, description="Limit search to specific council"),
    limit: int = Query(20, ge=1, le=100, description="Maximum results"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Search councils and meetings.

    - Without council_id: Search across all accessible councils
    - With council_id: Search within specific council only
    """
    council_uuid = _parse_uuid_optional(council_id, "審議会ID")

    # If council_id provided, verify access
    if council_uuid:
        check_council_access(db, council_uuid, current_user)

    results: List[CouncilSearchResult] = []
    query = q.strip()

    # Search councils (only if not searching within a specific council)
    if not council_uuid:
        councils = (
            db.query(Council)
            .filter(
                or_(
                    Council.owner_id == current_user.id,
                    Council.is_public == True
                ),
                or_(
                    Council.title.ilike(f"%{query}%"),
                    Council.description.ilike(f"%{query}%"),
                    Council.organization.ilike(f"%{query}%"),
                )
            )
            .all()
        )

        for council in councils:
            # Calculate relevance
            title_score = _calculate_relevance(council.title, query, 2.0)
            desc_score = _calculate_relevance(council.description or "", query, 1.0)
            org_score = _calculate_relevance(council.organization or "", query, 1.5)
            relevance = max(title_score, desc_score, org_score)

            if relevance > 0:
                match_context = None
                if council.description and query.lower() in council.description.lower():
                    match_context = _extract_match_context(council.description, query)

                results.append(CouncilSearchResult(
                    id=str(council.id),
                    type="council",
                    title=council.title,
                    description=council.description,
                    relevance_score=relevance,
                    created_at=council.created_at,
                    match_context=match_context,
                ))

    # Search meetings
    meeting_query = db.query(CouncilMeeting).join(
        Council, CouncilMeeting.council_id == Council.id
    ).filter(
        or_(
            Council.owner_id == current_user.id,
            Council.is_public == True
        ),
    )

    if council_uuid:
        meeting_query = meeting_query.filter(CouncilMeeting.council_id == council_uuid)

    meeting_query = meeting_query.filter(
        or_(
            CouncilMeeting.title.ilike(f"%{query}%"),
            CouncilMeeting.materials_summary.ilike(f"%{query}%"),
            CouncilMeeting.minutes_summary.ilike(f"%{query}%"),
        )
    )

    meetings = meeting_query.all()

    for meeting in meetings:
        # Get council info
        council = db.query(Council).filter(Council.id == meeting.council_id).first()

        # Calculate relevance
        title_score = _calculate_relevance(meeting.title or "", query, 2.0)
        materials_score = _calculate_relevance(meeting.materials_summary or "", query, 1.5)
        minutes_score = _calculate_relevance(meeting.minutes_summary or "", query, 1.5)
        relevance = max(title_score, materials_score, minutes_score)

        if relevance > 0:
            # Find match context
            match_context = None
            if meeting.materials_summary and query.lower() in meeting.materials_summary.lower():
                match_context = _extract_match_context(meeting.materials_summary, query)
            elif meeting.minutes_summary and query.lower() in meeting.minutes_summary.lower():
                match_context = _extract_match_context(meeting.minutes_summary, query)

            meeting_title = f"第{meeting.meeting_number}回"
            if meeting.title:
                meeting_title += f" {meeting.title}"

            results.append(CouncilSearchResult(
                id=str(meeting.id),
                type="meeting",
                title=meeting_title,
                description=meeting.materials_summary[:200] + "..." if meeting.materials_summary and len(meeting.materials_summary) > 200 else meeting.materials_summary,
                council_id=str(meeting.council_id),
                council_title=council.title if council else None,
                meeting_id=str(meeting.id),
                meeting_number=meeting.meeting_number,
                relevance_score=relevance,
                created_at=meeting.created_at,
                match_context=match_context,
            ))

    # Search notes
    note_query = db.query(CouncilNote).join(
        Council, CouncilNote.council_id == Council.id
    ).filter(
        or_(
            Council.owner_id == current_user.id,
            Council.is_public == True
        ),
    )

    if council_uuid:
        note_query = note_query.filter(CouncilNote.council_id == council_uuid)

    note_query = note_query.filter(
        or_(
            CouncilNote.title.ilike(f"%{query}%"),
            CouncilNote.content.ilike(f"%{query}%"),
        )
    )

    notes = note_query.all()

    for note in notes:
        council = db.query(Council).filter(Council.id == note.council_id).first()

        # Get meeting info if applicable
        meeting_number = None
        if note.meeting_id:
            meeting = db.query(CouncilMeeting).filter(CouncilMeeting.id == note.meeting_id).first()
            if meeting:
                meeting_number = meeting.meeting_number

        # Calculate relevance
        title_score = _calculate_relevance(note.title, query, 2.0)
        content_score = _calculate_relevance(note.content, query, 1.0)
        relevance = max(title_score, content_score)

        if relevance > 0:
            match_context = None
            if query.lower() in note.content.lower():
                match_context = _extract_match_context(note.content, query)

            results.append(CouncilSearchResult(
                id=str(note.id),
                type="note",
                title=note.title,
                description=note.content[:200] + "..." if len(note.content) > 200 else note.content,
                council_id=str(note.council_id),
                council_title=council.title if council else None,
                meeting_id=str(note.meeting_id) if note.meeting_id else None,
                meeting_number=meeting_number,
                relevance_score=relevance,
                created_at=note.created_at,
                match_context=match_context,
            ))

    # Sort by relevance and limit
    results.sort(key=lambda x: x.relevance_score, reverse=True)
    results = results[:limit]

    return CouncilSearchResponse(
        query=query,
        council_id=council_id,
        results=results,
        total=len(results),
    )
