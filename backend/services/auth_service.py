from datetime import timedelta
from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from ..models.user import User
from ..schemas.user import UserCreate, Token
from ..core.security import (
    get_password_hash,
    verify_password,
    create_access_token,
    create_refresh_token,
    ACCESS_TOKEN_EXPIRE_MINUTES,
)


async def register_user(db: AsyncSession, user_data: UserCreate) -> User:
    """Регистрирует нового пользователя."""
    # Проверяем, не занят ли логин
    result = await db.execute(select(User).where(User.login == user_data.login))
    if result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Логин уже занят"
        )
    
    # Проверяем, не занят ли email
    if user_data.email:
        result = await db.execute(select(User).where(User.email == user_data.email))
        if result.scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email уже зарегистрирован"
            )
    
    # Создаём пользователя
    user = User(
        login=user_data.login,
        hashed_password=get_password_hash(user_data.password),
        full_name=user_data.full_name,
        email=user_data.email,
    )
    
    db.add(user)
    await db.flush()  # Получаем ID пользователя
    await db.refresh(user)  # Обновляем объект
    
    return user


async def authenticate_user(db: AsyncSession, login: str, password: str) -> User:
    """Проверяет учётные данные пользователя."""
    result = await db.execute(select(User).where(User.login == login))
    user = result.scalar_one_or_none()
    
    if not user or not verify_password(password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Неверный логин или пароль"
        )
    
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Аккаунт деактивирован"
        )
    
    return user


async def login_user(db: AsyncSession, login: str, password: str) -> Token:
    """Авторизует пользователя и возвращает токены."""
    user = await authenticate_user(db, login, password)
    
    # Создаём токены (sub должен быть строкой по стандарту JWT)
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": str(user.id), "login": user.login},
        expires_delta=access_token_expires
    )
    refresh_token = create_refresh_token(
        data={"sub": str(user.id), "login": user.login}
    )
    
    return Token(
        access_token=access_token,
        refresh_token=refresh_token,
        token_type="bearer"
    )


async def refresh_tokens(db: AsyncSession, refresh_token: str) -> Token:
    """Обновляет токены по refresh token."""
    from ..core.security import decode_token
    
    payload = decode_token(refresh_token)
    if not payload or payload.get("type") != "refresh":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Недействительный refresh token"
        )
    
    user_id_str = payload.get("sub")
    if user_id_str is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Недействительный refresh token"
        )
    
    # Преобразуем строку в int (JWT требует, чтобы sub был строкой)
    try:
        user_id = int(user_id_str)
    except (ValueError, TypeError):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Недействительный refresh token"
        )
    
    # Ищем пользователя в БД
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    
    if not user or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Пользователь не найден или деактивирован"
        )
    
    # Создаём новые токены
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": str(user.id), "login": user.login},
        expires_delta=access_token_expires
    )
    new_refresh_token = create_refresh_token(
        data={"sub": str(user.id), "login": user.login}
    )
    
    return Token(
        access_token=access_token,
        refresh_token=new_refresh_token,
        token_type="bearer"
    )