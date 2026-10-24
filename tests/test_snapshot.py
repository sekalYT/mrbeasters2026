"""
Tests for PUT /api/v1/source/snapshot and POST /api/v1/source/reset endpoints.
"""

import pytest
from httpx import AsyncClient, ASGITransport
from app.main import app
from app.config import ADMIN_USERNAME, ADMIN_PASSWORD


@pytest.fixture
def anyio_backend():
    return 'asyncio'


@pytest.mark.anyio
async def test_snapshot_upload_and_recalculate():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        login_res = await ac.post("/api/v1/auth/login", json={
            "username": ADMIN_USERNAME,
            "password": ADMIN_PASSWORD
        })
        token = login_res.json()["token"]
        headers = {"Authorization": f"Bearer {token}"}

        # Snapshot with 2 accounts: one with high risk, one with no services (unknown risk)
        new_snapshot = {
            "accounts": [
                {
                    "id": 101,
                    "email": "user-101@test.org",
                    "balance": 0,
                    "withdrawBalance": 0,
                    "totalReplenished": 500,
                    "bonusBalance": 0,
                    "bonusState": "locked"
                },
                {
                    "id": 102,
                    "email": "empty-user-102@test.org",
                    "balance": 5000,
                    "withdrawBalance": 0,
                    "totalReplenished": 5000,
                    "bonusBalance": 0,
                    "bonusState": "unlocked"
                }
            ],
            "services": [
                {
                    "id": 501,
                    "name": "vps-at-risk",
                    "ownerId": 101,
                    "paymentTerm": "month",
                    "autoProlong": False,
                    "createdAt": "2026-01-01T00:00:00Z",
                    "expiresAt": "2026-02-01T00:00:00Z",
                    "status": "prolong_wait",
                    "price": 2000
                }
            ],
            "transactions": [
                {
                    "id": 901,
                    "amount": 200,
                    "status": "not_performed",
                    "performedAt": None,
                    "createdAt": "2026-01-01T00:00:00Z",
                    "type": "order",
                    "serviceId": 501
                }
            ]
        }

        put_res = await ac.put("/api/v1/source/snapshot", json=new_snapshot, headers=headers)
        assert put_res.status_code == 200
        data = put_res.json()
        assert data["accounts_count"] == 2
        assert data["services_count"] == 1
        assert data["high_risk_customers"] == 1

        # Check customers
        c_res = await ac.get("/api/v1/customers", headers=headers)
        assert c_res.status_code == 200
        customers = c_res.json()
        assert len(customers) == 2

        c101 = next(c for c in customers if c["id"] == 101)
        assert c101["risk_level"] == "high"

        c102 = next(c for c in customers if c["id"] == 102)
        assert c102["risk_level"] == "unknown"
        assert c102["risk_score"] is None

        # Test reset endpoint to restore original test dataset
        reset_res = await ac.post("/api/v1/source/reset", headers=headers)
        assert reset_res.status_code == 200
        reset_data = reset_res.json()
        assert reset_data["status"] == "success"
        assert reset_data["accounts_count"] == 11
