"""Реестр признаков оттока для динамического подключения модулей оценки риска."""

from typing import Dict, Type, List
from app.engine.base import BaseFeature

_REGISTRY: Dict[str, BaseFeature] = {}
_INITIALIZED: bool = False


def register_feature(cls: Type[BaseFeature]):
    """Декоратор для регистрации признака риска в реестре движка."""
    instance = cls()
    _REGISTRY[instance.feature_name] = instance
    return cls


def _ensure_features_loaded():
    global _INITIALIZED
    if not _INITIALIZED:
        import app.engine.features
        _INITIALIZED = True


def get_all_features() -> List[BaseFeature]:
    """Получить список всех зарегистрированных признаков риска."""
    _ensure_features_loaded()
    return list(_REGISTRY.values())


def get_feature(name: str) -> BaseFeature:
    """Получить признак риска по системному имени."""
    _ensure_features_loaded()
    return _REGISTRY[name]
