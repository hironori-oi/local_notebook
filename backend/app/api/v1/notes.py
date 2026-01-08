"""
Notes API endpoints.
"""
from typing import List
from uuid import UUID
import json

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.core.deps import get_db, get_current_user, check_notebook_access
from app.models.notebook import Notebook
from app.models.note import Note
from app.models.message import Message
from app.models.user import User
from app.schemas.note import NoteCreate, NoteUpdate, NoteOut, NoteListResponse

router = APIRouter(prefix="/notes", tags=["notes"])


def _get_note_with_messages(db: Session, note: Note) -> NoteOut:
    """Helper to build NoteOut with associated message content."""
    # Get the assistant message
    assistant_msg = db.query(Message).filter(
        Message.id == note.message_id
    ).first()

    # Try to find the preceding user message
    user_msg = None
    if assistant_msg:
        user_msg = db.query(Message).filter(
            Message.notebook_id == assistant_msg.notebook_id,
            Message.role == "user",
            Message.created_at < assistant_msg.created_at,
        ).order_by(Message.created_at.desc()).first()

    source_refs = None
    if assistant_msg and assistant_msg.source_refs:
        try:
            source_refs = json.loads(assistant_msg.source_refs)
        except json.JSONDecodeError:
            source_refs = []

    return NoteOut(
        id=str(note.id),
        notebook_id=str(note.notebook_id),
        message_id=str(note.message_id),
        title=note.title,
        content=note.content,
        created_by=str(note.created_by),
        created_at=note.created_at.isoformat(),
        updated_at=note.updated_at.isoformat() if note.updated_at else None,
        question=user_msg.content if user_msg else None,
        answer=assistant_msg.content if assistant_msg else None,
        source_refs=source_refs,
    )


@router.get("/notebook/{notebook_id}", response_model=NoteListResponse)
def list_notes(
    notebook_id: str,
    offset: int = Query(0, ge=0, description="Number of items to skip"),
    limit: int = Query(50, ge=1, le=100, description="Maximum items to return"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    List all notes in a notebook with pagination.
    """
    try:
        nb_uuid = UUID(notebook_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="無効なNotebook IDです",
        )

    # Verify notebook access (owner or public)
    check_notebook_access(db, nb_uuid, current_user)

    # Get total count
    total = db.query(Note).filter(Note.notebook_id == nb_uuid).count()

    notes = db.query(Note).filter(
        Note.notebook_id == nb_uuid
    ).order_by(Note.created_at.desc()).offset(offset).limit(limit).all()

    if not notes:
        return NoteListResponse(items=[], total=total, offset=offset, limit=limit)

    # Batch fetch all related messages to avoid N+1 queries
    message_ids = [note.message_id for note in notes]
    messages = db.query(Message).filter(Message.id.in_(message_ids)).all()
    message_map = {msg.id: msg for msg in messages}

    # Batch fetch user messages (preceding messages)
    # Get all messages from this notebook to find user messages
    all_notebook_messages = db.query(Message).filter(
        Message.notebook_id == nb_uuid,
        Message.role == "user"
    ).order_by(Message.created_at.desc()).all()

    # Build result efficiently
    items = []
    for note in notes:
        assistant_msg = message_map.get(note.message_id)

        # Find the preceding user message
        user_msg = None
        if assistant_msg:
            for msg in all_notebook_messages:
                if msg.created_at < assistant_msg.created_at:
                    user_msg = msg
                    break

        source_refs = None
        if assistant_msg and assistant_msg.source_refs:
            try:
                source_refs = json.loads(assistant_msg.source_refs)
            except json.JSONDecodeError:
                source_refs = []

        items.append(NoteOut(
            id=str(note.id),
            notebook_id=str(note.notebook_id),
            message_id=str(note.message_id),
            title=note.title,
            content=note.content,
            created_by=str(note.created_by),
            created_at=note.created_at.isoformat(),
            updated_at=note.updated_at.isoformat() if note.updated_at else None,
            question=user_msg.content if user_msg else None,
            answer=assistant_msg.content if assistant_msg else None,
            source_refs=source_refs,
        ))

    return NoteListResponse(
        items=items,
        total=total,
        offset=offset,
        limit=limit,
    )


@router.post("/{notebook_id}", response_model=NoteOut, status_code=status.HTTP_201_CREATED)
def create_note(
    notebook_id: str,
    data: NoteCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Save an assistant message as a note.
    """
    try:
        nb_uuid = UUID(notebook_id)
        msg_uuid = UUID(data.message_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="無効なIDです",
        )

    # Verify notebook access (owner or public)
    check_notebook_access(db, nb_uuid, current_user)

    # Verify message exists and belongs to this notebook
    message = db.query(Message).filter(
        Message.id == msg_uuid,
        Message.notebook_id == nb_uuid,
        Message.role == "assistant",
    ).first()

    if not message:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="メッセージが見つかりません",
        )

    # Check if note already exists for this message
    existing_note = db.query(Note).filter(
        Note.message_id == msg_uuid
    ).first()

    if existing_note:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="この回答は既に保存されています",
        )

    note = Note(
        notebook_id=nb_uuid,
        message_id=msg_uuid,
        title=data.title,
        created_by=current_user.id,
    )
    db.add(note)
    db.commit()
    db.refresh(note)

    return _get_note_with_messages(db, note)


@router.get("/{note_id}", response_model=NoteOut)
def get_note(
    note_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Get a specific note by ID.
    """
    try:
        note_uuid = UUID(note_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="無効なノートIDです",
        )

    note = db.query(Note).filter(Note.id == note_uuid).first()

    if not note:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="ノートが見つかりません",
        )

    # Verify notebook access (owner or public)
    check_notebook_access(db, note.notebook_id, current_user)

    return _get_note_with_messages(db, note)


@router.patch("/{note_id}", response_model=NoteOut)
def update_note(
    note_id: str,
    data: NoteUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Update a note's title and/or content.
    """
    try:
        note_uuid = UUID(note_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="無効なノートIDです",
        )

    note = db.query(Note).filter(Note.id == note_uuid).first()

    if not note:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="ノートが見つかりません",
        )

    # Verify notebook access (owner or public)
    check_notebook_access(db, note.notebook_id, current_user)

    # Update fields if provided
    if data.title is not None:
        note.title = data.title
    if data.content is not None:
        note.content = data.content

    db.commit()
    db.refresh(note)

    return _get_note_with_messages(db, note)


@router.delete("/{note_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_note(
    note_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Delete a note.
    """
    try:
        note_uuid = UUID(note_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="無効なノートIDです",
        )

    note = db.query(Note).filter(Note.id == note_uuid).first()

    if not note:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="ノートが見つかりません",
        )

    # Verify notebook access (owner or public)
    check_notebook_access(db, note.notebook_id, current_user)

    db.delete(note)
    db.commit()

    return None
