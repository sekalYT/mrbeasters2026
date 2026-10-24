"""
Точка входа веб-приложения FastAPI.
Регистрирует маршрутизаторы API, раздаёт статические файлы и генерирует спецификацию OpenAPI.
"""

import json
from pathlib import Path
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, HTMLResponse, RedirectResponse
from fastapi.middleware.cors import CORSMiddleware
import yaml

from app.api.routes_auth import router as auth_router
from app.api.routes_customers import router as customers_router
from app.api.routes_analytics import router as analytics_router
from app.api.routes_model import router as model_router
from app.api.routes_snapshot import router as snapshot_router
from app.api.routes_metrics import router as metrics_router
from app.api.events import router as events_router
from app.config import BASE_DIR

import app.engine.features


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Экспорт спецификаций OpenAPI при запуске сервиса.
    """
    openapi_schema = app.openapi()
    
    json_path = BASE_DIR / "openapi.json"
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(openapi_schema, f, indent=2, ensure_ascii=False)
    print(f"[INFO] Exported OpenAPI specification to {json_path}")
    
    yaml_path = BASE_DIR / "openapi.yaml"
    with open(yaml_path, "w", encoding="utf-8") as f:
        yaml.dump(openapi_schema, f, allow_unicode=True, sort_keys=False)
    print(f"[INFO] Exported OpenAPI specification to {yaml_path}")
    
    yield


app = FastAPI(
    title="Aéza Churn Risk Analyzer API",
    description=(
        "Аналитическая система прогнозирования рисков оттока клиентов хостинга, "
        "оценки денежных потерь и автоматического ранжирования. "
        "Хакатон РНД · Уровень Middle."
    ),
    version="1.0.0",
    docs_url="/api/v1/docs",
    openapi_url="/api/v1/openapi.json",
    redoc_url=None,
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router)
app.include_router(customers_router)
app.include_router(analytics_router)
app.include_router(model_router)
app.include_router(snapshot_router)
app.include_router(metrics_router)
app.include_router(events_router)

static_dir = Path(__file__).parent / "static"
app.mount("/static", StaticFiles(directory=static_dir), name="static")


@app.get("/docs", include_in_schema=False)
async def redirect_docs():
    """
    Редирект на стандартный Swagger UI эндпоинт по ТЗ (/api/v1/docs).
    """
    return RedirectResponse(url="/api/v1/docs")


@app.get("/", response_class=HTMLResponse, include_in_schema=False)
async def serve_index():
    """
    Отображение главной аналитической панели.
    """
    index_file = static_dir / "index.html"
    return FileResponse(index_file, headers={"Cache-Control": "no-cache, no-store, must-revalidate"})


@app.get("/api/v1/openapi.yaml", include_in_schema=False)
async def get_openapi_yaml():
    """
    Предоставление спецификации OpenAPI в формате YAML.
    """
    yaml_path = BASE_DIR / "openapi.yaml"
    if yaml_path.exists():
        return FileResponse(yaml_path, media_type="application/x-yaml")
    openapi_schema = app.openapi()
    return yaml.dump(openapi_schema, allow_unicode=True, sort_keys=False)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
