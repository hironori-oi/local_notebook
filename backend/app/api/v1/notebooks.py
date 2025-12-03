from typing import List
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.core.deps import get_db, get_current_user
from app.models.notebook import Notebook
from app.models.user import User
from app.schemas.notebook import NotebookCreate, NotebookOut
from app.services.audit import log_action, get_client_info, AuditAction, TargetType

router = APIRouter(prefix="/notebooks", tags=["notebooks"])


@router.get("", response_model=List[NotebookOut])
def list_notebooks(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    List all notebooks owned by the current user.
    """
    notebooks = db.query(Notebook).filter(
        Notebook.owner_id == current_user.id
    ).all()
    return notebooks


@router.get("/{notebook_id}", response_model=NotebookOut)
def get_notebook(
    notebook_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Get a specific notebook by ID.
    """
    try:
        nb_uuid = UUID(notebook_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="無効なNotebook IDです",
        )

    notebook = db.query(Notebook).filter(
        Notebook.id == nb_uuid,
        Notebook.owner_id == current_user.id,
    ).first()

    if not notebook:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Notebookが見つかりません",
        )

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
        details={"title": nb.title},
        ip_address=ip_address,
        user_agent=user_agent,
    )

    return nb


@router.delete("/{notebook_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_notebook(
    notebook_id: str,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Delete a notebook and all associated sources, chunks, and notes.
    """
    ip_address, user_agent = get_client_info(request)

    try:
        nb_uuid = UUID(notebook_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="無効なNotebook IDです",
        )

    notebook = db.query(Notebook).filter(
        Notebook.id == nb_uuid,
        Notebook.owner_id == current_user.id,
    ).first()

    if not notebook:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Notebookが見つかりません",
        )

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
