from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional
from ..core.database import get_db
from ..schemas.audit_log import AuditLogCreate, AuditLogResponse
from ..services import audit_log_service

router = APIRouter(prefix="/api/audit-logs", tags=["Аудит"])


# --- СОЗДАНИЕ ---

@router.post("/", response_model=AuditLogResponse, status_code=201)
async def create_audit_log(
    log_data: AuditLogCreate,
    db: AsyncSession = Depends(get_db)
):
    """Создать запись аудита."""
    return await audit_log_service.create_audit_log(db, log_data)


# --- ЧТЕНИЕ ---

@router.get("/", response_model=List[AuditLogResponse])
async def get_audit_logs(
    user_login: Optional[str] = Query(None, description="Фильтр по логину пользователя"),
    action_type: Optional[str] = Query(None, description="Фильтр по типу действия"),
    skip: int = 0,
    limit: int = 100,
    db: AsyncSession = Depends(get_db)
):
    """Получить записи аудита с фильтрацией."""
    return await audit_log_service.get_audit_logs(
        db,
        user_login=user_login,
        action_type=action_type,
        skip=skip,
        limit=limit
    )