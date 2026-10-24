"""Автоматическая загрузка и регистрация всех признаков риска для движка оценки оттока."""

from app.engine.features.auto_prolong import AutoProlongFeature
from app.engine.features.balance_sufficiency import BalanceSufficiencyFeature
from app.engine.features.prolong_wait import ProlongWaitFeature
from app.engine.features.transaction_failures import TransactionFailuresFeature

__all__ = [
    "AutoProlongFeature",
    "BalanceSufficiencyFeature",
    "ProlongWaitFeature",
    "TransactionFailuresFeature"
]
