from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List
from ..core.database import get_db
from ..schemas.host import HostResponse, HostSyncResult
from ..services import host_service

# Создаём роутер с префиксом /api/hosts
router = APIRouter(prefix="/api/hosts", tags=["Объекты"])


# ============================================================
# ВАЖНО: порядок маршрутов критичен для FastAPI!
# Конкретные маршруты (без параметров в пути) должны идти
# ПЕРЕД маршрутами с параметрами (/{host_id}), иначе FastAPI
# будет воспринимать "search", "redcheck" и т.д. как значения host_id
# ============================================================


# --- СИНХРОНИЗАЦИЯ ---

@router.post("/sync/{group_id}", response_model=HostSyncResult)
async def sync_hosts(
    group_id: int,
    redcheck_hosts: List[dict],
    db: AsyncSession = Depends(get_db)
):
    """
    Синхронизировать хосты из RedCheck с БД для конкретной группы.
    
    В реальном приложении здесь будет запрос к RedCheck API 
    с параметром GroupId. Пока что принимаем список хостов 
    в теле запроса для тестирования.
    """
    return await host_service.sync_hosts_from_redcheck(db, group_id, redcheck_hosts)


# --- ПОИСК ---

@router.get("/search", response_model=List[HostResponse])
async def search_hosts(
    connection_address: str = Query(..., description="IP-адрес или имя хоста для поиска (частичное совпадение)"),
    db: AsyncSession = Depends(get_db)
):
    """Поиск хостов по IP-адресу или имени."""
    return await host_service.get_host_by_connection_address(db, connection_address)


# --- СПИСОК ---

@router.get("/", response_model=List[HostResponse])
async def get_hosts(
    group_id: int = Query(..., description="ID группы для фильтрации"),
    skip: int = 0,
    limit: int = 100,
    db: AsyncSession = Depends(get_db)
):
    """Получить список хостов для конкретной группы."""
    return await host_service.get_hosts_by_group(db, group_id, skip=skip, limit=limit)


# --- ПО ВНЕШНЕМУ ID ---

@router.get("/redcheck/{redcheck_id}", response_model=HostResponse)
async def get_host_by_redcheck_id(
    redcheck_id: int,
    db: AsyncSession = Depends(get_db)
):
    """Получить хост по ID из RedCheck."""
    return await host_service.get_host_by_redcheck_id(db, redcheck_id)


# --- ПО ВНУТРЕННЕМУ ID ---

@router.get("/{host_id}", response_model=HostResponse)
async def get_host(
    host_id: int,
    db: AsyncSession = Depends(get_db)
):
    """Получить хост по внутреннему ID."""
    return await host_service.get_host(db, host_id)


# --- УДАЛЕНИЕ (всегда в конце!) ---

@router.delete("/{host_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_host(
    host_id: int,
    db: AsyncSession = Depends(get_db)
):
    """
    Удалить хост из БД (не из RedCheck).
    
    Внимание: это удаление только из локальной БД.
    Хост останется в сканере уязвимостей RedCheck.
    """
    await host_service.delete_host(db, host_id)