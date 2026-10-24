"""
Параметры конфигурации сервиса анализа рисков оттока.
"""

import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

DATA_DIR = Path(os.getenv("DATA_DIR", str(BASE_DIR / "data")))
DATA_DIR.mkdir(parents=True, exist_ok=True)

DEFAULT_DATA_FILE = DATA_DIR / "data.json"
SETTINGS_FILE = DATA_DIR / "model_settings.json"
SNAPSHOT_BACKUP_FILE = DATA_DIR / "current_snapshot.json"

SECRET_KEY = os.getenv("SECRET_KEY", "aeza-hackathon-rnd-super-secret-key-2026")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24

ADMIN_USERNAME = os.getenv("ADMIN_USERNAME", "admin")
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "aeza2026")

OIDC_ENABLED = os.getenv("OIDC_ENABLED", "true").lower() in ("true", "1", "yes")
OIDC_ISSUER = os.getenv("OIDC_ISSUER", "https://id.aeza.net")
OIDC_CLIENT_ID = os.getenv("OIDC_CLIENT_ID", "churn-risk-analyzer")
