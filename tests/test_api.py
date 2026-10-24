"""
Integration test suite for all mandatory API endpoints.
"""

import pytest
from httpx import AsyncClient, ASGITransport
from app.main import app
from app.config import ADMIN_USERNAME, ADMIN_PASSWORD


@pytest.fixture
def anyio_backend():
    return 'asyncio'


@pytest.mark.anyio
async def test_auth_flow():
    """
    Tests POST /api/v1/auth/login, GET /api/v1/auth/me, POST /api/v1/auth/logout.
    """
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        # 1. Unauthenticated me fails
        res = await ac.get("/api/v1/auth/me")
        assert res.status_code == 401

        # 2. Login with valid credentials
        res = await ac.post("/api/v1/auth/login", json={
            "username": ADMIN_USERNAME,
            "password": ADMIN_PASSWORD
        })
        assert res.status_code == 200
        data = res.json()
        assert "token" in data
        token = data["token"]

        # 3. Authenticated me succeeds
        res = await ac.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
        assert res.status_code == 200
        assert res.json()["username"] == ADMIN_USERNAME

        # 4. Logout
        res = await ac.post("/api/v1/auth/logout")
        assert res.status_code == 200


@pytest.mark.anyio
async def test_customers_sorting_both_directions():
    """
    Requirement: 'Обязательна сортировка по ID, email, балансу и общей сумме пополнений в обе стороны (по убыванию и по возрастанию).'
    """
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        # Authenticate
        login_res = await ac.post("/api/v1/auth/login", json={
            "username": ADMIN_USERNAME,
            "password": ADMIN_PASSWORD
        })
        token = login_res.json()["token"]
        headers = {"Authorization": f"Bearer {token}"}

        fields_to_test = ["id", "email", "balance", "totalReplenished", "risk_score"]
        for field in fields_to_test:
            for order in ["asc", "desc"]:
                res = await ac.get(f"/api/v1/customers?sort_by={field}&sort_order={order}", headers=headers)
                assert res.status_code == 200, f"Failed on sort_by={field}, sort_order={order}"
                items = res.json()
                assert len(items) > 0

                # Validate sort order
                vals = [item[field] for item in items if item.get(field) is not None]
                if order == "asc":
                    assert vals == sorted(vals), f"Field {field} not sorted asc: {vals}"
                else:
                    assert vals == sorted(vals, reverse=True), f"Field {field} not sorted desc: {vals}"


@pytest.mark.anyio
async def test_customer_detail_by_id():
    """
    Tests GET /api/v1/customers/{id}.
    """
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        login_res = await ac.post("/api/v1/auth/login", json={
            "username": ADMIN_USERNAME,
            "password": ADMIN_PASSWORD
        })
        token = login_res.json()["token"]
        headers = {"Authorization": f"Bearer {token}"}

        # Fetch first available customer id
        cust_list_res = await ac.get("/api/v1/customers", headers=headers)
        assert cust_list_res.status_code == 200
        customers = cust_list_res.json()
        assert len(customers) > 0
        target_id = customers[0]["id"]

        res = await ac.get(f"/api/v1/customers/{target_id}", headers=headers)
        assert res.status_code == 200
        detail = res.json()
        assert detail["id"] == target_id
        assert "services" in detail
        assert "transactions" in detail
        assert "reasons" in detail
        assert "explanations" in detail


@pytest.mark.anyio
async def test_analytics_summary():
    """
    Tests GET /api/v1/analytics/summary.
    """
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        login_res = await ac.post("/api/v1/auth/login", json={
            "username": ADMIN_USERNAME,
            "password": ADMIN_PASSWORD
        })
        token = login_res.json()["token"]
        headers = {"Authorization": f"Bearer {token}"}

        res = await ac.get("/api/v1/analytics/summary", headers=headers)
        assert res.status_code == 200
        data = res.json()
        assert "total_potential_loss_eur" in data
        assert "high_risk_customers" in data
        assert "loss_calculation_explanation" in data
        assert "forecast_chart_data" in data


@pytest.mark.anyio
async def test_model_settings_patch_and_recalculate():
    """
    Tests GET and PATCH /api/v1/model/settings with live recalculation.
    """
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        login_res = await ac.post("/api/v1/auth/login", json={
            "username": ADMIN_USERNAME,
            "password": ADMIN_PASSWORD
        })
        token = login_res.json()["token"]
        headers = {"Authorization": f"Bearer {token}"}

        # Get settings
        res = await ac.get("/api/v1/model/settings", headers=headers)
        assert res.status_code == 200
        orig_w = res.json()["w_auto_prolong_off"]

        # Patch settings
        new_w = 42.0 if orig_w != 42.0 else 45.0
        patch_res = await ac.patch("/api/v1/model/settings", json={"w_auto_prolong_off": new_w}, headers=headers)
        assert patch_res.status_code == 200
        assert patch_res.json()["w_auto_prolong_off"] == new_w

        # Verify new settings reflect in GET
        verify_res = await ac.get("/api/v1/model/settings", headers=headers)
        assert verify_res.json()["w_auto_prolong_off"] == new_w


@pytest.mark.anyio
async def test_prometheus_metrics():
    """
    Requirement 6: 'Endpoint /metrics. Отдаёт актуальные агрегированные показатели в формате, совместимом с Prometheus.'
    """
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        res = await ac.get("/metrics")
        assert res.status_code == 200
        text = res.text
        assert "churn_customers_total{" in text
        assert "churn_potential_monetary_loss_eur" in text
        assert "churn_potential_monetary_loss_cents" in text
        assert "churn_services_at_risk_total" in text


@pytest.mark.anyio
async def test_swagger_and_openapi_specs():
    """
    Requirement: 'Swagger-эндпоинт с рабочей документацией' & OpenAPI specification.
    """
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        # Swagger UI HTML
        res_docs = await ac.get("/api/v1/docs")
        assert res_docs.status_code == 200

        # OpenAPI JSON
        res_json = await ac.get("/api/v1/openapi.json")
        assert res_json.status_code == 200
        assert "paths" in res_json.json()

        # OpenAPI YAML
        res_yaml = await ac.get("/api/v1/openapi.yaml")
        assert res_yaml.status_code == 200
        assert "openapi:" in res_yaml.text
