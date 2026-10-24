"""
Эндпоинт экспорта метрик в формате Prometheus.
"""

from fastapi import APIRouter, Response
from app.database import repo

router = APIRouter(tags=["Метрики"])


@router.get("/metrics", summary="Метрики в формате Prometheus")
async def get_prometheus_metrics():
    """
    Отдаёт актуальные агрегированные показатели в формате, совместимом с Prometheus:
    - Количество клиентов по уровням риска (high, medium, low, unknown)
    - Потенциальные денежные потери (в евро и евроцентах)
    - Количество услуг под риском
    - Средний риск-скор
    - Счётчик пересчётов модели
    """
    summary = repo.get_summary()
    lines = [
        "# HELP churn_customers_total Количество клиентов по категориям риска",
        "# TYPE churn_customers_total gauge",
        f'churn_customers_total{{risk_level="high"}} {summary.high_risk_customers}',
        f'churn_customers_total{{risk_level="medium"}} {summary.medium_risk_customers}',
        f'churn_customers_total{{risk_level="low"}} {summary.low_risk_customers}',
        f'churn_customers_total{{risk_level="unknown"}} {summary.unknown_risk_customers}',
        "",
        "# HELP churn_potential_monetary_loss_cents Оценка потенциальных денежных потерь в евроцентах",
        "# TYPE churn_potential_monetary_loss_cents gauge",
        f"churn_potential_monetary_loss_cents {summary.total_potential_loss_cents}",
        "",
        "# HELP churn_potential_monetary_loss_eur Оценка потенциальных денежных потерь в евро",
        "# TYPE churn_potential_monetary_loss_eur gauge",
        f"churn_potential_monetary_loss_eur {summary.total_potential_loss_eur:.2f}",
        "",
        "# HELP churn_services_at_risk_total Общее количество услуг под риском оттока",
        "# TYPE churn_services_at_risk_total gauge",
        f"churn_services_at_risk_total {summary.services_at_risk}",
        "",
        "# HELP churn_avg_risk_score Средний показатель risk-score по клиентам с оценкой",
        "# TYPE churn_avg_risk_score gauge",
        f"churn_avg_risk_score {summary.average_risk_score if summary.average_risk_score is not None else 0.0}",
        "",
        "# HELP churn_recalculations_total Количество выполненных пересчетов модели",
        "# TYPE churn_recalculations_total counter",
        f"churn_recalculations_total {repo.recalculation_counter}",
        ""
    ]
    content = "\n".join(lines)
    return Response(content=content, media_type="text/plain; version=0.0.4; charset=utf-8")
