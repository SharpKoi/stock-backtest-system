"""Tests for FastAPI API endpoints."""

import pytest
from fastapi.testclient import TestClient

from app.core.config import STRATEGIES_DIR
from app.main import app
from app.services.workspace import initialize_workspace_with_examples


@pytest.fixture(scope="session", autouse=True)
def setup_workspace():
    """Initialize workspace with example strategies for all tests."""
    initialize_workspace_with_examples(STRATEGIES_DIR)


@pytest.fixture
def client():
    """Create a test client for the FastAPI app."""
    return TestClient(app)


class TestHealthCheck:
    def test_health(self, client: TestClient):
        response = client.get("/api/health")
        assert response.status_code == 200
        assert response.json() == {"status": "ok"}


class TestDataEndpoints:
    def test_list_stocks_empty(self, client: TestClient):
        response = client.get("/api/data/stocks")
        assert response.status_code == 200
        assert isinstance(response.json(), list)

    def test_get_nonexistent_stock(self, client: TestClient):
        response = client.get("/api/data/stocks/NONEXISTENT")
        assert response.status_code == 404

    def test_get_nonexistent_ohlcv(self, client: TestClient):
        response = client.get("/api/data/stocks/NONEXISTENT/ohlcv")
        assert response.status_code == 404

    def test_get_nonexistent_date_range(self, client: TestClient):
        response = client.get("/api/data/stocks/NONEXISTENT/date-range")
        assert response.status_code == 404

    def test_delete_nonexistent_stock(self, client: TestClient):
        response = client.delete("/api/data/stocks/NONEXISTENT")
        assert response.status_code == 404


class TestStrategyEndpoints:
    def test_list_strategies(self, client: TestClient):
        response = client.get("/api/strategies")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        class_names = [s["class_name"] for s in data]
        assert "SMACrossover" in class_names
        assert "RSIMeanReversion" in class_names

    def test_strategy_has_metadata(self, client: TestClient):
        response = client.get("/api/strategies")
        data = response.json()
        for strategy in data:
            assert "class_name" in strategy
            assert "name" in strategy
            assert "indicators" in strategy


class TestBacktestEndpoints:
    def test_list_backtests_empty(self, client: TestClient):
        response = client.get("/api/backtests")
        assert response.status_code == 200
        assert isinstance(response.json(), list)

    def test_get_nonexistent_backtest(self, client: TestClient):
        response = client.get("/api/backtests/99999")
        assert response.status_code == 404

    def test_delete_nonexistent_backtest(self, client: TestClient):
        response = client.delete("/api/backtests/99999")
        assert response.status_code == 404

    def test_run_backtest_missing_strategy(self, client: TestClient):
        response = client.post("/api/backtests", json={
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

    def test_run_backtest_validation(self, client: TestClient):
        """Test that request validation catches invalid data."""
        response = client.post("/api/backtests", json={
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
