"""
Slides API endpoints for generating and managing slide decks.
"""
import os
from typing import List
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.core.deps import get_db, get_current_user
from app.models.notebook import Notebook
from app.models.slide_deck import SlideDeck
from app.models.user import User
from app.schemas.slide import (
    SlideDeckCreateRequest,
    SlideDeckResponse,
    SlideDeckListItem,
    SlideDeckListResponse,
    SlideOutline,
)
from app.services.slide_planner import generate_slide_outline
from app.services.slide_builder import build_pptx, get_pptx_output_path, delete_pptx_file
from app.services.audit import log_action, get_client_info, AuditAction, TargetType

router = APIRouter(prefix="/slides", tags=["slides"])


def _parse_uuid(value: str, name: str = "ID") -> UUID:
    """Parse a string to UUID, raising HTTPException on failure."""
    try:
        return UUID(value)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"無効な{name}です",
        )


def _verify_notebook_ownership(db: Session, notebook_id: UUID, user_id: UUID) -> Notebook:
    """Verify that the notebook exists and is owned by the user."""
    notebook = db.query(Notebook).filter(
        Notebook.id == notebook_id,
        Notebook.owner_id == user_id,
    ).first()

    if not notebook:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Notebookが見つかりません",
        )
    return notebook


@router.post("/{notebook_id}", response_model=SlideDeckResponse, status_code=status.HTTP_201_CREATED)
async def create_slide_deck(
    notebook_id: str,
    data: SlideDeckCreateRequest,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Generate a new slide deck from notebook sources.

    Uses RAG to retrieve relevant context, LLM to generate the slide outline,
    and python-pptx to create the PPTX file.
    """
    ip_address, user_agent = get_client_info(request)
    nb_uuid = _parse_uuid(notebook_id, "Notebook ID")
    _verify_notebook_ownership(db, nb_uuid, current_user.id)

    # Parse source IDs if provided
    source_uuids = None
    if data.source_ids:
        source_uuids = [_parse_uuid(sid, "Source ID") for sid in data.source_ids]

    # Generate slide outline using LLM
    outline = await generate_slide_outline(
        db=db,
        notebook_id=nb_uuid,
        topic=data.topic,
        source_ids=source_uuids,
        user_id=current_user.id,
        target_slides=data.target_slides,
    )

    # Save to database first (to get the ID)
    slide_deck = SlideDeck(
        notebook_id=nb_uuid,
        created_by=current_user.id,
        title=outline.title,
        topic=data.topic,
        outline=outline.model_dump(),
        slide_count=len(outline.slides),
    )
    db.add(slide_deck)
    db.commit()
    db.refresh(slide_deck)

    # Build PPTX file
    pptx_path = get_pptx_output_path(str(nb_uuid), str(slide_deck.id))
    try:
        build_pptx(outline, pptx_path)
        slide_deck.pptx_path = pptx_path
        db.commit()
        pptx_available = True
    except Exception as e:
        # Log error but don't fail - the outline is still useful
        import logging
        logging.error(f"Failed to build PPTX: {e}")
        pptx_available = False

    # Log action
    log_action(
        db=db,
        action=AuditAction.CREATE_SLIDE_DECK,
        user_id=current_user.id,
        target_type=TargetType.SLIDE_DECK,
        target_id=str(slide_deck.id),
        details={
            "title": slide_deck.title,
            "topic": data.topic,
            "slide_count": len(outline.slides),
        },
        ip_address=ip_address,
        user_agent=user_agent,
    )

    return SlideDeckResponse(
        id=str(slide_deck.id),
        notebook_id=str(slide_deck.notebook_id),
        title=slide_deck.title,
        topic=slide_deck.topic,
        outline=SlideOutline.model_validate(slide_deck.outline),
        slide_count=slide_deck.slide_count,
        pptx_available=pptx_available,
        created_at=slide_deck.created_at,
        updated_at=slide_deck.updated_at,
    )


@router.get("/{notebook_id}", response_model=SlideDeckListResponse)
def list_slide_decks(
    notebook_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    List all slide decks for a notebook.
    """
    nb_uuid = _parse_uuid(notebook_id, "Notebook ID")
    _verify_notebook_ownership(db, nb_uuid, current_user.id)

    decks = db.query(SlideDeck).filter(
        SlideDeck.notebook_id == nb_uuid,
        SlideDeck.created_by == current_user.id,
    ).order_by(SlideDeck.created_at.desc()).all()

    items = [
        SlideDeckListItem(
            id=str(deck.id),
            notebook_id=str(deck.notebook_id),
            title=deck.title,
            topic=deck.topic,
            slide_count=deck.slide_count,
            pptx_available=deck.pptx_path is not None and os.path.exists(deck.pptx_path),
            created_at=deck.created_at,
        )
        for deck in decks
    ]

    return SlideDeckListResponse(slide_decks=items, total=len(items))


@router.get("/detail/{slide_deck_id}", response_model=SlideDeckResponse)
def get_slide_deck(
    slide_deck_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Get a specific slide deck by ID with full outline.
    """
    deck_uuid = _parse_uuid(slide_deck_id, "SlideDeck ID")

    slide_deck = db.query(SlideDeck).filter(
        SlideDeck.id == deck_uuid,
        SlideDeck.created_by == current_user.id,
    ).first()

    if not slide_deck:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="スライドデッキが見つかりません",
        )

    pptx_available = (
        slide_deck.pptx_path is not None and
        os.path.exists(slide_deck.pptx_path)
    )

    return SlideDeckResponse(
        id=str(slide_deck.id),
        notebook_id=str(slide_deck.notebook_id),
        title=slide_deck.title,
        topic=slide_deck.topic,
        outline=SlideOutline.model_validate(slide_deck.outline),
        slide_count=slide_deck.slide_count,
        pptx_available=pptx_available,
        created_at=slide_deck.created_at,
        updated_at=slide_deck.updated_at,
    )


@router.get("/download/{slide_deck_id}")
def download_slide_deck(
    slide_deck_id: str,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Download the PPTX file for a slide deck.
    """
    ip_address, user_agent = get_client_info(request)
    deck_uuid = _parse_uuid(slide_deck_id, "SlideDeck ID")

    slide_deck = db.query(SlideDeck).filter(
        SlideDeck.id == deck_uuid,
        SlideDeck.created_by == current_user.id,
    ).first()

    if not slide_deck:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="スライドデッキが見つかりません",
        )

    if not slide_deck.pptx_path or not os.path.exists(slide_deck.pptx_path):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="PPTXファイルが見つかりません",
        )

    # Log download action
    log_action(
        db=db,
        action=AuditAction.DOWNLOAD_SLIDE_DECK,
        user_id=current_user.id,
        target_type=TargetType.SLIDE_DECK,
        target_id=slide_deck_id,
        details={"title": slide_deck.title},
        ip_address=ip_address,
        user_agent=user_agent,
    )

    # Generate a safe filename
    safe_title = "".join(c for c in slide_deck.title if c.isalnum() or c in " -_").strip()
    if not safe_title:
        safe_title = "presentation"
    filename = f"{safe_title}.pptx"

    return FileResponse(
        path=slide_deck.pptx_path,
        filename=filename,
        media_type="application/vnd.openxmlformats-officedocument.presentationml.presentation",
    )


@router.delete("/{slide_deck_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_slide_deck(
    slide_deck_id: str,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Delete a slide deck and its associated PPTX file.
    """
    ip_address, user_agent = get_client_info(request)
    deck_uuid = _parse_uuid(slide_deck_id, "SlideDeck ID")

    slide_deck = db.query(SlideDeck).filter(
        SlideDeck.id == deck_uuid,
        SlideDeck.created_by == current_user.id,
    ).first()

    if not slide_deck:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="スライドデッキが見つかりません",
        )

    title = slide_deck.title
    pptx_path = slide_deck.pptx_path

    # Delete database record
    db.delete(slide_deck)
    db.commit()

    # Delete PPTX file
    if pptx_path:
        delete_pptx_file(pptx_path)

    # Log action
    log_action(
        db=db,
        action=AuditAction.DELETE_SLIDE_DECK,
        user_id=current_user.id,
        target_type=TargetType.SLIDE_DECK,
        target_id=slide_deck_id,
        details={"title": title},
        ip_address=ip_address,
        user_agent=user_agent,
    )

    return None
