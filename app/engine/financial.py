"""Модель оценки финансовых потерь бизнеса.

Рассчитывает потенциальные потери выручки от оттока, нормализованный MRR
и дефицит баланса для ближайших продлений услуг.
"""

from typing import List, Dict, Any
from app.models import Service, Account, PaymentTerm

TERM_TO_MONTHLY_MULTIPLIER: Dict[PaymentTerm, float] = {
    'hour': 720.0,
    'week': 4.33333333,
    'month': 1.0,
    'quarter_year': 1.0 / 3.0,
    'half_year': 1.0 / 6.0,
    'year': 1.0 / 12.0
}


def calculate_service_mrr(service: Service) -> int:
    """Рассчитать нормализованную ежемесячную регулярную выручку (MRR) по услуге в евроцентах."""
    mult = TERM_TO_MONTHLY_MULTIPLIER.get(service.paymentTerm, 1.0)
    return int(round(service.price * mult))


def calculate_customer_financials(
    account: Account,
    services: List[Service],
    risk_score: float
) -> Dict[str, Any]:
    """Рассчитать финансовые показатели клиента.

    Включает стоимость предстоящего продления, доступный баланс,
    дефицит средств и потенциальные ежемесячные потери с учётом вероятности оттока.
    """
    renewable = [s for s in services if s.status in ('active', 'suspended', 'prolong_wait')]
    upcoming_renewal_cents = sum(s.price for s in renewable)

    usable_balance = account.balance
    if account.bonusState == 'unlocked':
        usable_balance += account.bonusBalance

    balance_deficit_cents = max(0, upcoming_renewal_cents - usable_balance)
    total_mrr_cents = sum(calculate_service_mrr(s) for s in renewable)

    p_risk = (risk_score or 0.0) / 100.0
    if any(s.status == 'prolong_wait' for s in renewable) and balance_deficit_cents > 0:
        p_risk = max(p_risk, 0.85)

    potential_monthly_loss_cents = int(round(total_mrr_cents * p_risk))

    return {
        "services_count": len(services),
        "active_services_count": sum(1 for s in services if s.status == 'active'),
        "services_at_risk_count": len(renewable) if p_risk >= 0.35 else 0,
        "total_mrr_cents": total_mrr_cents,
        "total_mrr_eur": round(total_mrr_cents / 100.0, 2),
        "potential_monthly_loss_cents": potential_monthly_loss_cents,
        "potential_monthly_loss_eur": round(potential_monthly_loss_cents / 100.0, 2),
        "upcoming_renewal_cost_cents": upcoming_renewal_cents,
        "upcoming_renewal_cost_eur": round(upcoming_renewal_cents / 100.0, 2),
        "balance_deficit_cents": balance_deficit_cents,
        "balance_deficit_eur": round(balance_deficit_cents / 100.0, 2),
    }


def get_loss_explanation_text(
    total_loss_eur: float,
    total_mrr_eur: float,
    total_deficit_eur: float,
    forecast_days: int
) -> str:
    """Сформировать текстовое объяснение методики расчёта потенциальных финансовых потерь."""
    if forecast_days == 30:
        mrr_desc = f"Общая сумма ежемесячной выручки (MRR) под риском составляет €{total_mrr_eur:,.2f}."
    else:
        base_monthly = round(total_mrr_eur / (forecast_days / 30.0), 2)
        mrr_desc = (
            f"Выручка под риском на горизонт {forecast_days} дн. составляет €{total_mrr_eur:,.2f} "
            f"(при базовом месячном MRR €{base_monthly:,.2f}/мес)."
        )

    return (
        f"Оценка потенциальных потерь бизнеса (€{total_loss_eur:,.2f}) рассчитана на горизонт {forecast_days} дней "
        f"как математическое ожидание недополученной выручки по услугам клиентов с учётом вероятности "
        f"их оттока (Risk Score / 100), статуса автопродления и дефицита баланса аккаунта. "
        f"{mrr_desc} "
        f"Суммарный кассовый дефицит для ближайших продлений составляет €{total_deficit_eur:,.2f}."
    )
