"""
Репозиторий состояния и данных в оперативной памяти.
Обеспечивает сохранение снимков данных, персистентность настроек модели
и автоматический пересчет показателей.
"""

import json
import threading
from pathlib import Path
from typing import List, Optional, Tuple, Dict, Any

from app.config import DEFAULT_DATA_FILE, SETTINGS_FILE, SNAPSHOT_BACKUP_FILE
from app.models import (
    Account, Service, Transaction, DataSnapshot,
    ModelSettings, CustomerDetail, AnalyticsSummary
)
from app.engine.evaluator import evaluate_all


class StateRepository:
    """
    Потокобезопасное хранилище состояния аналитической модели.
    """
    def __init__(self):
        self._lock = threading.Lock()
        self.settings: ModelSettings = self._load_settings()
        self.accounts: List[Account] = []
        self.services: List[Service] = []
        self.transactions: List[Transaction] = []
        self.customer_details: List[CustomerDetail] = []
        self.summary: Optional[AnalyticsSummary] = None
        self.recalculation_counter: int = 0
        
        self._load_initial_snapshot()
        self.recalculate()

    def _load_settings(self) -> ModelSettings:
        """
        Загрузка сохраненных параметров модели из файла JSON.
        """
        if SETTINGS_FILE.exists():
            try:
                with open(SETTINGS_FILE, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    return ModelSettings(**data)
            except Exception as e:
                print(f"[WARN] Failed to load settings from {SETTINGS_FILE}: {e}")
        return ModelSettings()

    def save_settings(self, new_settings: ModelSettings):
        """
        Сохранение новых коэффициентов модели на диск с вызовом пересчета.
        """
        with self._lock:
            self.settings = new_settings
            try:
                with open(SETTINGS_FILE, "w", encoding="utf-8") as f:
                    json.dump(new_settings.model_dump(), f, indent=2, ensure_ascii=False)
            except Exception as e:
                print(f"[ERROR] Failed to save settings to {SETTINGS_FILE}: {e}")
        self.recalculate()

    def _load_initial_snapshot(self):
        """
        Загрузка исходного снимка данных при старте сервиса.
        """
        source_path = SNAPSHOT_BACKUP_FILE if SNAPSHOT_BACKUP_FILE.exists() else DEFAULT_DATA_FILE
        if source_path.exists():
            try:
                with open(source_path, "r", encoding="utf-8") as f:
                    raw = json.load(f)
                    snapshot = DataSnapshot(**raw)
                    self.accounts = snapshot.accounts
                    self.services = snapshot.services
                    self.transactions = snapshot.transactions
                    print(f"[INFO] Loaded snapshot from {source_path}: {len(self.accounts)} accounts, {len(self.services)} services, {len(self.transactions)} transactions")
                    return
            except Exception as e:
                print(f"[WARN] Failed to load data from {source_path}: {e}")
        self.accounts = []
        self.services = []
        self.transactions = []

    def set_snapshot(self, snapshot: DataSnapshot):
        """
        Замена снимка данных новыми значениями с сохранением резервной копии.
        """
        with self._lock:
            self.accounts = snapshot.accounts
            self.services = snapshot.services
            self.transactions = snapshot.transactions
            try:
                with open(SNAPSHOT_BACKUP_FILE, "w", encoding="utf-8") as f:
                    json.dump(snapshot.model_dump(mode="json"), f, indent=2, ensure_ascii=False)
            except Exception as e:
                print(f"[ERROR] Failed to persist snapshot backup: {e}")
        self.recalculate()

    def recalculate(self):
        """
        Полный пересчет скоринга и аналитических показателей.
        """
        with self._lock:
            details, summary = evaluate_all(
                self.accounts,
                self.services,
                self.transactions,
                self.settings
            )
            self.customer_details = details
            self.summary = summary
            self.recalculation_counter += 1

    def get_customers(
        self,
        risk_level: Optional[str] = None,
        sort_by: str = "risk_score",
        sort_order: str = "desc",
        search: Optional[str] = None
    ) -> List[CustomerDetail]:
        """
        Получение списка клиентов с фильтрацией, поиском и сортировкой.
        """
        with self._lock:
            results = list(self.customer_details)

        if risk_level and risk_level != "all":
            results = [c for c in results if c.risk_level == risk_level]

        if search:
            q = search.lower().strip()
            results = [
                c for c in results
                if q in c.email.lower() or q in str(c.id)
            ]

        reverse = (sort_order.lower() == "desc")
        
        def sort_key(item: CustomerDetail):
            val = getattr(item, sort_by, None)
            if val is None:
                return -1e9 if reverse else 1e9
            return val

        if hasattr(CustomerDetail, sort_by) or sort_by in [
            "id", "email", "balance", "totalReplenished", "risk_score", "loyalty_score", "potential_monthly_loss_cents"
        ]:
            results.sort(key=sort_key, reverse=reverse)

        return results

    def get_customer_by_id(self, customer_id: int) -> Optional[CustomerDetail]:
        """
        Получение подробных данных клиента по его идентификатору.
        """
        with self._lock:
            for c in self.customer_details:
                if c.id == customer_id:
                    return c
        return None

    def get_summary(self) -> AnalyticsSummary:
        """
        Получение сводных аналитических показателей.
        """
        with self._lock:
            return self.summary or evaluate_all([], [], [], self.settings)[1]

    def get_settings(self) -> ModelSettings:
        """
        Получение действующих параметров модели.
        """
        with self._lock:
            return self.settings


repo = StateRepository()
