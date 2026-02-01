"""
Council meeting management API endpoints.

Provides CRUD operations for council meetings (開催回).
"""

from typing import List
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core.deps import check_council_access, get_current_user, get_db, parse_uuid
from app.models.council import Council
from app.models.council_agenda_item import CouncilAgendaItem
from app.models.council_agenda_material import CouncilAgendaMaterial
from app.models.council_meeting import CouncilMeeting
from app.models.council_note import CouncilNote
from app.models.user import User
from app.schemas.council_agenda import CouncilAgendaMaterialOut, CouncilAgendaOut
from app.schemas.council_meeting import (
    CouncilMeetingCreate,
    CouncilMeetingDetailOut,
    CouncilMeetingListItem,
    CouncilMeetingOut,
    CouncilMeetingUpdate,
)
from app.services.audit import AuditAction, TargetType, get_client_info, log_action

router = APIRouter(prefix="/council-meetings", tags=["council-meetings"])


def _get_aggregated_materials_status(agenda: CouncilAgendaItem) -> str:
    """Get aggregated processing status from materials array."""
    if not agenda.materials or len(agenda.materials) == 0:
        # No materials in array, use legacy status
        return agenda.materials_processing_status

    statuses = [m.processing_status for m in agenda.materials]
    if any(s == "failed" for s in statuses):
        return "failed"
    if any(s == "processing" for s in statuses):
        return "processing"
    if any(s == "pending" for s in statuses):
        return "pending"
    if all(s == "completed" for s in statuses):
        return "completed"
    return "completed"


def _build_material_out(material: CouncilAgendaMaterial) -> CouncilAgendaMaterialOut:
    """Build material output schema."""
    return CouncilAgendaMaterialOut(
        id=material.id,
        agenda_id=material.agenda_id,
        material_number=material.material_number,
        title=material.title,
        source_type=material.source_type,
        url=material.url,
        original_filename=material.original_filename,
        processing_status=material.processing_status,
        has_summary=bool(material.summary),
        created_at=material.created_at,
        updated_at=material.updated_at,
    )


@router.get("/council/{council_id}", response_model=List[CouncilMeetingListItem])
def list_council_meetings(
    council_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    List all meetings for a council.
    """
    council_uuid = parse_uuid(council_id, "council ID")
    check_council_access(db, council_uuid, current_user)

    # Build note count subquery
    note_count_subq = (
        db.query(CouncilNote.meeting_id, func.count(CouncilNote.id).label("note_count"))
        .filter(CouncilNote.meeting_id.isnot(None))
        .group_by(CouncilNote.meeting_id)
        .subquery()
    )

    # Build agenda count subquery
    agenda_count_subq = (
        db.query(
            CouncilAgendaItem.meeting_id,
            func.count(CouncilAgendaItem.id).label("agenda_count"),
        )
        .group_by(CouncilAgendaItem.meeting_id)
        .subquery()
    )

    query = (
        db.query(
            CouncilMeeting.id,
            CouncilMeeting.council_id,
            CouncilMeeting.meeting_number,
            CouncilMeeting.title,
            CouncilMeeting.scheduled_at,
            CouncilMeeting.created_at,
            CouncilMeeting.updated_at,
            func.coalesce(note_count_subq.c.note_count, 0).label("note_count"),
            func.coalesce(agenda_count_subq.c.agenda_count, 0).label("agenda_count"),
        )
        .outerjoin(note_count_subq, CouncilMeeting.id == note_count_subq.c.meeting_id)
        .outerjoin(
            agenda_count_subq, CouncilMeeting.id == agenda_count_subq.c.meeting_id
        )
        .filter(CouncilMeeting.council_id == council_uuid)
        .order_by(CouncilMeeting.scheduled_at.desc())
    )

    results = query.all()

    meetings = []
    for row in results:
        meetings.append(
            CouncilMeetingListItem(
                id=row.id,
                council_id=row.council_id,
                meeting_number=row.meeting_number,
                title=row.title,
                scheduled_at=row.scheduled_at,
                agenda_count=row.agenda_count,
                note_count=row.note_count,
                created_at=row.created_at,
                updated_at=row.updated_at,
            )
        )

    return meetings


@router.get("/{meeting_id}", response_model=CouncilMeetingOut)
def get_council_meeting(
    meeting_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Get a specific council meeting by ID.
    """
    meeting_uuid = parse_uuid(meeting_id, "meeting ID")

    meeting = db.query(CouncilMeeting).filter(CouncilMeeting.id == meeting_uuid).first()
    if not meeting:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="開催回が見つかりません",
        )

    # Check council access
    check_council_access(db, meeting.council_id, current_user)

    # Get agenda count
    agenda_count = (
        db.query(func.count(CouncilAgendaItem.id))
        .filter(CouncilAgendaItem.meeting_id == meeting.id)
        .scalar()
        or 0
    )

    return CouncilMeetingOut(
        id=meeting.id,
        council_id=meeting.council_id,
        meeting_number=meeting.meeting_number,
        title=meeting.title,
        scheduled_at=meeting.scheduled_at,
        agenda_count=agenda_count,
        created_at=meeting.created_at,
        updated_at=meeting.updated_at,
    )


@router.get("/{meeting_id}/detail", response_model=CouncilMeetingDetailOut)
def get_council_meeting_detail(
    meeting_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Get detailed information for a council meeting, including agendas.
    """
    meeting_uuid = parse_uuid(meeting_id, "meeting ID")

    meeting = db.query(CouncilMeeting).filter(CouncilMeeting.id == meeting_uuid).first()
    if not meeting:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="開催回が見つかりません",
        )

    # Check council access
    check_council_access(db, meeting.council_id, current_user)

    # Get note count
    note_count = (
        db.query(func.count(CouncilNote.id))
        .filter(CouncilNote.meeting_id == meeting.id)
        .scalar()
        or 0
    )

    # Get agendas
    agendas = (
        db.query(CouncilAgendaItem)
        .filter(CouncilAgendaItem.meeting_id == meeting.id)
        .order_by(CouncilAgendaItem.agenda_number)
        .all()
    )

    agenda_list = [
        CouncilAgendaOut(
            id=agenda.id,
            meeting_id=agenda.meeting_id,
            agenda_number=agenda.agenda_number,
            title=agenda.title,
            materials_url=agenda.materials_url,
            minutes_url=agenda.minutes_url,
            materials_processing_status=_get_aggregated_materials_status(agenda),
            minutes_processing_status=agenda.minutes_processing_status,
            has_materials_summary=bool(agenda.materials_summary)
            or any(m.summary for m in agenda.materials if agenda.materials),
            has_minutes_summary=bool(agenda.minutes_summary),
            materials_count=len(agenda.materials) if agenda.materials else 0,
            materials=(
                [_build_material_out(m) for m in agenda.materials]
                if agenda.materials
                else []
            ),
            created_at=agenda.created_at,
            updated_at=agenda.updated_at,
        )
        for agenda in agendas
    ]

    return CouncilMeetingDetailOut(
        id=meeting.id,
        council_id=meeting.council_id,
        meeting_number=meeting.meeting_number,
        title=meeting.title,
        scheduled_at=meeting.scheduled_at,
        agenda_count=len(agendas),
        agendas=agenda_list,
        note_count=note_count,
        created_at=meeting.created_at,
        updated_at=meeting.updated_at,
    )


@router.post(
    "/council/{council_id}",
    response_model=CouncilMeetingOut,
    status_code=status.HTTP_201_CREATED,
)
def create_council_meeting(
    council_id: str,
    data: CouncilMeetingCreate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Create a new council meeting.

    Agenda items should be added separately using the /council-agendas endpoint.
    """
    ip_address, user_agent = get_client_info(request)
    council_uuid = parse_uuid(council_id, "council ID")

    check_council_access(db, council_uuid, current_user)

    # Check if meeting number already exists
    existing = (
        db.query(CouncilMeeting)
        .filter(
            CouncilMeeting.council_id == council_uuid,
            CouncilMeeting.meeting_number == data.meeting_number,
        )
        .first()
    )
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Meeting number {data.meeting_number} already exists",
        )

    meeting = CouncilMeeting(
        council_id=council_uuid,
        meeting_number=data.meeting_number,
        title=data.title,
        scheduled_at=data.scheduled_at,
    )
    db.add(meeting)
    db.commit()
    db.refresh(meeting)

    log_action(
        db=db,
        action=AuditAction.CREATE_COUNCIL_MEETING,
        user_id=current_user.id,
        target_type=TargetType.COUNCIL_MEETING,
        target_id=str(meeting.id),
        details={
            "council_id": council_id,
            "meeting_number": meeting.meeting_number,
            "title": meeting.title,
        },
        ip_address=ip_address,
        user_agent=user_agent,
    )

    return CouncilMeetingOut(
        id=meeting.id,
        council_id=meeting.council_id,
        meeting_number=meeting.meeting_number,
        title=meeting.title,
        scheduled_at=meeting.scheduled_at,
        agenda_count=0,
        created_at=meeting.created_at,
        updated_at=meeting.updated_at,
    )


@router.patch("/{meeting_id}", response_model=CouncilMeetingOut)
def update_council_meeting(
    meeting_id: str,
    data: CouncilMeetingUpdate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Update a council meeting.
    """
    ip_address, user_agent = get_client_info(request)
    meeting_uuid = parse_uuid(meeting_id, "meeting ID")

    meeting = db.query(CouncilMeeting).filter(CouncilMeeting.id == meeting_uuid).first()
    if not meeting:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="開催回が見つかりません",
        )

    check_council_access(db, meeting.council_id, current_user)

    update_details = {}

    if (
        data.meeting_number is not None
        and data.meeting_number != meeting.meeting_number
    ):
        # Check if new number already exists
        existing = (
            db.query(CouncilMeeting)
            .filter(
                CouncilMeeting.council_id == meeting.council_id,
                CouncilMeeting.meeting_number == data.meeting_number,
                CouncilMeeting.id != meeting.id,
            )
            .first()
        )
        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Meeting number {data.meeting_number} already exists",
            )
        meeting.meeting_number = data.meeting_number
        update_details["meeting_number"] = data.meeting_number

    if data.title is not None:
        meeting.title = data.title
        update_details["title"] = data.title

    if data.scheduled_at is not None:
        meeting.scheduled_at = data.scheduled_at
        update_details["scheduled_at"] = str(data.scheduled_at)

    db.commit()
    db.refresh(meeting)

    if update_details:
        log_action(
            db=db,
            action=AuditAction.UPDATE_COUNCIL_MEETING,
            user_id=current_user.id,
            target_type=TargetType.COUNCIL_MEETING,
            target_id=meeting_id,
            details=update_details,
            ip_address=ip_address,
            user_agent=user_agent,
        )

    # Get agenda count
    agenda_count = (
        db.query(func.count(CouncilAgendaItem.id))
        .filter(CouncilAgendaItem.meeting_id == meeting.id)
        .scalar()
        or 0
    )

    return CouncilMeetingOut(
        id=meeting.id,
        council_id=meeting.council_id,
        meeting_number=meeting.meeting_number,
        title=meeting.title,
        scheduled_at=meeting.scheduled_at,
        agenda_count=agenda_count,
        created_at=meeting.created_at,
        updated_at=meeting.updated_at,
    )


@router.delete("/{meeting_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_council_meeting(
    meeting_id: str,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Delete a council meeting and all associated agendas and notes.
    """
    ip_address, user_agent = get_client_info(request)
    meeting_uuid = parse_uuid(meeting_id, "meeting ID")

    meeting = db.query(CouncilMeeting).filter(CouncilMeeting.id == meeting_uuid).first()
    if not meeting:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="開催回が見つかりません",
        )

    # Check council access (require owner)
    check_council_access(db, meeting.council_id, current_user, require_owner=True)

    meeting_number = meeting.meeting_number
    council_id = str(meeting.council_id)

    db.delete(meeting)
    db.commit()

    log_action(
        db=db,
        action=AuditAction.DELETE_COUNCIL_MEETING,
        user_id=current_user.id,
        target_type=TargetType.COUNCIL_MEETING,
        target_id=meeting_id,
        details={"council_id": council_id, "meeting_number": meeting_number},
        ip_address=ip_address,
        user_agent=user_agent,
    )

    return None
