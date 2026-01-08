"""
Admin API endpoints for user management.

Only accessible by users with admin role.
"""

import logging
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.core.deps import get_current_admin_user, get_db, parse_uuid
from app.models.user import User
from app.schemas.admin import (AdminUserCreate, AdminUserUpdate, UserDetail,
                               UserListItem, UserListResponse)
from app.services.audit import (AuditAction, TargetType, get_client_info,
                                log_action)
from app.services.auth import (create_user, get_password_hash,
                               get_user_by_username)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/admin", tags=["admin"])


@router.get("/users", response_model=UserListResponse)
async def list_users(
    db: Session = Depends(get_db),
    admin_user: User = Depends(get_current_admin_user),
):
    """
    List all users.

    Requires admin role.
    """
    users = db.query(User).order_by(User.created_at.desc()).all()

    user_list = [
        UserListItem(
            id=user.id,
            username=user.username,
            display_name=user.display_name,
            role=user.role,
            created_at=user.created_at,
        )
        for user in users
    ]

    return UserListResponse(users=user_list, total=len(users))


@router.post("/users", response_model=UserDetail, status_code=status.HTTP_201_CREATED)
async def create_new_user(
    data: AdminUserCreate,
    request: Request,
    db: Session = Depends(get_db),
    admin_user: User = Depends(get_current_admin_user),
):
    """
    Create a new user.

    Requires admin role.
    """
    ip_address, user_agent = get_client_info(request)

    # Check if username already exists
    existing_user = get_user_by_username(db, data.username)
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="このユーザー名は既に使用されています",
        )

    # Create new user
    user = create_user(
        db=db,
        username=data.username,
        password=data.password,
        display_name=data.display_name,
        role=data.role,
    )

    # Log action
    log_action(
        db=db,
        action=AuditAction.CREATE_USER,
        user_id=admin_user.id,
        target_type=TargetType.USER,
        target_id=str(user.id),
        details={
            "username": user.username,
            "role": user.role,
            "created_by_admin": admin_user.username,
        },
        ip_address=ip_address,
        user_agent=user_agent,
    )

    logger.info(
        f"Admin {admin_user.username} created user {user.username} with role {user.role}"
    )

    return UserDetail(
        id=user.id,
        username=user.username,
        display_name=user.display_name,
        role=user.role,
        created_at=user.created_at,
    )


@router.get("/users/{user_id}", response_model=UserDetail)
async def get_user(
    user_id: str,
    db: Session = Depends(get_db),
    admin_user: User = Depends(get_current_admin_user),
):
    """
    Get a specific user by ID.

    Requires admin role.
    """
    uid = parse_uuid(user_id, "User ID")

    user = db.query(User).filter(User.id == uid).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="ユーザーが見つかりません",
        )

    return UserDetail(
        id=user.id,
        username=user.username,
        display_name=user.display_name,
        role=user.role,
        created_at=user.created_at,
    )


@router.patch("/users/{user_id}", response_model=UserDetail)
async def update_user(
    user_id: str,
    data: AdminUserUpdate,
    request: Request,
    db: Session = Depends(get_db),
    admin_user: User = Depends(get_current_admin_user),
):
    """
    Update a user's information.

    Requires admin role.
    """
    ip_address, user_agent = get_client_info(request)
    uid = parse_uuid(user_id, "User ID")

    user = db.query(User).filter(User.id == uid).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="ユーザーが見つかりません",
        )

    changes = {}

    # Update display_name if provided
    if data.display_name is not None:
        changes["display_name"] = {"old": user.display_name, "new": data.display_name}
        user.display_name = data.display_name

    # Update role if provided
    if data.role is not None:
        # Prevent removing the last admin
        if user.role == "admin" and data.role == "user":
            admin_count = db.query(User).filter(User.role == "admin").count()
            if admin_count <= 1:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="最後の管理者のロールは変更できません",
                )

        changes["role"] = {"old": user.role, "new": data.role}
        user.role = data.role

    # Update password if provided
    if data.password is not None:
        user.password_hash = get_password_hash(data.password)
        changes["password"] = "changed"

    if changes:
        db.commit()
        db.refresh(user)

        # Log action
        log_action(
            db=db,
            action=AuditAction.UPDATE_USER,
            user_id=admin_user.id,
            target_type=TargetType.USER,
            target_id=str(user.id),
            details={
                "username": user.username,
                "changes": changes,
                "updated_by_admin": admin_user.username,
            },
            ip_address=ip_address,
            user_agent=user_agent,
        )

        logger.info(
            f"Admin {admin_user.username} updated user {user.username}: {list(changes.keys())}"
        )

    return UserDetail(
        id=user.id,
        username=user.username,
        display_name=user.display_name,
        role=user.role,
        created_at=user.created_at,
    )


@router.delete("/users/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_user(
    user_id: str,
    request: Request,
    db: Session = Depends(get_db),
    admin_user: User = Depends(get_current_admin_user),
):
    """
    Delete a user.

    Requires admin role.
    Cannot delete yourself or the last admin.
    """
    ip_address, user_agent = get_client_info(request)
    uid = parse_uuid(user_id, "User ID")

    user = db.query(User).filter(User.id == uid).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="ユーザーが見つかりません",
        )

    # Prevent self-deletion
    if user.id == admin_user.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="自分自身を削除することはできません",
        )

    # Prevent deleting the last admin
    if user.role == "admin":
        admin_count = db.query(User).filter(User.role == "admin").count()
        if admin_count <= 1:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="最後の管理者は削除できません",
            )

    username = user.username

    # Delete user (cascades should handle related records)
    db.delete(user)
    db.commit()

    # Log action
    log_action(
        db=db,
        action=AuditAction.DELETE_USER,
        user_id=admin_user.id,
        target_type=TargetType.USER,
        target_id=user_id,
        details={
            "username": username,
            "deleted_by_admin": admin_user.username,
        },
        ip_address=ip_address,
        user_agent=user_agent,
    )

    logger.info(f"Admin {admin_user.username} deleted user {username}")

    return None


@router.post("/users/{user_id}/promote", response_model=UserDetail)
async def promote_to_admin(
    user_id: str,
    request: Request,
    db: Session = Depends(get_db),
    admin_user: User = Depends(get_current_admin_user),
):
    """
    Promote a user to admin role.

    Requires admin role.
    """
    ip_address, user_agent = get_client_info(request)
    uid = parse_uuid(user_id, "User ID")

    user = db.query(User).filter(User.id == uid).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="ユーザーが見つかりません",
        )

    if user.role == "admin":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="このユーザーは既に管理者です",
        )

    old_role = user.role
    user.role = "admin"
    db.commit()
    db.refresh(user)

    # Log action
    log_action(
        db=db,
        action=AuditAction.UPDATE_USER,
        user_id=admin_user.id,
        target_type=TargetType.USER,
        target_id=str(user.id),
        details={
            "username": user.username,
            "action": "promote_to_admin",
            "old_role": old_role,
            "new_role": "admin",
            "promoted_by_admin": admin_user.username,
        },
        ip_address=ip_address,
        user_agent=user_agent,
    )

    logger.info(f"Admin {admin_user.username} promoted user {user.username} to admin")

    return UserDetail(
        id=user.id,
        username=user.username,
        display_name=user.display_name,
        role=user.role,
        created_at=user.created_at,
    )
