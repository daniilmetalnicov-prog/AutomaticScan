from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase
from .config import get_settings


# Получаем настройки
settings = get_settings()

# Создаём асинхронный движок SQLAlchemy
engine = create_async_engine(
    settings.DATABASE_URL,
    echo=False,  # True = показывать SQL-запросы в консоли (для отладки)
    pool_pre_ping=True,  # Проверять соединение перед использованием
)

# Создаём фабрику сессий
async_session_factory = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,  # Не обновлять объекты после commit
)


class Base(DeclarativeBase):
    """Базовый класс для всех моделей."""
    pass


async def get_db() -> AsyncSession:
    """Генератор для получения сессии БД. Используется в эндпоинтах."""
    async with async_session_factory() as session:
        try:
            yield session
            await session.commit()  # Автоматически коммитим при успехе
        except Exception:
            await session.rollback()  # Откатываем при ошибке
            raise
        finally:
            await session.close()  # Закрываем сессию