"""Tests for FastAPI API endpoints."""

import pytest
from httpx import AsyncClient, ASGITransport
from sqlalchemy import select

from app.core.auth import hash_password
from app.core.config import settings
from app.db import get_db
from app.main import app
from app.models.models import User
from app.services.workspace import initialize_user_workspace_with_examples


# Test user credentials
TEST_USER_EMAIL = "test@example.com"
TEST_USER_PASSWORD = "testpassword123"


@pytest.fixture
async def test_user():
    """Create a test user in the database and initialize workspace."""
    async for db in get_db():
        # Check if test user already exists
        result = await db.execute(select(User).where(User.email == TEST_USER_EMAIL))
        existing_user = result.scalar_one_or_none()

        if existing_user:
            user = existing_user
        else:
            # Create test user
            hashed_password = hash_password(TEST_USER_PASSWORD)
            user = User(email=TEST_USER_EMAIL, hashed_password=hashed_password)
            db.add(user)
            await db.commit()
            await db.refresh(user)

            # Initialize workspace with examples
            builtin_strategies_dir = settings.strategies_dir
            initialize_user_workspace_with_examples(user.id, builtin_strategies_dir)

        yield user
        break


@pytest.fixture
async def auth_headers(test_user):
    """Get authentication headers with JWT token."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Login to get token
        response = await client.post(
            "/api/auth/login",
            json={"email": TEST_USER_EMAIL, "password": TEST_USER_PASSWORD}
        )
        assert response.status_code == 200
        token = response.json()["access_token"]

        return {"Authorization": f"Bearer {token}"}


@pytest.fixture
async def client():
    """Create an async test client for the FastAPI app."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


class TestHealthCheck:
    @pytest.mark.asyncio
    async def test_health(self, client):
        response = await client.get("/api/health")
        assert response.status_code == 200
        assert response.json() == {"status": "ok"}


class TestDataEndpoints:
    @pytest.mark.asyncio
    async def test_list_stocks_empty(self, client, auth_headers):
        response = await client.get("/api/data/stocks", headers=auth_headers)
        assert response.status_code == 200
        assert isinstance(response.json(), list)

    @pytest.mark.asyncio
    async def test_get_nonexistent_stock(self, client, auth_headers):
        response = await client.get("/api/data/stocks/NONEXISTENT", headers=auth_headers)
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_get_nonexistent_ohlcv(self, client, auth_headers):
        response = await client.get("/api/data/stocks/NONEXISTENT/ohlcv", headers=auth_headers)
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_get_nonexistent_date_range(self, client, auth_headers):
        response = await client.get("/api/data/stocks/NONEXISTENT/date-range", headers=auth_headers)
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_delete_nonexistent_stock(self, client, auth_headers):
        response = await client.delete("/api/data/stocks/NONEXISTENT", headers=auth_headers)
        assert response.status_code == 404


class TestStrategyEndpoints:
    @pytest.mark.asyncio
    async def test_list_strategies(self, client, test_user, auth_headers):
        response = await client.get("/api/strategies", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        class_names = [s["class_name"] for s in data]
        assert "SMACrossover" in class_names
        assert "RSIMeanReversion" in class_names

    @pytest.mark.asyncio
    async def test_strategy_has_metadata(self, client, test_user, auth_headers):
        response = await client.get("/api/strategies", headers=auth_headers)
        data = response.json()
        for strategy in data:
            assert "class_name" in strategy
            assert "name" in strategy
            assert "indicators" in strategy


class TestBacktestEndpoints:
    @pytest.mark.asyncio
    async def test_list_backtests_empty(self, client, auth_headers):
        response = await client.get("/api/backtests", headers=auth_headers)
        assert response.status_code == 200
        assert isinstance(response.json(), list)

    @pytest.mark.asyncio
    async def test_get_nonexistent_backtest(self, client, auth_headers):
        response = await client.get("/api/backtests/99999", headers=auth_headers)
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_delete_nonexistent_backtest(self, client, auth_headers):
        response = await client.delete("/api/backtests/99999", headers=auth_headers)
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_run_backtest_missing_strategy(self, client, test_user, auth_headers):
        response = await client.post("/api/backtests", headers=auth_headers, json={
            "name": "Test",
            "strategy_name": "NonexistentStrategy",
            "symbols": ["AAPL"],
            "start_date": "2024-01-01",
            "end_date": "2024-12-31",
            "initial_capital": 100000,
            "commission_rate": 0.001,
            "strategy_params": {},
        })
        assert response.status_code == 400

    @pytest.mark.asyncio
    async def test_run_backtest_validation(self, client, auth_headers):
        """Test that request validation catches invalid data."""
        response = await client.post("/api/backtests", headers=auth_headers, json={
            "name": "Test",
            "strategy_name": "SMACrossover",
            "symbols": ["AAPL"],
            "start_date": "2024-01-01",
            "end_date": "2024-12-31",
            "initial_capital": -1000,  # Invalid
            "commission_rate": 0.001,
            "strategy_params": {},
        })
        assert response.status_code == 422  # Validation error
