from pydantic import BaseModel, EmailStr, field_validator
from pydantic_core import PydanticCustomError
from typing import Optional
from datetime import datetime
import re


class UserBase(BaseModel):
    """Базовая схема пользователя."""
    login: str
    full_name: Optional[str] = None
    email: Optional[EmailStr] = None


class UserCreate(UserBase):
    """Схема для создания пользователя (при регистрации)."""
    password: str  # Пароль в открытом виде (будет захеширован на сервере)
    
    @field_validator("password")
    @classmethod
    def validate_password(cls, v: str) -> str:
        """Проверяет сложность пароля."""
        if len(v) < 8:
            raise PydanticCustomError(
                "password_too_short",
                "Пароль должен содержать не менее 8 символов"
            )
        if not re.search(r"[A-Z]", v):
            raise PydanticCustomError(
                "password_no_uppercase",
                "Пароль должен содержать хотя бы одну заглавную букву"
            )
        if not re.search(r"[a-z]", v):
            raise PydanticCustomError(
                "password_no_lowercase",
                "Пароль должен содержать хотя бы одну строчную букву"
            )
        if not re.search(r"\d", v):
            raise PydanticCustomError(
                "password_no_digit",
                "Пароль должен содержать хотя бы одну цифру"
            )
        if not re.search(r"[!@#$%^&*(),.?\":{}|<>]", v):
            raise PydanticCustomError(
                "password_no_special",
                "Пароль должен содержать хотя бы один специальный символ"
            )
        return v


class UserResponse(UserBase):
    """Схема для ответа (без пароля!)."""
    id: int
    is_active: bool
    is_admin: bool
    created_at: datetime
    
    class Config:
        from_attributes = True  # Позволяет создавать схему из ORM-объекта


class UserLogin(BaseModel):
    """Схема для логина."""
    login: str
    password: str


class Token(BaseModel):
    """Схема для токена."""
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class TokenData(BaseModel):
    """Схема для данных внутри токена."""
    user_id: Optional[int] = None