"""
Маршруты клиентов: получение списка с фильтрацией и сортировкой, а также детальной информации.
"""

from typing import List, Optional
from fastapi import APIRouter, Query, HTTPException, status, Depends
from app.models import CustomerRiskScore, CustomerDetail, UserInfo
from app.auth import get_current_user
from app.database import repo

router = APIRouter(prefix="/api/v1/customers", tags=["Клиенты"])


@router.get("", response_model=List[CustomerDetail], summary="Получение списка клиентов с оценками риска")
async def get_customers(
    risk_level: Optional[str] = Query(
        None,
        description="Фильтр по уровню риска: high, medium, low, unknown или all"
    ),
    sort_by: str = Query(
        "risk_score",
        description="Поле для сортировки: id, email, balance, totalReplenished, risk_score, loyalty_score"
    ),
    sort_order: str = Query(
        "desc",
        pattern="^(asc|desc)$",
        description="Направление сортировки: asc (по возрастанию) или desc (по убыванию)"
    ),
    search: Optional[str] = Query(
        None,
        description="Поиск по email или ID клиента"
    ),
    current_user: UserInfo = Depends(get_current_user)
):
    """
    Получение списка клиентов с оценками риска.
    Поддерживает фильтрацию по уровням риска и двунаправленную сортировку
    по ID, email, balance, totalReplenished и risk_score.
    """
    valid_sort_fields = {
        "id", "email", "balance", "totalReplenished",
        "risk_score", "loyalty_score", "potential_monthly_loss_cents"
    }
    if sort_by not in valid_sort_fields:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Недопустимое поле сортировки '{sort_by}'. Доступны: {', '.join(sorted(valid_sort_fields))}"
        )

    return repo.get_customers(
        risk_level=risk_level,
        sort_by=sort_by,
        sort_order=sort_order,
        search=search
    )


@router.get("/{id}", response_model=CustomerDetail, summary="Получение подробной оценки клиента")
async def get_customer_by_id(
    id: int,
    current_user: UserInfo = Depends(get_current_user)
):
    """
    Получение подробной оценки клиента, списка его услуг, признаков риска и объяснений.
    """
    customer = repo.get_customer_by_id(id)
    if not customer:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Клиент с ID {id} не найден"
        )
    return customer
