from fastapi import Request, HTTPException, status
from fastapi.responses import JSONResponse
from sqlalchemy.exc import IntegrityError, OperationalError, SQLAlchemyError
import logging

logger = logging.getLogger(__name__)


async def integrity_error_handler(request: Request, exc: IntegrityError):
    """
    Обработчик ошибок целостности БД (нарушение уникальности, FK и т.д.).
    """
    logger.error(f"IntegrityError: {exc}")
    return JSONResponse(
        status_code=status.HTTP_409_CONFLICT,
        content={
            "detail": "Ошибка целостности данных",
            "error": str(exc.orig) if hasattr(exc, 'orig') else str(exc)
        }
    )


async def operational_error_handler(request: Request, exc: OperationalError):
    """
    Обработчик ошибок подключения к БД.
    """
    logger.error(f"OperationalError: {exc}")
    return JSONResponse(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        content={
            "detail": "База данных недоступна",
            "error": "Попробуйте позже"
        }
    )


async def sqlalchemy_error_handler(request: Request, exc: SQLAlchemyError):
    """
    Обработчик общих ошибок SQLAlchemy.
    """
    logger.error(f"SQLAlchemyError: {exc}")
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "detail": "Внутренняя ошибка базы данных",
            "error": "Обратитесь к администратору"
        }
    )