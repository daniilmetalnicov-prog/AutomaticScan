from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel
from ..core.database import get_db
from ..schemas.user import UserCreate, UserResponse, UserLogin, Token
from ..services import auth_service
from ..core.security import get_current_user
from ..models.user import User

router = APIRouter(prefix="/api/auth", tags=["Авторизация"])


class RefreshTokenRequest(BaseModel):
    """Схема для запроса обновления токена."""
    refresh_token: str


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def register(user_data: UserCreate, db: AsyncSession = Depends(get_db)):
    """Регистрация нового пользователя."""
    return await auth_service.register_user(db, user_data)


@router.post("/login", response_model=Token)
async def login(user_data: UserLogin, db: AsyncSession = Depends(get_db)):
    """Авторизация пользователя и получение токенов."""
    return await auth_service.login_user(db, user_data.login, user_data.password)


@router.post("/refresh", response_model=Token)
async def refresh_token(request: RefreshTokenRequest, db: AsyncSession = Depends(get_db)):
    """Обновление токенов по refresh token."""
    return await auth_service.refresh_tokens(db, request.refresh_token)


@router.get("/me", response_model=UserResponse)
async def get_current_user_info(current_user: User = Depends(get_current_user)):
    """Получить информацию о текущем пользователе."""
    return current_user