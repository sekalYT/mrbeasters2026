"""Признак риска: статус автоматического продления услуг."""

from typing import List
from app.models import Account, Service, Transaction
from app.engine.base import BaseFeature, FeatureResult, EvaluationContext
from app.engine.registry import register_feature


@register_feature
class AutoProlongFeature(BaseFeature):
    """Оценивает долю продлеваемых услуг с отключенным автопродлением."""
    feature_name = "w_auto_prolong_off"
    description = "Отключение автоматического продления на активных услугах"
    default_weight = 35.0

    def compute(
        self,
        account: Account,
        services: List[Service],
        transactions: List[Transaction],
        context: EvaluationContext
    ) -> FeatureResult:
        weight = context.weights.get(self.feature_name, self.default_weight)

        renewable = [s for s in services if s.status in ('active', 'suspended', 'prolong_wait')]
        if not renewable:
            return FeatureResult(
                feature_name=self.feature_name,
                weight=weight,
                raw_score=0.0,
                weighted_score=0.0,
                reason=None,
                details={"renewable_count": 0, "off_count": 0}
            )

        off_count = sum(1 for s in renewable if not s.autoProlong)
        ratio = off_count / len(renewable)
        raw_score = round(ratio * 100.0, 2)
        weighted_score = round((raw_score * weight) / 100.0, 2)

        reason = None
        if off_count > 0:
            reason = f"Автопродление отключено на {off_count} из {len(renewable)} услуг ({raw_score:.0f}%)"

        return FeatureResult(
            feature_name=self.feature_name,
            weight=weight,
            raw_score=raw_score,
            weighted_score=weighted_score,
            reason=reason,
            details={
                "renewable_count": len(renewable),
                "auto_prolong_off_count": off_count,
                "ratio": ratio
            }
        )
