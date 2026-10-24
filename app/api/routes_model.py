"""
Маршруты управления параметрами и коэффициентами скоринговой модели.
"""

from fastapi import APIRouter, Depends
from app.models import ModelSettings, ModelSettingsUpdate, UserInfo
from app.auth import get_current_user
from app.database import repo
from app.api.events import broadcast_event

router = APIRouter(prefix="/api/v1/model", tags=["Настройки модели"])


@router.get("/settings", response_model=ModelSettings, summary="Получение действующих настроек модели")
async def get_model_settings(current_user: UserInfo = Depends(get_current_user)):
    """
    Получение действующих настроек, порогов и весовых коэффициентов модели.
    """
    return repo.get_settings()


@router.patch("/settings", response_model=ModelSettings, summary="Изменение настроек модели с пересчётом")
async def update_model_settings(
    update_data: ModelSettingsUpdate,
    current_user: UserInfo = Depends(get_current_user)
):
    """
    Изменение настроек и весовых коэффициентов модели.
    Автоматически пересчитывает оценки и сохраняет изменения в конфигурацию.
    """
    current_settings = repo.get_settings()
    current_dict = current_settings.model_dump()
    
    update_dict = update_data.model_dump(exclude_unset=True)
    current_dict.update(update_dict)
    
    new_settings = ModelSettings(**current_dict)
    repo.save_settings(new_settings)
    
    await broadcast_event("recalculated", {"source": "settings_update"})
    
    return new_settings
