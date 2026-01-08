from typing import List, Literal, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy import func, or_
from sqlalchemy.orm import Session

from app.core.deps import check_notebook_access, get_current_user, get_db
from app.models.notebook import Notebook
from app.models.source import Source
from app.models.user import User
from app.schemas.notebook import (NotebookCreate, NotebookListOut,
                                  NotebookListResponse, NotebookOut,
                                  NotebookUpdate)
from app.services.audit import (AuditAction, TargetType, get_client_info,
                                log_action)

router = APIRouter(prefix="/notebooks", tags=["notebooks"])


@router.get("", response_model=NotebookListResponse)
def list_notebooks(
    filter_type: Literal["all", "mine", "public"] = Query(
        "all",
        description="Filter type: all (mine + public), mine (only mine), public (only public)",
    ),
    offset: int = Query(0, ge=0, description="Number of items to skip"),
    limit: int = Query(50, ge=1, le=100, description="Maximum items to return"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    List notebooks based on filter type with pagination.

    - all: All notebooks the user can access (own + public)
    - mine: Only notebooks owned by the user
    - public: Only public notebooks

    Supports pagination via offset and limit parameters.
    """
    # Build base query with source count subquery
    source_count_subq = (
        db.query(Source.notebook_id, func.count(Source.id).label("source_count"))
        .group_by(Source.notebook_id)
        .subquery()
    )

    query = (
        db.query(
            Notebook.id,
            Notebook.title,
            Notebook.description,
            Notebook.is_public,
            Notebook.owner_id,
            User.display_name.label("owner_display_name"),
            func.coalesce(source_count_subq.c.source_count, 0).label("source_count"),
            Notebook.created_at,
            Notebook.updated_at,
        )
        .join(User, Notebook.owner_id == User.id)
        .outerjoin(source_count_subq, Notebook.id == source_count_subq.c.notebook_id)
    )

    if filter_type == "mine":
        # Only user's own notebooks
        query = query.filter(Notebook.owner_id == current_user.id)
    elif filter_type == "public":
        # Only public notebooks
        query = query.filter(Notebook.is_public == True)
    else:  # "all"
        # User's own notebooks + public notebooks
        query = query.filter(
            or_(Notebook.owner_id == current_user.id, Notebook.is_public == True)
        )

    # Get total count before pagination
    # Use a subquery to count from the filtered base query
    count_query = db.query(Notebook.id)
    if filter_type == "mine":
        count_query = count_query.filter(Notebook.owner_id == current_user.id)
    elif filter_type == "public":
        count_query = count_query.filter(Notebook.is_public == True)
    else:
        count_query = count_query.filter(
            or_(Notebook.owner_id == current_user.id, Notebook.is_public == True)
        )
    total = count_query.count()

    # Order by updated_at descending and apply pagination
    query = query.order_by(Notebook.updated_at.desc()).offset(offset).limit(limit)

    results = query.all()

    # Convert to NotebookListOut format
    notebooks = []
    for row in results:
        notebooks.append(
            NotebookListOut(
                id=row.id,
                title=row.title,
                description=row.description,
                is_public=row.is_public,
                owner_id=row.owner_id,
                owner_display_name=row.owner_display_name,
                source_count=row.source_count,
                created_at=row.created_at,
                updated_at=row.updated_at,
            )
        )

    return NotebookListResponse(
        items=notebooks,
        total=total,
        offset=offset,
        limit=limit,
    )


@router.get("/{notebook_id}", response_model=NotebookOut)
def get_notebook(
    notebook_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Get a specific notebook by ID.

    Accessible by owner or any user if the notebook is public.
    """
    try:
        nb_uuid = UUID(notebook_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="無効なNotebook IDです",
        )

    notebook = check_notebook_access(db, nb_uuid, current_user)
    return notebook


@router.post("", response_model=NotebookOut, status_code=status.HTTP_201_CREATED)
def create_notebook(
    data: NotebookCreate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Create a new notebook.
    """
    ip_address, user_agent = get_client_info(request)

    nb = Notebook(
        owner_id=current_user.id,
        title=data.title,
        description=data.description,
        is_public=data.is_public,
    )
    db.add(nb)
    db.commit()
    db.refresh(nb)

    # Log notebook creation
    log_action(
        db=db,
        action=AuditAction.CREATE_NOTEBOOK,
        user_id=current_user.id,
        target_type=TargetType.NOTEBOOK,
        target_id=str(nb.id),
        details={"title": nb.title, "is_public": nb.is_public},
        ip_address=ip_address,
        user_agent=user_agent,
    )

    return nb


@router.patch("/{notebook_id}", response_model=NotebookOut)
def update_notebook(
    notebook_id: str,
    data: NotebookUpdate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Update a notebook.

    - Title and description: Can be updated by owner or any user if public
    - is_public: Can only be changed by the owner
    """
    ip_address, user_agent = get_client_info(request)

    try:
        nb_uuid = UUID(notebook_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="無効なNotebook IDです",
        )

    # If changing is_public, require owner
    require_owner = data.is_public is not None
    notebook = check_notebook_access(
        db, nb_uuid, current_user, require_owner=require_owner
    )

    update_details = {}

    if data.title is not None:
        notebook.title = data.title
        update_details["title"] = data.title

    if data.description is not None:
        notebook.description = data.description
        update_details["description"] = data.description

    if data.is_public is not None:
        old_is_public = notebook.is_public
        notebook.is_public = data.is_public
        update_details["is_public"] = {"from": old_is_public, "to": data.is_public}

    db.commit()
    db.refresh(notebook)

    # Log notebook update
    if update_details:
        log_action(
            db=db,
            action=AuditAction.UPDATE_NOTEBOOK,
            user_id=current_user.id,
            target_type=TargetType.NOTEBOOK,
            target_id=notebook_id,
            details=update_details,
            ip_address=ip_address,
            user_agent=user_agent,
        )

    return notebook


@router.delete("/{notebook_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_notebook(
    notebook_id: str,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Delete a notebook and all associated sources, chunks, and notes.

    Only the owner can delete a notebook.
    """
    ip_address, user_agent = get_client_info(request)

    try:
        nb_uuid = UUID(notebook_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="無効なNotebook IDです",
        )

    # Only owner can delete
    notebook = check_notebook_access(db, nb_uuid, current_user, require_owner=True)

    notebook_title = notebook.title

    # Delete notebook (cascading will handle related records if configured)
    db.delete(notebook)
    db.commit()

    # Log notebook deletion
    log_action(
        db=db,
        action=AuditAction.DELETE_NOTEBOOK,
        user_id=current_user.id,
        target_type=TargetType.NOTEBOOK,
        target_id=notebook_id,
        details={"title": notebook_title},
        ip_address=ip_address,
        user_agent=user_agent,
    )

    return None
