from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List, Optional
from ..models.audit_log import AuditLog
from ..schemas.audit_log import AuditLogCreate


async def create_audit_log(
    db: AsyncSession,
    log_data: AuditLogCreate
) -> AuditLog:
    """Создаёт запись аудита."""
    audit_log = AuditLog(**log_data.model_dump())
    db.add(audit_log)
    await db.flush()
    await db.refresh(audit_log)
    return audit_log


async def get_audit_logs(
    db: AsyncSession,
    user_login: Optional[str] = None,
    action_type: Optional[str] = None,
    skip: int = 0,
    limit: int = 100
) -> List[AuditLog]:
    """Получает записи аудита с фильтрацией."""
    query = select(AuditLog).order_by(AuditLog.created_at.desc())
    
    if user_login:
        query = query.where(AuditLog.user_login == user_login)
    if action_type:
        query = query.where(AuditLog.action_type == action_type)
    
    query = query.offset(skip).limit(limit)
    
    result = await db.execute(query)
    return result.scalars().all()