"""
Authentication service - JWT token management and password hashing.
"""

from datetime import datetime, timedelta, timezone
from typing import Optional
from uuid import UUID

from jose import JWTError, jwt
from passlib.context import CryptContext
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.user import User
from app.schemas.auth import TokenData

# Password hashing context
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a plain password against a hashed password."""
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    """Hash a plain password."""
    return pwd_context.hash(password)


def create_access_token(
    data: dict,
    expires_delta: Optional[timedelta] = None,
) -> str:
    """
    Create a JWT access token.

    Args:
        data: Payload data to encode in the token
        expires_delta: Optional custom expiration time

    Returns:
        Encoded JWT token string
    """
    to_encode = data.copy()

    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(
            minutes=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES
        )

    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(
        to_encode,
        settings.JWT_SECRET_KEY,
        algorithm=settings.JWT_ALGORITHM,
    )
    return encoded_jwt


def decode_access_token(token: str) -> Optional[TokenData]:
    """
    Decode and validate a JWT access token.

    Args:
        token: JWT token string

    Returns:
        TokenData if valid, None if invalid or expired
    """
    try:
        payload = jwt.decode(
            token,
            settings.JWT_SECRET_KEY,
            algorithms=[settings.JWT_ALGORITHM],
        )
        user_id: str = payload.get("sub")
        username: str = payload.get("username")
        role: str = payload.get("role", "user")

        if user_id is None:
            return None

        return TokenData(user_id=user_id, username=username, role=role)
    except JWTError:
        return None


def authenticate_user(db: Session, username: str, password: str) -> Optional[User]:
    """
    Authenticate a user by username and password.

    Args:
        db: Database session
        username: Username to authenticate
        password: Plain text password

    Returns:
        User object if authentication successful, None otherwise
    """
    user = db.query(User).filter(User.username == username).first()
    if not user:
        return None
    if not verify_password(password, user.password_hash):
        return None
    return user


def get_user_by_id(db: Session, user_id: UUID) -> Optional[User]:
    """Get a user by their ID."""
    return db.query(User).filter(User.id == user_id).first()


def get_user_by_username(db: Session, username: str) -> Optional[User]:
    """Get a user by their username."""
    return db.query(User).filter(User.username == username).first()


def create_user(
    db: Session,
    username: str,
    password: str,
    display_name: str,
    role: str = "user",
) -> User:
    """
    Create a new user.

    Args:
        db: Database session
        username: Unique username
        password: Plain text password (will be hashed)
        display_name: User's display name
        role: User role ("admin" or "user", default: "user")

    Returns:
        Created User object
    """
    hashed_password = get_password_hash(password)
    user = User(
        username=username,
        password_hash=hashed_password,
        display_name=display_name,
        role=role,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def change_user_password(
    db: Session,
    user: User,
    new_password: str,
) -> User:
    """
    Change a user's password.

    Args:
        db: Database session
        user: User object to update
        new_password: New plain text password (will be hashed)

    Returns:
        Updated User object
    """
    user.password_hash = get_password_hash(new_password)
    db.commit()
    db.refresh(user)
    return user
