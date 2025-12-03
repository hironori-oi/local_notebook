"""
Infographic API endpoints for generating and managing infographics.
"""
from typing import List
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.core.deps import get_db, get_current_user
from app.models.notebook import Notebook
from app.models.infographic import Infographic
from app.models.user import User
from app.schemas.infographic import (
    InfographicCreateRequest,
    InfographicResponse,
    InfographicListItem,
    InfographicListResponse,
    InfographicStructure,
)
from app.services.infographic_planner import generate_infographic_structure
from app.services.audit import log_action, get_client_info, AuditAction, TargetType

router = APIRouter(prefix="/infographics", tags=["infographics"])


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


@router.post("/{notebook_id}", response_model=InfographicResponse, status_code=status.HTTP_201_CREATED)
async def create_infographic(
    notebook_id: str,
    data: InfographicCreateRequest,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Generate a new infographic from notebook sources.

    Uses RAG to retrieve relevant context and LLM to generate the infographic structure.
    """
    ip_address, user_agent = get_client_info(request)
    nb_uuid = _parse_uuid(notebook_id, "Notebook ID")
    _verify_notebook_ownership(db, nb_uuid, current_user.id)

    # Parse source IDs if provided
    source_uuids = None
    if data.source_ids:
        source_uuids = [_parse_uuid(sid, "Source ID") for sid in data.source_ids]

    # Generate infographic structure using LLM
    structure = await generate_infographic_structure(
        db=db,
        notebook_id=nb_uuid,
        topic=data.topic,
        source_ids=source_uuids,
        user_id=current_user.id,
    )

    # Save to database
    infographic = Infographic(
        notebook_id=nb_uuid,
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
        details={"title": infographic.title, "topic": data.topic},
        ip_address=ip_address,
        user_agent=user_agent,
    )

    return InfographicResponse(
        id=str(infographic.id),
        notebook_id=str(infographic.notebook_id),
        title=infographic.title,
        topic=infographic.topic,
        structure=InfographicStructure.model_validate(infographic.structure),
        style_preset=infographic.style_preset,
        created_at=infographic.created_at,
        updated_at=infographic.updated_at,
    )


@router.get("/{notebook_id}", response_model=InfographicListResponse)
def list_infographics(
    notebook_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    List all infographics for a notebook.
    """
    nb_uuid = _parse_uuid(notebook_id, "Notebook ID")
    _verify_notebook_ownership(db, nb_uuid, current_user.id)

    infographics = db.query(Infographic).filter(
        Infographic.notebook_id == nb_uuid,
        Infographic.created_by == current_user.id,
    ).order_by(Infographic.created_at.desc()).all()

    items = [
        InfographicListItem(
            id=str(inf.id),
            notebook_id=str(inf.notebook_id),
            title=inf.title,
            topic=inf.topic,
            style_preset=inf.style_preset,
            created_at=inf.created_at,
        )
        for inf in infographics
    ]

    return InfographicListResponse(infographics=items, total=len(items))


@router.get("/detail/{infographic_id}", response_model=InfographicResponse)
def get_infographic(
    infographic_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Get a specific infographic by ID with full structure.
    """
    inf_uuid = _parse_uuid(infographic_id, "Infographic ID")

    infographic = db.query(Infographic).filter(
        Infographic.id == inf_uuid,
        Infographic.created_by == current_user.id,
    ).first()

    if not infographic:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="インフォグラフィックが見つかりません",
        )

    return InfographicResponse(
        id=str(infographic.id),
        notebook_id=str(infographic.notebook_id),
        title=infographic.title,
        topic=infographic.topic,
        structure=InfographicStructure.model_validate(infographic.structure),
        style_preset=infographic.style_preset,
        created_at=infographic.created_at,
        updated_at=infographic.updated_at,
    )


@router.delete("/{infographic_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_infographic(
    infographic_id: str,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Delete an infographic.
    """
    ip_address, user_agent = get_client_info(request)
    inf_uuid = _parse_uuid(infographic_id, "Infographic ID")

    infographic = db.query(Infographic).filter(
        Infographic.id == inf_uuid,
        Infographic.created_by == current_user.id,
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
