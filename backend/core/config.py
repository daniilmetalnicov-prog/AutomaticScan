from pydantic_settings import BaseSettings
from pydantic import ConfigDict
from functools import lru_cache


class Settings(BaseSettings):
    """Настройки приложения. Читаются из переменных окружения."""
    
    # Название приложения
    APP_NAME: str = "AutomaticScan"
    APP_VERSION: str = "1.0.0"
    
    # Настройки базы данных
    POSTGRES_USER: str
    POSTGRES_PASSWORD: str
    POSTGRES_DB: str
    POSTGRES_HOST: str = "localhost"
    POSTGRES_PORT: int = 5432
    
    # URL для подключения к БД (формируется автоматически)
    @property
    def DATABASE_URL(self) -> str:
        return f"postgresql+asyncpg://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
    
    # Настройки CORS (разрешаем запросы с фронтенда)
    CORS_ORIGINS: list[str] = ["http://localhost:3000", "http://localhost:5173"]
    
    # Конфигурация Pydantic
    model_config = ConfigDict(
        env_file=".env", 		# Читаем переменные из файла .env
        env_file_encoding="utf-8",
        extra="ignore",  		# Если в .env есть переменные, которых нет в классе Settings — просто игнорируй их, не выдавай ошибку
    )


@lru_cache()
def get_settings() -> Settings:
    """Возвращает кэшированный экземпляр настроек."""
    return Settings()