"""Folder API endpoints for managing source folders."""

import logging
from typing import List
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core.deps import (check_notebook_access, get_current_user, get_db,
                           parse_uuid)
from app.models.source import Source
from app.models.source_folder import SourceFolder
from app.models.user import User
from app.schemas.source_folder import (FolderCreate, FolderOut, FolderReorder,
                                       FolderUpdate)
from app.services.audit import (AuditAction, TargetType, get_client_info,
                                log_action)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/folders", tags=["folders"])


def _get_folder_with_access_check(
    db: Session, folder_id: UUID, user: User
) -> SourceFolder:
    """Get a folder and verify the user can access the parent notebook."""
    folder = db.query(SourceFolder).filter(SourceFolder.id == folder_id).first()

    if not folder:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="フォルダが見つかりません",
        )

    # Verify notebook access (owner or public)
    check_notebook_access(db, folder.notebook_id, user)

    return folder


def _folder_to_out(folder: SourceFolder, source_count: int) -> FolderOut:
    """Convert a SourceFolder model to FolderOut schema."""
    return FolderOut(
        id=folder.id,
        notebook_id=folder.notebook_id,
        name=folder.name,
        position=folder.position,
        source_count=source_count,
        created_at=folder.created_at,
        updated_at=folder.updated_at,
    )


@router.get("/notebook/{notebook_id}", response_model=List[FolderOut])
def list_folders(
    notebook_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    List all folders in a notebook, ordered by position.
    """
    nb_uuid = parse_uuid(notebook_id, "Notebook ID")
    check_notebook_access(db, nb_uuid, current_user)

    folders = (
        db.query(SourceFolder)
        .filter(
            SourceFolder.notebook_id == nb_uuid,
        )
        .order_by(SourceFolder.position)
        .all()
    )

    if not folders:
        return []

    # Batch fetch source counts to avoid N+1 queries
    folder_ids = [f.id for f in folders]
    source_counts = (
        db.query(Source.folder_id, func.count(Source.id).label("count"))
        .filter(Source.folder_id.in_(folder_ids))
        .group_by(Source.folder_id)
        .all()
    )

    count_map = {row.folder_id: row.count for row in source_counts}

    result = []
    for folder in folders:
        result.append(_folder_to_out(folder, count_map.get(folder.id, 0)))

    return result


@router.post(
    "/notebook/{notebook_id}",
    response_model=FolderOut,
    status_code=status.HTTP_201_CREATED,
)
def create_folder(
    notebook_id: str,
    data: FolderCreate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Create a new folder in a notebook.
    """
    ip_address, user_agent = get_client_info(request)
    nb_uuid = parse_uuid(notebook_id, "Notebook ID")
    check_notebook_access(db, nb_uuid, current_user)

    # Get max position for new folder
    max_position = (
        db.query(func.max(SourceFolder.position))
        .filter(SourceFolder.notebook_id == nb_uuid)
        .scalar()
        or -1
    )

    folder = SourceFolder(
        notebook_id=nb_uuid,
        name=data.name,
        position=max_position + 1,
    )
    db.add(folder)
    db.commit()
    db.refresh(folder)

    # Log action
    log_action(
        db=db,
        action=AuditAction.CREATE_FOLDER,
        user_id=current_user.id,
        target_type=TargetType.FOLDER,
        target_id=str(folder.id),
        details={
            "name": folder.name,
            "notebook_id": notebook_id,
        },
        ip_address=ip_address,
        user_agent=user_agent,
    )

    logger.info(f"Folder created: {folder.name} by user {current_user.id}")

    return _folder_to_out(folder, 0)


@router.patch("/{folder_id}", response_model=FolderOut)
def update_folder(
    folder_id: str,
    data: FolderUpdate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Update a folder's name.
    """
    ip_address, user_agent = get_client_info(request)
    f_uuid = parse_uuid(folder_id, "Folder ID")
    folder = _get_folder_with_access_check(db, f_uuid, current_user)

    old_name = folder.name

    if data.name is not None:
        folder.name = data.name

    db.commit()
    db.refresh(folder)

    # Log action
    log_action(
        db=db,
        action=AuditAction.UPDATE_FOLDER,
        user_id=current_user.id,
        target_type=TargetType.FOLDER,
        target_id=str(folder.id),
        details={
            "old_name": old_name,
            "new_name": folder.name,
        },
        ip_address=ip_address,
        user_agent=user_agent,
    )

    source_count = db.query(Source).filter(Source.folder_id == folder.id).count()
    return _folder_to_out(folder, source_count)


@router.delete("/{folder_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_folder(
    folder_id: str,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Delete a folder and all its sources.

    This will also delete all sources within the folder (CASCADE).
    """
    ip_address, user_agent = get_client_info(request)
    f_uuid = parse_uuid(folder_id, "Folder ID")
    folder = _get_folder_with_access_check(db, f_uuid, current_user)

    folder_name = folder.name
    notebook_id = str(folder.notebook_id)

    # Count sources that will be deleted
    source_count = db.query(Source).filter(Source.folder_id == folder.id).count()

    # Delete the folder (sources will be deleted via CASCADE)
    db.delete(folder)
    db.commit()

    # Log action
    log_action(
        db=db,
        action=AuditAction.DELETE_FOLDER,
        user_id=current_user.id,
        target_type=TargetType.FOLDER,
        target_id=folder_id,
        details={
            "name": folder_name,
            "notebook_id": notebook_id,
            "sources_deleted": source_count,
        },
        ip_address=ip_address,
        user_agent=user_agent,
    )

    logger.info(
        f"Folder deleted: {folder_name} ({source_count} sources) by user {current_user.id}"
    )

    return None


@router.put("/notebook/{notebook_id}/reorder", response_model=List[FolderOut])
def reorder_folders(
    notebook_id: str,
    data: FolderReorder,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Reorder folders in a notebook.

    The folder_ids list should contain all folder IDs in the desired order.
    """
    nb_uuid = parse_uuid(notebook_id, "Notebook ID")
    check_notebook_access(db, nb_uuid, current_user)

    # Verify all folder IDs belong to this notebook
    existing_folders = (
        db.query(SourceFolder).filter(SourceFolder.notebook_id == nb_uuid).all()
    )
    existing_ids = {f.id for f in existing_folders}
    provided_ids = set(data.folder_ids)

    if existing_ids != provided_ids:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="フォルダIDリストが不正です。すべてのフォルダIDを含める必要があります。",
        )

    # Build a map of folder_id -> position for batch update
    folder_map = {f.id: f for f in existing_folders}
    for position, folder_id in enumerate(data.folder_ids):
        if folder_id in folder_map:
            folder_map[folder_id].position = position

    db.commit()

    # Return updated folders
    folders = (
        db.query(SourceFolder)
        .filter(
            SourceFolder.notebook_id == nb_uuid,
        )
        .order_by(SourceFolder.position)
        .all()
    )

    if not folders:
        return []

    # Batch fetch source counts to avoid N+1 queries
    folder_ids = [f.id for f in folders]
    source_counts = (
        db.query(Source.folder_id, func.count(Source.id).label("count"))
        .filter(Source.folder_id.in_(folder_ids))
        .group_by(Source.folder_id)
        .all()
    )

    count_map = {row.folder_id: row.count for row in source_counts}

    result = []
    for folder in folders:
        result.append(_folder_to_out(folder, count_map.get(folder.id, 0)))

    return result
