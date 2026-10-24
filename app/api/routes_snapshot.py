"""
Маршруты загрузки и обновления снимков исходных данных.
"""

from fastapi import APIRouter, Depends
from app.models import DataSnapshot, UserInfo
from app.auth import get_current_user
from app.database import repo
from app.api.events import broadcast_event

router = APIRouter(prefix="/api/v1/source", tags=["Источник данных"])


@router.put("/snapshot", summary="Загрузка или полная замена снимка исходных данных")
async def put_snapshot(
    snapshot: DataSnapshot,
    current_user: UserInfo = Depends(get_current_user)
):
    """
    Загрузка или полная замена снимка исходных данных (аккаунты, услуги, транзакции)
    с автоматическим пересчётом всех показателей риска.
    """
    repo.set_snapshot(snapshot)
    
    await broadcast_event("recalculated", {"source": "snapshot_update"})
    
    summary = repo.get_summary()
    return {
        "status": "success",
        "message": "Снимок данных успешно загружен и пересчитан",
        "accounts_count": len(snapshot.accounts),
        "services_count": len(snapshot.services),
        "transactions_count": len(snapshot.transactions),
        "total_potential_loss_eur": summary.total_potential_loss_eur,
        "high_risk_customers": summary.high_risk_customers
    }


@router.post("/reset", summary="Сброс данных к исходному снимку data.json")
async def reset_snapshot(
    current_user: UserInfo = Depends(get_current_user)
):
    """
    Сброс данных к исходному состоянию из базового файла data.json.
    """
    import json
    from app.config import DEFAULT_DATA_FILE
    with open(DEFAULT_DATA_FILE, "r", encoding="utf-8") as f:
        snapshot = DataSnapshot(**json.load(f))
    repo.set_snapshot(snapshot)
    await broadcast_event("recalculated", {"source": "snapshot_reset"})
    summary = repo.get_summary()
    return {
        "status": "success",
        "message": "Данные успешно сброшены к исходному снимку data.json",
        "accounts_count": len(snapshot.accounts),
        "services_count": len(snapshot.services),
        "transactions_count": len(snapshot.transactions),
        "total_potential_loss_eur": summary.total_potential_loss_eur,
        "high_risk_customers": summary.high_risk_customers
    }


@router.post("/load-demo-2", summary="Загрузка демонстрационного набора данных data2-test.json")
async def load_demo_2(
    current_user: UserInfo = Depends(get_current_user)
):
    """
    Загрузка расширенного демонстрационного набора данных (25 клиентов, кассовый дефицит, клиенты высокого риска).
    """
    import json
    from app.config import BASE_DIR
    demo_file = BASE_DIR / "data" / "data2-test.json"
    with open(demo_file, "r", encoding="utf-8") as f:
        snapshot = DataSnapshot(**json.load(f))
    repo.set_snapshot(snapshot)
    await broadcast_event("recalculated", {"source": "snapshot_demo2"})
    summary = repo.get_summary()
    return {
        "status": "success",
        "message": "Тестовый набор данных 2 успешно загружен",
        "accounts_count": len(snapshot.accounts),
        "services_count": len(snapshot.services),
        "transactions_count": len(snapshot.transactions),
        "total_potential_loss_eur": summary.total_potential_loss_eur,
        "high_risk_customers": summary.high_risk_customers
    }
