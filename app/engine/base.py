"""
Базовые классы и структуры модульного аналитического движка оценки рисков.
"""

from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
from pydantic import BaseModel
from app.models import Account, Service, Transaction


class FeatureResult(BaseModel):
    feature_name: str
    weight: float
    raw_score: float
    weighted_score: float
    reason: Optional[str] = None
    details: Dict[str, Any] = {}


class EvaluationContext(BaseModel):
    reference_time: Optional[str] = None
    forecast_days: int = 30
    weights: Dict[str, float] = {}


class BaseFeature(ABC):
    """
    Абстрактный базовый класс для признаков скоринговой модели.
    Для добавления нового признака достаточно отнаследоваться от него и объявить @register_feature.
    """
    feature_name: str
    description: str
    default_weight: float = 20.0

    @abstractmethod
    def compute(
        self,
        account: Account,
        services: List[Service],
        transactions: List[Transaction],
        context: EvaluationContext
    ) -> FeatureResult:
        """
        Вычисление балла риска по признаку (от 0.0 до 100.0) и текстового объяснения.
        """
        pass
