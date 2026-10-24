"""Признак риска: доля неудавшихся транзакций (status: not_performed)."""

from typing import List
from app.models import Account, Service, Transaction
from app.engine.base import BaseFeature, FeatureResult, EvaluationContext
from app.engine.registry import register_feature


@register_feature
class TransactionFailuresFeature(BaseFeature):
    """Оценивает соотношение неудавшихся и выполненных транзакций клиента."""
    feature_name = "w_failed_tx_ratio"
    description = "Доля неудавшихся или отмененных транзакций (status: not_performed)"
    default_weight = 10.0

    def compute(
        self,
        account: Account,
        services: List[Service],
        transactions: List[Transaction],
        context: EvaluationContext
    ) -> FeatureResult:
        weight = context.weights.get(self.feature_name, self.default_weight)

        if not transactions:
            return FeatureResult(
                feature_name=self.feature_name,
                weight=weight,
                raw_score=0.0,
                weighted_score=0.0,
                reason=None,
                details={"total_transactions": 0, "failed_transactions": 0}
            )

        failed_tx = [t for t in transactions if t.status == 'not_performed']
        ratio = len(failed_tx) / len(transactions)
        raw_score = round(ratio * 100.0, 2)
        weighted_score = round((raw_score * weight) / 100.0, 2)

        reason = None
        if len(failed_tx) > 0 and ratio >= 0.2:
            reason = (
                f"{len(failed_tx)} из {len(transactions)} транзакций не были оплачены "
                f"({raw_score:.0f}% отказов)"
            )

        return FeatureResult(
            feature_name=self.feature_name,
            weight=weight,
            raw_score=raw_score,
            weighted_score=weighted_score,
            reason=reason,
            details={
                "total_transactions": len(transactions),
                "failed_transactions": len(failed_tx),
                "failure_ratio": ratio
            }
        )
