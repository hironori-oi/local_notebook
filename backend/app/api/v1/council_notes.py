"""
Council notes management API endpoints.

Provides CRUD operations for council notes (メモ).
Notes can be associated with a council (council-level) or a specific meeting (meeting-level).
"""

from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy.orm import Session

from app.core.deps import check_council_access, get_current_user, get_db, parse_uuid
from app.models.council import Council
from app.models.council_meeting import CouncilMeeting
from app.models.council_note import CouncilNote
from app.models.user import User
from app.schemas.council_note import (
    CouncilNoteCreate,
    CouncilNoteListItem,
    CouncilNoteOut,
    CouncilNoteUpdate,
)
from app.services.audit import AuditAction, TargetType, get_client_info, log_action

router = APIRouter(prefix="/council-notes", tags=["council-notes"])


@router.get("/council/{council_id}", response_model=List[CouncilNoteListItem])
def list_council_notes(
    council_id: str,
    meeting_id: Optional[str] = Query(
        None,
        description="Filter by meeting ID. Use 'council' for council-level notes only.",
    ),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    List notes for a council.

    - No meeting_id: All notes (council-level + meeting-level)
    - meeting_id='council': Council-level notes only (meeting_id IS NULL)
    - meeting_id=<uuid>: Notes for specific meeting only
    """
    council_uuid = parse_uuid(council_id, "審議会ID")
    check_council_access(db, council_uuid, current_user)

    query = (
        db.query(CouncilNote)
        .join(User, CouncilNote.user_id == User.id)
        .filter(CouncilNote.council_id == council_uuid)
    )

    if meeting_id:
        if meeting_id.lower() == "council":
            # Council-level notes only
            query = query.filter(CouncilNote.meeting_id.is_(None))
        else:
            # Specific meeting notes
            meeting_uuid = parse_uuid(meeting_id, "開催回ID")
            query = query.filter(CouncilNote.meeting_id == meeting_uuid)

    query = query.order_by(CouncilNote.created_at.desc())
    notes = query.all()

    result = []
    for note in notes:
        # Get meeting number if applicable
        meeting_number = None
        if note.meeting_id:
            meeting = (
                db.query(CouncilMeeting)
                .filter(CouncilMeeting.id == note.meeting_id)
                .first()
            )
            if meeting:
                meeting_number = meeting.meeting_number

        # Get user display name
        user = db.query(User).filter(User.id == note.user_id).first()

        # Create content preview
        content_preview = (
            note.content[:100] + "..." if len(note.content) > 100 else note.content
        )

        result.append(
            CouncilNoteListItem(
                id=note.id,
                council_id=note.council_id,
                meeting_id=note.meeting_id,
                meeting_number=meeting_number,
                user_id=note.user_id,
                user_display_name=user.display_name if user else "Unknown",
                title=note.title,
                content_preview=content_preview,
                created_at=note.created_at,
                updated_at=note.updated_at,
            )
        )

    return result


@router.get("/{note_id}", response_model=CouncilNoteOut)
def get_council_note(
    note_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Get a specific council note by ID.
    """
    note_uuid = parse_uuid(note_id, "メモID")

    note = db.query(CouncilNote).filter(CouncilNote.id == note_uuid).first()
    if not note:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="メモが見つかりません",
        )

    # Check council access
    check_council_access(db, note.council_id, current_user)

    return note


@router.post("", response_model=CouncilNoteOut, status_code=status.HTTP_201_CREATED)
def create_council_note(
    data: CouncilNoteCreate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Create a new council note.

    - If meeting_id is provided, creates a meeting-level note
    - If meeting_id is not provided, creates a council-level note
    """
    ip_address, user_agent = get_client_info(request)

    # Check council access
    check_council_access(db, data.council_id, current_user)

    # If meeting_id provided, verify it belongs to the council
    if data.meeting_id:
        meeting = (
            db.query(CouncilMeeting)
            .filter(CouncilMeeting.id == data.meeting_id)
            .first()
        )
        if not meeting:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="開催回が見つかりません",
            )
        if meeting.council_id != data.council_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="指定された開催回はこの審議会に属していません",
            )

    note = CouncilNote(
        council_id=data.council_id,
        meeting_id=data.meeting_id,
        user_id=current_user.id,
        title=data.title,
        content=data.content,
    )
    db.add(note)
    db.commit()
    db.refresh(note)

    log_action(
        db=db,
        action=AuditAction.CREATE_COUNCIL_NOTE,
        user_id=current_user.id,
        target_type=TargetType.COUNCIL_NOTE,
        target_id=str(note.id),
        details={
            "council_id": str(data.council_id),
            "meeting_id": str(data.meeting_id) if data.meeting_id else None,
            "title": note.title,
        },
        ip_address=ip_address,
        user_agent=user_agent,
    )

    return note


@router.patch("/{note_id}", response_model=CouncilNoteOut)
def update_council_note(
    note_id: str,
    data: CouncilNoteUpdate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Update a council note.

    Users can only update their own notes.
    """
    ip_address, user_agent = get_client_info(request)
    note_uuid = parse_uuid(note_id, "メモID")

    note = db.query(CouncilNote).filter(CouncilNote.id == note_uuid).first()
    if not note:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="メモが見つかりません",
        )

    # Check council access
    check_council_access(db, note.council_id, current_user)

    # Users can only update their own notes
    if note.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="自分のメモのみ編集できます",
        )

    update_details = {}

    if data.title is not None:
        note.title = data.title
        update_details["title"] = data.title

    if data.content is not None:
        note.content = data.content
        update_details["content_updated"] = True

    db.commit()
    db.refresh(note)

    if update_details:
        log_action(
            db=db,
            action=AuditAction.UPDATE_COUNCIL_NOTE,
            user_id=current_user.id,
            target_type=TargetType.COUNCIL_NOTE,
            target_id=note_id,
            details=update_details,
            ip_address=ip_address,
            user_agent=user_agent,
        )

    return note


@router.delete("/{note_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_council_note(
    note_id: str,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Delete a council note.

    Users can only delete their own notes.
    Council owner can delete any note.
    """
    ip_address, user_agent = get_client_info(request)
    note_uuid = parse_uuid(note_id, "メモID")

    note = db.query(CouncilNote).filter(CouncilNote.id == note_uuid).first()
    if not note:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="メモが見つかりません",
        )

    # Check council access
    council = db.query(Council).filter(Council.id == note.council_id).first()
    is_council_owner = council and council.owner_id == current_user.id

    # Users can delete their own notes, council owners can delete any note
    if note.user_id != current_user.id and not is_council_owner:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="自分のメモのみ削除できます",
        )

    note_title = note.title

    db.delete(note)
    db.commit()

    log_action(
        db=db,
        action=AuditAction.DELETE_COUNCIL_NOTE,
        user_id=current_user.id,
        target_type=TargetType.COUNCIL_NOTE,
        target_id=note_id,
        details={"title": note_title},
        ip_address=ip_address,
        user_agent=user_agent,
    )

    return None
