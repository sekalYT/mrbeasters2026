"""
Unit tests for the Risk Engine and Financial Loss Model.
"""

from datetime import datetime, timezone
import pytest

from app.models import Account, Service, Transaction, ModelSettings
from app.engine.evaluator import evaluate_customer, evaluate_all
from app.engine.financial import calculate_service_mrr, calculate_customer_financials


def test_customer_with_no_services_has_unknown_risk():
    """
    Requirement 1: 'При недостатке данных по клиенту необходимо явно указать отсутствие оценки.'
    """
    account = Account(
        id=999,
        email="empty@example.test",
        balance=10000,
        withdrawBalance=0,
        totalReplenished=10000,
        bonusBalance=0,
        bonusState="locked"
    )
    settings = ModelSettings()
    result = evaluate_customer(account, services=[], transactions=[], settings=settings)

    assert result.risk_score is None
    assert result.risk_level == "unknown"
    assert result.loyalty_score is None
    assert len(result.reasons) > 0
    assert "недостаточно данных" in result.reasons[0].lower()


def test_customer_high_risk_prolong_wait_and_no_balance():
    """
    Service in prolong_wait with insufficient balance should trigger high risk.
    """
    account = Account(
        id=1,
        email="test@example.test",
        balance=0,
        withdrawBalance=0,
        totalReplenished=5000,
        bonusBalance=0,
        bonusState="locked"
    )
    service = Service(
        id=10,
        name="srv-10",
        ownerId=1,
        paymentTerm="month",
        autoProlong=False,
        createdAt=datetime(2026, 1, 1, tzinfo=timezone.utc),
        expiresAt=datetime(2026, 2, 1, tzinfo=timezone.utc),
        status="prolong_wait",
        price=1500
    )
    settings = ModelSettings()
    result = evaluate_customer(account, services=[service], transactions=[], settings=settings)

    assert result.risk_score is not None
    assert result.risk_score >= settings.threshold_high
    assert result.risk_level == "high"
    assert result.loyalty_score is not None
    assert result.loyalty_score <= 100.0 - settings.threshold_high
    assert result.potential_monthly_loss_cents > 0


def test_customer_low_risk_active_autoprolong_high_balance():
    """
    Active service with autoprolong enabled and plenty of balance should have low risk.
    """
    account = Account(
        id=2,
        email="loyal@example.test",
        balance=100000,
        withdrawBalance=5000,
        totalReplenished=200000,
        bonusBalance=5000,
        bonusState="unlocked"
    )
    service = Service(
        id=20,
        name="srv-20",
        ownerId=2,
        paymentTerm="month",
        autoProlong=True,
        createdAt=datetime(2026, 1, 1, tzinfo=timezone.utc),
        expiresAt=datetime(2026, 2, 1, tzinfo=timezone.utc),
        status="active",
        price=1000
    )
    settings = ModelSettings()
    result = evaluate_customer(account, services=[service], transactions=[], settings=settings)

    assert result.risk_score is not None
    assert result.risk_score < settings.threshold_medium
    assert result.risk_level == "low"
    assert result.loyalty_score >= 100.0 - settings.threshold_medium


def test_mrr_normalization():
    """
    Checks MRR conversion for hourly, weekly, monthly, yearly services.
    """
    now = datetime.now(timezone.utc)
    s_hour = Service(id=1, name="s1", ownerId=1, paymentTerm="hour", autoProlong=True, createdAt=now, expiresAt=now, status="active", price=10)
    s_month = Service(id=2, name="s2", ownerId=1, paymentTerm="month", autoProlong=True, createdAt=now, expiresAt=now, status="active", price=1000)
    s_year = Service(id=3, name="s3", ownerId=1, paymentTerm="year", autoProlong=True, createdAt=now, expiresAt=now, status="active", price=12000)

    assert calculate_service_mrr(s_hour) == 7200  # 10 * 720
    assert calculate_service_mrr(s_month) == 1000
    assert calculate_service_mrr(s_year) == 1000  # 12000 / 12
