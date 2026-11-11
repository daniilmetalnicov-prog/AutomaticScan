from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List
from ..core.database import get_db
from ..schemas.group import GroupResponse, GroupSyncResult
from ..services import group_service

# Создаём роутер с префиксом /api/groups
router = APIRouter(prefix="/api/groups", tags=["Группы"])


# ============================================================
# ВАЖНО: порядок маршрутов критичен для FastAPI!
# Конкретные маршруты (без параметров в пути) должны идти
# ПЕРЕД маршрутами с параметрами (/{group_id}), иначе FastAPI
# будет воспринимать "search", "redcheck" и т.д. как значения group_id
# ============================================================


# --- СИНХРОНИЗАЦИЯ ---

@router.post("/sync", response_model=GroupSyncResult)
async def sync_groups(
    redcheck_groups: List[dict],
    db: AsyncSession = Depends(get_db)
):
    """
    Синхронизировать группы из RedCheck с БД.
    
    В реальном приложении здесь будет запрос к RedCheck API.
    Пока что принимаем список групп в теле запроса для тестирования.
    """
    return await group_service.sync_groups_from_redcheck(db, redcheck_groups)


# --- ПОИСК ---

@router.get("/search", response_model=List[GroupResponse])
async def search_groups(
    name: str = Query(..., description="Название группы для поиска (частичное совпадение)"),
    db: AsyncSession = Depends(get_db)
):
    """Поиск групп по имени."""
    return await group_service.get_group_by_name(db, name)


# --- СПИСОК ---

@router.get("/", response_model=List[GroupResponse])
async def get_groups(
    skip: int = 0,
    limit: int = 100,
    db: AsyncSession = Depends(get_db)
):
    """Получить список всех групп (не удалённых в RedCheck)."""
    return await group_service.get_all_groups(db, skip=skip, limit=limit)


# --- ПО ВНЕШНЕМУ ID ---

@router.get("/redcheck/{redcheck_id}", response_model=GroupResponse)
async def get_group_by_redcheck_id(
    redcheck_id: int,
    db: AsyncSession = Depends(get_db)
):
    """Получить группу по ID из RedCheck."""
    return await group_service.get_group_by_redcheck_id(db, redcheck_id)


# --- ПО ВНУТРЕННЕМУ ID ---

@router.get("/{group_id}", response_model=GroupResponse)
async def get_group(
    group_id: int,
    db: AsyncSession = Depends(get_db)
):
    """Получить группу по внутреннему ID."""
    return await group_service.get_group(db, group_id)


# --- УДАЛЕНИЕ (всегда в конце!) ---
 
@router.delete("/{group_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_group(
    group_id: int,
    db: AsyncSession = Depends(get_db)
):
    """
    Удалить группу из БД (не из RedCheck).
    
    Внимание: это удаление только из локальной БД.
    Группа останется в сканере уязвимостей RedCheck.
    """
    await group_service.delete_group(db, group_id)