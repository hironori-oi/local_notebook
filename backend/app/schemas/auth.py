import re
from typing import Optional

from pydantic import BaseModel, Field, field_validator

# Password complexity requirements
PASSWORD_MIN_LENGTH = 8
PASSWORD_MAX_LENGTH = 128
PASSWORD_PATTERN = re.compile(
    r"^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)(?=.*[!@#$%^&*()_+\-=\[\]{};':\"\\|,.<>\/?]).+$"
)


class UserRegister(BaseModel):
    """ユーザー登録リクエスト"""

    username: str = Field(..., min_length=3, max_length=50, pattern=r"^[a-zA-Z0-9_-]+$")
    password: str = Field(
        ..., min_length=PASSWORD_MIN_LENGTH, max_length=PASSWORD_MAX_LENGTH
    )
    display_name: str = Field(..., min_length=1, max_length=100)

    @field_validator("password")
    @classmethod
    def validate_password_complexity(cls, v: str) -> str:
        """
        Validate password meets complexity requirements:
        - At least 8 characters
        - At least one lowercase letter
        - At least one uppercase letter
        - At least one digit
        - At least one special character
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
            raise ValueError(
                "パスワードには特殊文字（!@#$%^&*など）を含める必要があります"
            )

        # Check for common weak passwords
        common_passwords = {"password", "12345678", "qwerty123", "admin123"}
        if v.lower() in common_passwords:
            raise ValueError("このパスワードは一般的すぎるため使用できません")

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


class UserLogin(BaseModel):
    """ログインリクエスト"""

    username: str
    password: str


class Token(BaseModel):
    """認証トークンレスポンス"""

    access_token: str
    token_type: str = "bearer"
    expires_in: int  # seconds


class TokenData(BaseModel):
    """JWTトークンのペイロード"""

    user_id: Optional[str] = None
    username: Optional[str] = None
    role: Optional[str] = None


class UserOut(BaseModel):
    """ユーザー情報レスポンス"""

    id: str
    username: str
    display_name: str
    role: str = "user"

    class Config:
        from_attributes = True


class UserWithToken(BaseModel):
    """ログイン成功時のレスポンス（ユーザー情報 + トークン）"""

    user: UserOut
    token: Token


class PasswordChange(BaseModel):
    """パスワード変更リクエスト"""

    current_password: str = Field(..., min_length=1)
    new_password: str = Field(
        ..., min_length=PASSWORD_MIN_LENGTH, max_length=PASSWORD_MAX_LENGTH
    )

    @field_validator("new_password")
    @classmethod
    def validate_new_password_complexity(cls, v: str) -> str:
        """
        Validate new password meets complexity requirements.
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
            raise ValueError(
                "パスワードには特殊文字（!@#$%^&*など）を含める必要があります"
            )

        common_passwords = {"password", "12345678", "qwerty123", "admin123"}
        if v.lower() in common_passwords:
            raise ValueError("このパスワードは一般的すぎるため使用できません")

        return v
