"""Признак риска: достаточность средств на балансе аккаунта."""

from typing import List
from app.models import Account, Service, Transaction
from app.engine.base import BaseFeature, FeatureResult, EvaluationContext
from app.engine.registry import register_feature


@register_feature
class BalanceSufficiencyFeature(BaseFeature):
    """Оценивает достаточность реального баланса и разблокированных бонусов для предстоящих продлений услуг."""
    feature_name = "w_insufficient_funds"
    description = "Недостаточность средств на аккаунте для предстоящих продлений"
    default_weight = 30.0

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
                details={"renewal_cost_cents": 0, "usable_balance_cents": account.balance}
            )

        renewal_cost = sum(s.price for s in renewable)

        usable_balance = account.balance
        if account.bonusState == 'unlocked':
            usable_balance += account.bonusBalance

        reason = None
        if usable_balance >= renewal_cost:
            raw_score = 0.0
            deficit = 0
        else:
            deficit = renewal_cost - usable_balance
            if renewal_cost > 0:
                raw_score = min(100.0, (deficit / renewal_cost) * 100.0)
            else:
                raw_score = 0.0

            deficit_eur = deficit / 100.0
            renewal_eur = renewal_cost / 100.0
            usable_eur = usable_balance / 100.0
            reason = (
                f"Недостаточно средств для продления услуг: требуется €{renewal_eur:.2f}, "
                f"доступно €{usable_eur:.2f} (дефицит €{deficit_eur:.2f})"
            )

        weighted_score = round((raw_score * weight) / 100.0, 2)

        return FeatureResult(
            feature_name=self.feature_name,
            weight=weight,
            raw_score=round(raw_score, 2),
            weighted_score=weighted_score,
            reason=reason,
            details={
                "renewal_cost_cents": renewal_cost,
                "usable_balance_cents": usable_balance,
                "deficit_cents": max(0, renewal_cost - usable_balance)
            }
        )
