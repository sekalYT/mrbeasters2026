"""Признак риска: наличие услуг в статусе ожидания оплаты (prolong_wait)."""

from typing import List
from app.models import Account, Service, Transaction
from app.engine.base import BaseFeature, FeatureResult, EvaluationContext
from app.engine.registry import register_feature


@register_feature
class ProlongWaitFeature(BaseFeature):
    """Определяет наличие услуг с истёкшим сроком действия в 5-дневном льготном периоде перед удалением."""
    feature_name = "w_prolong_wait"
    description = "Наличие услуг в статусе ожидания оплаты (prolong_wait, угроза удаления через 5 дней)"
    default_weight = 25.0

    def compute(
        self,
        account: Account,
        services: List[Service],
        transactions: List[Transaction],
        context: EvaluationContext
    ) -> FeatureResult:
        weight = context.weights.get(self.feature_name, self.default_weight)

        prolong_wait_services = [s for s in services if s.status == 'prolong_wait']
        active_or_pw = [s for s in services if s.status in ('active', 'suspended', 'prolong_wait')]

        if not prolong_wait_services:
            return FeatureResult(
                feature_name=self.feature_name,
                weight=weight,
                raw_score=0.0,
                weighted_score=0.0,
                reason=None,
                details={"prolong_wait_count": 0}
            )

        ratio = len(prolong_wait_services) / max(1, len(active_or_pw))
        raw_score = min(100.0, 50.0 + ratio * 50.0)

        usable_balance = account.balance + (account.bonusBalance if account.bonusState == 'unlocked' else 0)
        if usable_balance == 0:
            raw_score = 100.0

        weighted_score = round((raw_score * weight) / 100.0, 2)
        names = ", ".join(s.name for s in prolong_wait_services[:3])
        if len(prolong_wait_services) > 3:
            names += f" (+{len(prolong_wait_services) - 3})"

        reason = (
            f"{len(prolong_wait_services)} услуг(и) в статусе prolong_wait ({names}) — "
            f"риск безвозвратного удаления по истечении 5 дней"
        )
        if usable_balance == 0:
            reason += " при нулевом балансе"

        return FeatureResult(
            feature_name=self.feature_name,
            weight=weight,
            raw_score=round(raw_score, 2),
            weighted_score=weighted_score,
            reason=reason,
            details={
                "prolong_wait_count": len(prolong_wait_services),
                "service_ids": [s.id for s in prolong_wait_services]
            }
        )
