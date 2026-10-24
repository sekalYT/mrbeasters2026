"""
Маршруты сводной аналитики риска оттока и финансовых показателей.
"""

from fastapi import APIRouter, Depends
from app.models import AnalyticsSummary, UserInfo
from app.auth import get_current_user
from app.database import repo

router = APIRouter(prefix="/api/v1/analytics", tags=["Аналитика"])


@router.get("/summary", response_model=AnalyticsSummary, summary="Сводные показатели риска и денежной оценки")
async def get_analytics_summary(current_user: UserInfo = Depends(get_current_user)):
    """
    Получение сводных показателей риска, распределения клиентов по уровням,
    денежной оценки потенциальных потерь и данных для графика оттока.
    """
    return repo.get_summary()
