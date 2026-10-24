"""
Модели данных и структуры DTO для системы анализа рисков оттока.
"""

from typing import List, Optional, Literal, Dict, Any
from datetime import datetime
from pydantic import BaseModel, Field, EmailStr


PaymentTerm = Literal['hour', 'week', 'month', 'quarter_year', 'half_year', 'year']
ServiceStatus = Literal['active', 'blocked', 'deleted', 'suspended', 'prolong_wait']
TransactionStatus = Literal['not_performed', 'performed']
TransactionType = Literal['prolong', 'order']
BonusState = Literal['locked', 'unlocked']
RiskLevel = Literal['high', 'medium', 'low', 'unknown']


class Account(BaseModel):
    id: int
    email: str
    balance: int = Field(ge=0, description="Основной баланс в евроцентах (€1 = 100)")
    withdrawBalance: int = Field(default=0, ge=0, description="Доступный для вывода реферальный баланс")
    totalReplenished: int = Field(default=0, ge=0, description="Всего пополнено за всё время в евроцентах")
    bonusBalance: int = Field(default=0, ge=0, description="Бонусный баланс в евроцентах")
    bonusState: BonusState = Field(default="locked", description="Возможность тратить бонусный баланс")


class Service(BaseModel):
    id: int
    name: str
    ownerId: int
    paymentTerm: PaymentTerm
    autoProlong: bool = False
    createdAt: datetime
    expiresAt: datetime
    status: ServiceStatus
    price: int = Field(ge=0, description="Стоимость услуги в евроцентах")


class Transaction(BaseModel):
    id: int
    amount: int = Field(ge=0, le=1000, description="Сумма транзакции в евроцентах")
    status: TransactionStatus = "not_performed"
    performedAt: Optional[datetime] = None
    createdAt: datetime
    type: TransactionType
    serviceId: int


class DataSnapshot(BaseModel):
    accounts: List[Account]
    services: List[Service]
    transactions: List[Transaction]


class FeatureExplanation(BaseModel):
    feature_name: str
    weight: float
    raw_score: float
    weighted_score: float
    reason: str


class CustomerRiskScore(BaseModel):
    id: int
    email: str
    balance: int
    balance_eur: float
    withdrawBalance: int
    withdrawBalance_eur: float
    totalReplenished: int
    totalReplenished_eur: float
    bonusBalance: int
    bonusBalance_eur: float
    bonusState: BonusState
    
    risk_score: Optional[float] = Field(
        None, description="Оценка риска от 0.0 до 100.0 (null если данных недостаточно)"
    )
    risk_level: RiskLevel = Field(
        description="Уровень риска: high, medium, low или unknown при недостатке данных"
    )
    loyalty_score: Optional[float] = Field(
        None, description="Обратная шкала лояльности (100 - risk_score)"
    )
    reasons: List[str] = Field(default_factory=list, description="Понятные причины оценки риска")
    explanations: List[FeatureExplanation] = Field(default_factory=list)
    
    services_count: int = 0
    active_services_count: int = 0
    services_at_risk_count: int = 0
    total_mrr_cents: int = 0
    total_mrr_eur: float = 0.0
    potential_monthly_loss_cents: int = 0
    potential_monthly_loss_eur: float = 0.0
    upcoming_renewal_cost_cents: int = 0
    upcoming_renewal_cost_eur: float = 0.0
    balance_deficit_cents: int = 0
    balance_deficit_eur: float = 0.0


class CustomerDetail(CustomerRiskScore):
    services: List[Service] = Field(default_factory=list)
    transactions: List[Transaction] = Field(default_factory=list)


class ModelSettings(BaseModel):
    w_auto_prolong_off: float = Field(default=35.0, ge=0.0, le=100.0, description="Вес отключенного автопродления")
    w_insufficient_funds: float = Field(default=30.0, ge=0.0, le=100.0, description="Вес нехватки средств для продления")
    w_prolong_wait: float = Field(default=25.0, ge=0.0, le=100.0, description="Вес услуги в статусе prolong_wait")
    w_failed_tx_ratio: float = Field(default=10.0, ge=0.0, le=100.0, description="Вес доли неуспешных транзакций")
    
    threshold_high: float = Field(default=70.0, ge=0.0, le=100.0, description="Порог высокого риска")
    threshold_medium: float = Field(default=35.0, ge=0.0, le=100.0, description="Порог среднего риска")
    
    forecast_days: int = Field(default=30, ge=1, le=365, description="Горизонт прогноза в днях")
    loss_calculation_mode: Literal['mrr_risk_weighted', 'direct_deficit', 'hybrid'] = Field(
        default='hybrid', description="Методология расчёта денежных потерь"
    )


class ModelSettingsUpdate(BaseModel):
    w_auto_prolong_off: Optional[float] = Field(default=None, ge=0.0, le=100.0)
    w_insufficient_funds: Optional[float] = Field(default=None, ge=0.0, le=100.0)
    w_prolong_wait: Optional[float] = Field(default=None, ge=0.0, le=100.0)
    w_failed_tx_ratio: Optional[float] = Field(default=None, ge=0.0, le=100.0)
    threshold_high: Optional[float] = Field(default=None, ge=0.0, le=100.0)
    threshold_medium: Optional[float] = Field(default=None, ge=0.0, le=100.0)
    forecast_days: Optional[int] = Field(default=None, ge=1, le=365)
    loss_calculation_mode: Optional[Literal['mrr_risk_weighted', 'direct_deficit', 'hybrid']] = None


class ChurnForecastPoint(BaseModel):
    label: str
    fact_deleted_services: int
    forecast_at_risk_services: int
    forecast_lost_revenue_eur: float


class AnalyticsSummary(BaseModel):
    total_customers: int
    high_risk_customers: int
    medium_risk_customers: int
    low_risk_customers: int
    unknown_risk_customers: int
    
    total_services: int
    services_at_risk: int
    
    total_potential_loss_cents: int
    total_potential_loss_eur: float
    total_mrr_at_risk_eur: float
    total_balance_deficit_eur: float
    
    average_risk_score: Optional[float]
    loss_calculation_explanation: str
    forecast_chart_data: List[ChurnForecastPoint] = Field(default_factory=list)


class UserCredentials(BaseModel):
    username: str
    password: str


class UserInfo(BaseModel):
    username: str
    role: str
    auth_type: str = "password"


class AuthResponse(BaseModel):
    token: str
    token_type: str = "bearer"
    user: UserInfo
