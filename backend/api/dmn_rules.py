from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List
from ..core.database import get_db
from ..schemas.dmn_rule import DmnRuleResponse, DmnDecisionResponse
from ..services import dmn_service
from ..models.dmn_rule import DmnRule
from sqlalchemy import select

router = APIRouter(prefix="/api/dmn-rules", tags=["DMN Правила"])


@router.get("/", response_model=List[DmnRuleResponse])
async def get_all_dmn_rules(
    skip: int = Query(0, description="Количество записей для пропуска"),
    limit: int = Query(100, description="Максимальное количество записей"),
    db: AsyncSession = Depends(get_db)
):
    """Получить все правила DMN."""
    result = await db.execute(
        select(DmnRule).offset(skip).limit(limit)
    )
    return result.scalars().all()


@router.post("/evaluate/{stage_run_id}", response_model=DmnDecisionResponse)
async def evaluate_dmn(
    stage_run_id: int,
    db: AsyncSession = Depends(get_db)
):
    """
    Вызвать движок DMN для определения следующего шага.
    
    Используется для тестирования DMN без интеграции с RedCheck API.
    В продакшене DMN вызывается автоматически после получения stage_output_status.
    """
    return await dmn_service.evaluate_dmn(db, stage_run_id)