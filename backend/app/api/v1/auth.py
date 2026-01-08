"""
Authentication API endpoints.
"""
from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from sqlalchemy.orm import Session

from app.core.deps import get_db, get_current_user
from app.core.config import settings

from app.models.user import User

from app.schemas.auth import (
    UserRegister,
    UserLogin,
    Token,
    UserOut,
    UserWithToken,
    PasswordChange,
)
from app.services.auth import (
    authenticate_user,
    create_user,
    create_access_token,
    get_user_by_username,
    verify_password,
    change_user_password,
)
from app.services.audit import (
    log_action,
    get_client_info,
    AuditAction,
    TargetType,
)

# Cookie settings for secure token storage
COOKIE_NAME = "access_token"
COOKIE_MAX_AGE = settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES * 60  # seconds
COOKIE_SECURE = settings.ENV == "production"  # Only send over HTTPS in production

router = APIRouter(prefix="/auth", tags=["auth"])


def set_auth_cookie(response: Response, token: str) -> None:
    """Set HTTPOnly secure cookie with the access token."""
    response.set_cookie(
        key=COOKIE_NAME,
        value=token,
        httponly=True,
        secure=COOKIE_SECURE,
        samesite="lax",
        max_age=COOKIE_MAX_AGE,
        path="/",
    )


def clear_auth_cookie(response: Response) -> None:
    """Clear the authentication cookie."""
    response.delete_cookie(
        key=COOKIE_NAME,
        path="/",
        httponly=True,
        secure=COOKIE_SECURE,
        samesite="lax",
    )


@router.post("/register", response_model=UserWithToken, status_code=status.HTTP_201_CREATED)
def register(
    data: UserRegister,
    request: Request,
    response: Response,
    db: Session = Depends(get_db),
):
    """
    Register a new user.

    - **username**: Unique username (3-50 characters)
    - **password**: Password (8+ chars with uppercase, lowercase, digit, special char)
    - **display_name**: Display name for the user

    Returns user info and access token on success.
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
    )

    # Log registration
    log_action(
        db=db,
        action=AuditAction.REGISTER,
        user_id=user.id,
        target_type=TargetType.USER,
        target_id=str(user.id),
        details={"username": user.username},
        ip_address=ip_address,
        user_agent=user_agent,
    )

    # Create access token (include role for authorization)
    access_token = create_access_token(
        data={"sub": str(user.id), "username": user.username, "role": user.role}
    )

    expires_in = settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES * 60  # convert to seconds

    # Set HTTPOnly cookie with the token
    set_auth_cookie(response, access_token)

    return UserWithToken(
        user=UserOut(
            id=str(user.id),
            username=user.username,
            display_name=user.display_name,
            role=user.role,
        ),
        token=Token(
            access_token=access_token,
            token_type="bearer",
            expires_in=expires_in,
        ),
    )


@router.post("/login", response_model=UserWithToken)
def login(
    data: UserLogin,
    request: Request,
    response: Response,
    db: Session = Depends(get_db),
):
    """
    Authenticate user and return access token.

    - **username**: Username
    - **password**: Password

    Returns user info and access token on success.
    """
    ip_address, user_agent = get_client_info(request)

    user = authenticate_user(db, data.username, data.password)
    if not user:
        # Log failed login attempt
        log_action(
            db=db,
            action=AuditAction.LOGIN_FAILED,
            user_id=None,
            target_type=TargetType.USER,
            target_id=None,
            details={"username": data.username},
            ip_address=ip_address,
            user_agent=user_agent,
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="ユーザー名またはパスワードが正しくありません",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Log successful login
    log_action(
        db=db,
        action=AuditAction.LOGIN,
        user_id=user.id,
        target_type=TargetType.USER,
        target_id=str(user.id),
        details={"username": user.username},
        ip_address=ip_address,
        user_agent=user_agent,
    )

    access_token = create_access_token(
        data={"sub": str(user.id), "username": user.username, "role": user.role}
    )

    expires_in = settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES * 60

    # Set HTTPOnly cookie with the token
    set_auth_cookie(response, access_token)

    return UserWithToken(
        user=UserOut(
            id=str(user.id),
            username=user.username,
            display_name=user.display_name,
            role=user.role,
        ),
        token=Token(
            access_token=access_token,
            token_type="bearer",
            expires_in=expires_in,
        ),
    )


@router.post("/logout")
def logout(
    request: Request,
    response: Response,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Logout endpoint.

    For JWT-based authentication, the actual logout is handled client-side
    by removing the token. This endpoint logs the logout action.
    """
    ip_address, user_agent = get_client_info(request)

    # Log logout
    log_action(
        db=db,
        action=AuditAction.LOGOUT,
        user_id=current_user.id,
        target_type=TargetType.USER,
        target_id=str(current_user.id),
        ip_address=ip_address,
        user_agent=user_agent,
    )

    # Clear the authentication cookie
    clear_auth_cookie(response)

    return {"message": "ログアウトしました"}


@router.post("/change-password")
def change_password(
    data: PasswordChange,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Change the current user's password.

    - **current_password**: Current password for verification
    - **new_password**: New password (must meet complexity requirements)

    Returns success message on success.
    """
    ip_address, user_agent = get_client_info(request)

    # Verify current password
    if not verify_password(data.current_password, current_user.password_hash):
        log_action(
            db=db,
            action=AuditAction.UPDATE,
            user_id=current_user.id,
            target_type=TargetType.USER,
            target_id=str(current_user.id),
            details={"action": "password_change_failed", "reason": "invalid_current_password"},
            ip_address=ip_address,
            user_agent=user_agent,
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="現在のパスワードが正しくありません",
        )

    # Check that new password is different from current
    if verify_password(data.new_password, current_user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="新しいパスワードは現在のパスワードと異なる必要があります",
        )

    # Change password
    change_user_password(db, current_user, data.new_password)

    # Log password change
    log_action(
        db=db,
        action=AuditAction.UPDATE,
        user_id=current_user.id,
        target_type=TargetType.USER,
        target_id=str(current_user.id),
        details={"action": "password_changed"},
        ip_address=ip_address,
        user_agent=user_agent,
    )

    return {"message": "パスワードを変更しました"}


@router.get("/me", response_model=UserOut)
def get_current_user_info(
    current_user: User = Depends(get_current_user),
):
    """
    Get current user information.

    Returns the authenticated user's info.
    """
    return UserOut(
        id=str(current_user.id),
        username=current_user.username,
        display_name=current_user.display_name,
        role=current_user.role,
    )
