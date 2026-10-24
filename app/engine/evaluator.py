"""Оркестратор оценки рисков.

Рассчитывает баллы риска, лояльность, уровни риска,
факторные объяснения и сводную аналитику портфеля клиентов.
"""

from typing import List, Dict, Tuple
from app.models import (
    Account, Service, Transaction, ModelSettings,
    CustomerDetail, AnalyticsSummary,
    FeatureExplanation, ChurnForecastPoint
)
from app.engine.registry import get_all_features
from app.engine.base import EvaluationContext
from app.engine.financial import (
    calculate_customer_financials,
    get_loss_explanation_text
)


def evaluate_customer(
    account: Account,
    services: List[Service],
    transactions: List[Transaction],
    settings: ModelSettings
) -> CustomerDetail:
    """Выполнить оценку отдельного клиента.

    При недостаточности данных (например, 0 услуг) явно устанавливает
    risk_score равным None и risk_level равным 'unknown'.
    """
    if not services:
        financials = calculate_customer_financials(account, [], 0.0)
        return CustomerDetail(
            id=account.id,
            email=account.email,
            balance=account.balance,
            balance_eur=round(account.balance / 100.0, 2),
            withdrawBalance=account.withdrawBalance,
            withdrawBalance_eur=round(account.withdrawBalance / 100.0, 2),
            totalReplenished=account.totalReplenished,
            totalReplenished_eur=round(account.totalReplenished / 100.0, 2),
            bonusBalance=account.bonusBalance,
            bonusBalance_eur=round(account.bonusBalance / 100.0, 2),
            bonusState=account.bonusState,
            risk_score=None,
            risk_level="unknown",
            loyalty_score=None,
            reasons=["Отсутствует оценка: недостаточно данных (у клиента нет услуг)"],
            explanations=[],
            services=[],
            transactions=transactions,
            **financials
        )

    weights_dict = {
        "w_auto_prolong_off": settings.w_auto_prolong_off,
        "w_insufficient_funds": settings.w_insufficient_funds,
        "w_prolong_wait": settings.w_prolong_wait,
        "w_failed_tx_ratio": settings.w_failed_tx_ratio,
    }
    context = EvaluationContext(
        forecast_days=settings.forecast_days,
        weights=weights_dict
    )

    features = get_all_features()
    total_weighted_score = 0.0
    total_weights = 0.0
    reasons: List[str] = []
    explanations: List[FeatureExplanation] = []

    for feat in features:
        res = feat.compute(account, services, transactions, context)
        total_weighted_score += res.weighted_score
        total_weights += res.weight
        if res.reason:
            reasons.append(res.reason)
        explanations.append(
            FeatureExplanation(
                feature_name=res.feature_name,
                weight=res.weight,
                raw_score=res.raw_score,
                weighted_score=res.weighted_score,
                reason=res.reason or "В норме"
            )
        )

    if total_weights > 0:
        normalized_score = min(100.0, max(0.0, (total_weighted_score / total_weights) * 100.0))
    else:
        normalized_score = 0.0

    risk_score = round(normalized_score, 1)

    if risk_score >= settings.threshold_high:
        risk_level = "high"
    elif risk_score >= settings.threshold_medium:
        risk_level = "medium"
    else:
        risk_level = "low"

    loyalty_score = round(max(0.0, 100.0 - risk_score), 1)

    if not reasons:
        reasons.append("Низкий риск: автопродление включено, баланса достаточно для продления")

    financials = calculate_customer_financials(account, services, risk_score)

    return CustomerDetail(
        id=account.id,
        email=account.email,
        balance=account.balance,
        balance_eur=round(account.balance / 100.0, 2),
        withdrawBalance=account.withdrawBalance,
        withdrawBalance_eur=round(account.withdrawBalance / 100.0, 2),
        totalReplenished=account.totalReplenished,
        totalReplenished_eur=round(account.totalReplenished / 100.0, 2),
        bonusBalance=account.bonusBalance,
        bonusBalance_eur=round(account.bonusBalance / 100.0, 2),
        bonusState=account.bonusState,
        risk_score=risk_score,
        risk_level=risk_level,
        loyalty_score=loyalty_score,
        reasons=reasons,
        explanations=explanations,
        services=services,
        transactions=transactions,
        **financials
    )


def evaluate_all(
    accounts: List[Account],
    services: List[Service],
    transactions: List[Transaction],
    settings: ModelSettings
) -> Tuple[List[CustomerDetail], AnalyticsSummary]:
    """Выполнить оценку всех клиентов и сформировать сводную аналитику."""
    services_by_owner: Dict[int, List[Service]] = {a.id: [] for a in accounts}
    for s in services:
        if s.ownerId in services_by_owner:
            services_by_owner[s.ownerId].append(s)

    service_to_owner = {s.id: s.ownerId for s in services}
    tx_by_owner: Dict[int, List[Transaction]] = {a.id: [] for a in accounts}
    for t in transactions:
        owner_id = service_to_owner.get(t.serviceId)
        if owner_id and owner_id in tx_by_owner:
            tx_by_owner[owner_id].append(t)

    customer_details: List[CustomerDetail] = []
    for acc in accounts:
        detail = evaluate_customer(
            acc,
            services_by_owner.get(acc.id, []),
            tx_by_owner.get(acc.id, []),
            settings
        )
        customer_details.append(detail)

    high_count = sum(1 for c in customer_details if c.risk_level == 'high')
    med_count = sum(1 for c in customer_details if c.risk_level == 'medium')
    low_count = sum(1 for c in customer_details if c.risk_level == 'low')
    unk_count = sum(1 for c in customer_details if c.risk_level == 'unknown')

    scores_with_data = [c.risk_score for c in customer_details if c.risk_score is not None]
    avg_score = round(sum(scores_with_data) / len(scores_with_data), 1) if scores_with_data else None

    horizon_ratio = max(1, settings.forecast_days) / 30.0
    monthly_loss_cents = sum(c.potential_monthly_loss_cents for c in customer_details)
    total_loss_cents = int(round(monthly_loss_cents * horizon_ratio))
    total_loss_eur = round(total_loss_cents / 100.0, 2)
    
    base_mrr_cents = sum(c.total_mrr_cents for c in customer_details if c.risk_level in ('high', 'medium'))
    total_mrr_cents = int(round(base_mrr_cents * horizon_ratio))
    total_mrr_eur = round(total_mrr_cents / 100.0, 2)

    total_deficit_cents = sum(c.balance_deficit_cents for c in customer_details)
    total_deficit_eur = round(total_deficit_cents / 100.0, 2)

    services_at_risk = sum(c.services_at_risk_count for c in customer_details)

    fact_deleted = sum(1 for s in services if s.status == 'deleted')
    fact_suspended = sum(1 for s in services if s.status == 'suspended')
    forecast_pw = sum(1 for s in services if s.status == 'prolong_wait')
    forecast_active_off = sum(1 for s in services if s.status == 'active' and not s.autoProlong)

    chart_data = [
        ChurnForecastPoint(
            label="Исторический факт: Удалено",
            fact_deleted_services=fact_deleted,
            forecast_at_risk_services=0,
            forecast_lost_revenue_eur=0.0
        ),
        ChurnForecastPoint(
            label="Исторический факт: Выключено (suspended)",
            fact_deleted_services=fact_suspended,
            forecast_at_risk_services=0,
            forecast_lost_revenue_eur=0.0
        ),
        ChurnForecastPoint(
            label="Прогноз 5 дней: prolong_wait",
            fact_deleted_services=0,
            forecast_at_risk_services=forecast_pw,
            forecast_lost_revenue_eur=round(forecast_pw * 35.0, 2)
        ),
        ChurnForecastPoint(
            label=f"Прогноз {settings.forecast_days} дней: Автопродление ВЫКЛ",
            fact_deleted_services=0,
            forecast_at_risk_services=forecast_active_off,
            forecast_lost_revenue_eur=round(total_loss_eur * 0.7, 2)
        ),
        ChurnForecastPoint(
            label=f"Прогноз {settings.forecast_days} дней: Полный риск оттока",
            fact_deleted_services=0,
            forecast_at_risk_services=services_at_risk,
            forecast_lost_revenue_eur=total_loss_eur
        )
    ]

    explanation = get_loss_explanation_text(
        total_loss_eur, total_mrr_eur, total_deficit_eur, settings.forecast_days
    )

    summary = AnalyticsSummary(
        total_customers=len(customer_details),
        high_risk_customers=high_count,
        medium_risk_customers=med_count,
        low_risk_customers=low_count,
        unknown_risk_customers=unk_count,
        total_services=len(services),
        services_at_risk=services_at_risk,
        total_potential_loss_cents=total_loss_cents,
        total_potential_loss_eur=total_loss_eur,
        total_mrr_at_risk_eur=total_mrr_eur,
        total_balance_deficit_eur=total_deficit_eur,
        average_risk_score=avg_score,
        loss_calculation_explanation=explanation,
        forecast_chart_data=chart_data
    )

    return customer_details, summary
