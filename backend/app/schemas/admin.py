"""
Admin schemas for user management.
"""

import re
from datetime import datetime
from typing import List, Optional
from uuid import UUID

from pydantic import BaseModel, Field, field_validator

# Password complexity requirements (same as auth.py)
PASSWORD_MIN_LENGTH = 8
PASSWORD_MAX_LENGTH = 128


class UserListItem(BaseModel):
    """User list item for admin view."""

    id: UUID
    username: str
    display_name: str
    role: str
    created_at: datetime

    class Config:
        from_attributes = True


class UserDetail(BaseModel):
    """User detail for admin view."""

    id: UUID
    username: str
    display_name: str
    role: str
    created_at: datetime

    class Config:
        from_attributes = True


class AdminUserCreate(BaseModel):
    """Schema for admin to create a new user."""

    username: str = Field(..., min_length=3, max_length=50, pattern=r"^[a-zA-Z0-9_-]+$")
    password: str = Field(
        ..., min_length=PASSWORD_MIN_LENGTH, max_length=PASSWORD_MAX_LENGTH
    )
    display_name: str = Field(..., min_length=1, max_length=100)
    role: str = Field(default="user", pattern=r"^(admin|user)$")

    @field_validator("password")
    @classmethod
    def validate_password_complexity(cls, v: str) -> str:
        """
        Validate password meets complexity requirements.
        """
        if len(v) < PASSWORD_MIN_LENGTH:
            raise ValueError(
                f"パスワードは{PASSWORD_MIN_LENGTH}文字以上である必要があります"
            )

        if not re.search(r"[a-z]", v):
            raise ValueError("パスワードには小文字を含める必要があります")

        if not re.search(r"[A-Z]", v):
            raise ValueError("パスワードには大文字を含める必要があります")

        if not re.search(r"\d", v):
            raise ValueError("パスワードには数字を含める必要があります")

        if not re.search(r"[!@#$%^&*()_+\-=\[\]{};':\"\\|,.<>\/?]", v):
            raise ValueError("パスワードには特殊文字を含める必要があります")

        return v

    @field_validator("username")
    @classmethod
    def validate_username(cls, v: str) -> str:
        """Validate username format."""
        if not re.match(r"^[a-zA-Z0-9_-]+$", v):
            raise ValueError(
                "ユーザー名には英数字、アンダースコア、ハイフンのみ使用できます"
            )
        return v

    @field_validator("role")
    @classmethod
    def validate_role(cls, v: str) -> str:
        """Validate role value."""
        if v not in ("admin", "user"):
            raise ValueError("ロールは 'admin' または 'user' のみ使用できます")
        return v


class AdminUserUpdate(BaseModel):
    """Schema for admin to update a user."""

    display_name: Optional[str] = Field(None, min_length=1, max_length=100)
    role: Optional[str] = Field(None, pattern=r"^(admin|user)$")
    password: Optional[str] = Field(
        None, min_length=PASSWORD_MIN_LENGTH, max_length=PASSWORD_MAX_LENGTH
    )

    @field_validator("password")
    @classmethod
    def validate_password_complexity(cls, v: Optional[str]) -> Optional[str]:
        """Validate password meets complexity requirements if provided."""
        if v is None:
            return v

        if len(v) < PASSWORD_MIN_LENGTH:
            raise ValueError(
                f"パスワードは{PASSWORD_MIN_LENGTH}文字以上である必要があります"
            )

        if not re.search(r"[a-z]", v):
            raise ValueError("パスワードには小文字を含める必要があります")

        if not re.search(r"[A-Z]", v):
            raise ValueError("パスワードには大文字を含める必要があります")

        if not re.search(r"\d", v):
            raise ValueError("パスワードには数字を含める必要があります")

        if not re.search(r"[!@#$%^&*()_+\-=\[\]{};':\"\\|,.<>\/?]", v):
            raise ValueError("パスワードには特殊文字を含める必要があります")

        return v

    @field_validator("role")
    @classmethod
    def validate_role(cls, v: Optional[str]) -> Optional[str]:
        """Validate role value if provided."""
        if v is not None and v not in ("admin", "user"):
            raise ValueError("ロールは 'admin' または 'user' のみ使用できます")
        return v


class UserListResponse(BaseModel):
    """Response for user list endpoint."""

    users: List[UserListItem]
    total: int
