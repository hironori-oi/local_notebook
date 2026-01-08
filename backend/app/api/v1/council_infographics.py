"""
Council Infographic API endpoints for generating and managing council infographics.
"""
from typing import List
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.core.deps import get_db, get_current_user, parse_uuid
from app.models.council import Council
from app.models.council_meeting import CouncilMeeting
from app.models.council_infographic import CouncilInfographic
from app.models.user import User
from app.schemas.council_infographic import (
    CouncilInfographicCreateRequest,
    CouncilInfographicResponse,
    CouncilInfographicListItem,
    CouncilInfographicListResponse,
)
from app.schemas.infographic import InfographicStructure
from app.services.council_infographic_planner import generate_council_infographic_structure
from app.services.audit import log_action, get_client_info, AuditAction, TargetType

router = APIRouter(prefix="/council-infographics", tags=["council-infographics"])


def _verify_council_access(db: Session, council_id: UUID, user: User) -> Council:
    """Verify that the council exists."""
    council = db.query(Council).filter(Council.id == council_id).first()
    if not council:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="審議会が見つかりません",
        )
    return council


def _verify_meeting_access(db: Session, meeting_id: UUID, council_id: UUID) -> CouncilMeeting:
    """Verify that the meeting exists and belongs to the council."""
    meeting = db.query(CouncilMeeting).filter(
        CouncilMeeting.id == meeting_id,
        CouncilMeeting.council_id == council_id,
    ).first()
    if not meeting:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="開催回が見つかりません",
        )
    return meeting


@router.post("/{council_id}/meeting/{meeting_id}", response_model=CouncilInfographicResponse, status_code=status.HTTP_201_CREATED)
async def create_council_infographic(
    council_id: str,
    meeting_id: str,
    data: CouncilInfographicCreateRequest,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Generate a new infographic from council meeting agendas.

    Uses RAG to retrieve relevant context and LLM to generate the infographic structure.
    """
    ip_address, user_agent = get_client_info(request)
    council_uuid = parse_uuid(council_id, "Council ID")
    meeting_uuid = parse_uuid(meeting_id, "Meeting ID")

    _verify_council_access(db, council_uuid, current_user)
    _verify_meeting_access(db, meeting_uuid, council_uuid)

    # Parse agenda IDs if provided
    agenda_uuids = None
    if data.agenda_ids:
        agenda_uuids = [parse_uuid(aid, "Agenda ID") for aid in data.agenda_ids]

    # Generate infographic structure using LLM
    structure = await generate_council_infographic_structure(
        db=db,
        meeting_id=meeting_uuid,
        topic=data.topic,
        agenda_ids=agenda_uuids,
        user_id=current_user.id,
    )

    # Save to database
    infographic = CouncilInfographic(
        council_id=council_uuid,
        meeting_id=meeting_uuid,
        created_by=current_user.id,
        title=structure.title,
        topic=data.topic,
        structure=structure.model_dump(),
        style_preset=data.style_preset,
    )
    db.add(infographic)
    db.commit()
    db.refresh(infographic)

    # Log action
    log_action(
        db=db,
        action=AuditAction.CREATE_INFOGRAPHIC,
        user_id=current_user.id,
        target_type=TargetType.INFOGRAPHIC,
        target_id=str(infographic.id),
        details={"title": infographic.title, "topic": data.topic, "council_id": council_id, "meeting_id": meeting_id},
        ip_address=ip_address,
        user_agent=user_agent,
    )

    return CouncilInfographicResponse(
        id=str(infographic.id),
        council_id=str(infographic.council_id),
        meeting_id=str(infographic.meeting_id) if infographic.meeting_id else None,
        title=infographic.title,
        topic=infographic.topic,
        structure=InfographicStructure.model_validate(infographic.structure),
        style_preset=infographic.style_preset,
        created_at=infographic.created_at,
        updated_at=infographic.updated_at,
    )


@router.get("/{council_id}/meeting/{meeting_id}", response_model=CouncilInfographicListResponse)
def list_council_infographics(
    council_id: str,
    meeting_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    List all infographics for a council meeting.
    """
    council_uuid = parse_uuid(council_id, "Council ID")
    meeting_uuid = parse_uuid(meeting_id, "Meeting ID")

    _verify_council_access(db, council_uuid, current_user)
    _verify_meeting_access(db, meeting_uuid, council_uuid)

    infographics = db.query(CouncilInfographic).filter(
        CouncilInfographic.meeting_id == meeting_uuid,
        CouncilInfographic.created_by == current_user.id,
    ).order_by(CouncilInfographic.created_at.desc()).all()

    items = [
        CouncilInfographicListItem(
            id=str(inf.id),
            council_id=str(inf.council_id),
            meeting_id=str(inf.meeting_id) if inf.meeting_id else None,
            title=inf.title,
            topic=inf.topic,
            style_preset=inf.style_preset,
            created_at=inf.created_at,
        )
        for inf in infographics
    ]

    return CouncilInfographicListResponse(infographics=items, total=len(items))


@router.get("/detail/{infographic_id}", response_model=CouncilInfographicResponse)
def get_council_infographic(
    infographic_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Get a specific council infographic by ID with full structure.
    """
    inf_uuid = parse_uuid(infographic_id, "Infographic ID")

    infographic = db.query(CouncilInfographic).filter(
        CouncilInfographic.id == inf_uuid,
        CouncilInfographic.created_by == current_user.id,
    ).first()

    if not infographic:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="インフォグラフィックが見つかりません",
        )

    return CouncilInfographicResponse(
        id=str(infographic.id),
        council_id=str(infographic.council_id),
        meeting_id=str(infographic.meeting_id) if infographic.meeting_id else None,
        title=infographic.title,
        topic=infographic.topic,
        structure=InfographicStructure.model_validate(infographic.structure),
        style_preset=infographic.style_preset,
        created_at=infographic.created_at,
        updated_at=infographic.updated_at,
    )


@router.delete("/{infographic_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_council_infographic(
    infographic_id: str,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Delete a council infographic.
    """
    ip_address, user_agent = get_client_info(request)
    inf_uuid = parse_uuid(infographic_id, "Infographic ID")

    infographic = db.query(CouncilInfographic).filter(
        CouncilInfographic.id == inf_uuid,
        CouncilInfographic.created_by == current_user.id,
    ).first()

    if not infographic:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="インフォグラフィックが見つかりません",
        )

    title = infographic.title

    db.delete(infographic)
    db.commit()

    # Log action
    log_action(
        db=db,
        action=AuditAction.DELETE_INFOGRAPHIC,
        user_id=current_user.id,
        target_type=TargetType.INFOGRAPHIC,
        target_id=infographic_id,
        details={"title": title},
        ip_address=ip_address,
        user_agent=user_agent,
    )

    return None
