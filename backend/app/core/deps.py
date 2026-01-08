"""
Common dependencies for FastAPI endpoints.
"""
from typing import Generator, Optional
from uuid import UUID

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session

from app.db.session import SessionLocal
from app.models.user import User
from app.models.notebook import Notebook
from app.models.council import Council
from app.services.auth import decode_access_token, get_user_by_id


def parse_uuid(value: str, name: str = "ID") -> UUID:
    """
    Parse a string to UUID, raising HTTPException on failure.

    This is a common utility function to validate UUID parameters
    across all API endpoints.

    Args:
        value: String value to parse as UUID
        name: Human-readable name for error messages (e.g., "Notebook ID")

    Returns:
        Parsed UUID object

    Raises:
        HTTPException 400: If the value is not a valid UUID
    """
    try:
        return UUID(value)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"無効な{name}です",
        )

# HTTP Bearer token security scheme (with auto_error=False to allow cookie fallback)
security = HTTPBearer(auto_error=False)

# Cookie name for token storage
COOKIE_NAME = "access_token"


def get_token_from_request(
    request: Request,
    credentials: Optional[HTTPAuthorizationCredentials],
) -> Optional[str]:
    """
    Extract token from Authorization header or cookie.

    Priority:
    1. Authorization: Bearer <token> header
    2. access_token cookie

    Returns None if no token found.
    """
    # First try Authorization header
    if credentials is not None:
        return credentials.credentials

    # Fall back to cookie
    return request.cookies.get(COOKIE_NAME)


def get_db() -> Generator[Session, None, None]:
    """
    Database session dependency.

    Yields a database session and ensures it's closed after the request.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


async def get_current_user(
    request: Request,
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    db: Session = Depends(get_db),
) -> User:
    """
    Get the current authenticated user from JWT token.

    Token is extracted from:
    1. Authorization: Bearer <token> header (priority)
    2. access_token cookie (fallback)

    Args:
        request: FastAPI request object
        credentials: Bearer token from Authorization header (optional)
        db: Database session

    Returns:
        Authenticated User object

    Raises:
        HTTPException: If token is invalid or user not found
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="認証情報が無効です",
        headers={"WWW-Authenticate": "Bearer"},
    )

    # Get token from header or cookie
    token = get_token_from_request(request, credentials)
    if token is None:
        raise credentials_exception

    token_data = decode_access_token(token)

    if token_data is None or token_data.user_id is None:
        raise credentials_exception

    try:
        user_id = UUID(token_data.user_id)
    except ValueError:
        raise credentials_exception

    user = get_user_by_id(db, user_id)
    if user is None:
        raise credentials_exception

    return user


async def get_current_user_optional(
    request: Request,
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    db: Session = Depends(get_db),
) -> User | None:
    """
    Optionally get the current authenticated user.

    Returns None if no valid token is provided instead of raising an exception.
    Useful for endpoints that work with or without authentication.

    Token is extracted from Authorization header or cookie.
    """
    # Get token from header or cookie
    token = get_token_from_request(request, credentials)
    if token is None:
        return None

    token_data = decode_access_token(token)
    if token_data is None or token_data.user_id is None:
        return None

    try:
        user_id = UUID(token_data.user_id)
    except ValueError:
        return None

    return get_user_by_id(db, user_id)


async def get_current_admin_user(
    current_user: User = Depends(get_current_user),
) -> User:
    """
    Get the current authenticated user and verify admin role.

    Args:
        current_user: Authenticated user from get_current_user

    Returns:
        Authenticated admin User object

    Raises:
        HTTPException: If user is not an admin
    """
    if not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="管理者権限が必要です",
        )
    return current_user


def check_notebook_access(
    db: Session,
    notebook_id: UUID,
    user: User,
    require_owner: bool = False,
) -> Notebook:
    """
    Check notebook access and return the notebook if accessible.

    Args:
        db: Database session
        notebook_id: UUID of the notebook to access
        user: Current authenticated user
        require_owner: If True, only owner can access (for delete, change is_public)
                      If False, owner OR public notebook can be accessed

    Returns:
        Notebook object if accessible

    Raises:
        HTTPException 404: Notebook not found
        HTTPException 403: No access permission
    """
    notebook = db.query(Notebook).filter(Notebook.id == notebook_id).first()

    if notebook is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="ノートブックが見つかりません",
        )

    is_owner = notebook.owner_id == user.id

    if require_owner:
        # Owner-only operations (delete, change is_public)
        if not is_owner:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="この操作を行う権限がありません",
            )
    else:
        # Access allowed for owner OR public notebook
        if not is_owner and not notebook.is_public:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="このノートブックへのアクセス権限がありません",
            )

    return notebook


def check_council_access(
    db: Session,
    council_id: UUID,
    user: User,
    require_owner: bool = False,
) -> Council:
    """
    Check council access and return the council if accessible.

    Args:
        db: Database session
        council_id: UUID of the council to access
        user: Current authenticated user
        require_owner: If True, only owner can access (for delete, change is_public)
                      If False, owner OR public council can be accessed

    Returns:
        Council object if accessible

    Raises:
        HTTPException 404: Council not found
        HTTPException 403: No access permission
    """
    council = db.query(Council).filter(Council.id == council_id).first()

    if council is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="審議会が見つかりません",
        )

    is_owner = council.owner_id == user.id

    if require_owner:
        # Owner-only operations (delete, change is_public)
        if not is_owner:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="この操作を行う権限がありません",
            )
    else:
        # Access allowed for owner OR public council
        if not is_owner and not council.is_public:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="この審議会へのアクセス権限がありません",
            )

    return council
