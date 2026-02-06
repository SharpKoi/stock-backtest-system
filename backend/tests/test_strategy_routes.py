"""Tests for strategy API routes."""

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app
from app.services.workspace import (
    delete_strategy_file,
    get_strategies_dir,
    write_strategy_file,
)


@pytest.fixture
def setup_test_strategy():
    """Create a test strategy file and clean up after."""
    test_file = "test_api_strategy.py"
    test_content = '''
from vici_trade_sdk import Strategy, Portfolio
import pandas as pd

class TestAPIStrategy(Strategy):
    @property
    def name(self) -> str:
        return "Test API Strategy"

    def on_bar(self, date: str, data: dict[str, pd.Series], portfolio: Portfolio) -> None:
        pass
'''
    write_strategy_file(test_file, test_content)
    yield test_file
    try:
        delete_strategy_file(test_file)
    except FileNotFoundError:
        pass


@pytest.mark.asyncio
async def test_list_strategy_files(setup_test_strategy):
    """Test listing all strategy files."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/api/strategies/files")
        assert response.status_code == 200
        files = response.json()
        assert isinstance(files, list)
        assert any(f["filename"] == setup_test_strategy for f in files)


@pytest.mark.asyncio
async def test_get_strategy_file(setup_test_strategy):
    """Test retrieving a strategy file."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get(f"/api/strategies/files/{setup_test_strategy}")
        assert response.status_code == 200
        data = response.json()
        assert data["filename"] == setup_test_strategy
        assert "TestAPIStrategy" in data["content"]


@pytest.mark.asyncio
async def test_get_nonexistent_file():
    """Test getting a file that doesn't exist."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/api/strategies/files/nonexistent.py")
        assert response.status_code == 404


@pytest.mark.asyncio
async def test_create_strategy_file():
    """Test creating a new strategy file."""
    transport = ASGITransport(app=app)
    filename = "new_test_strategy.py"
    content = '''
from vici_trade_sdk import Strategy, Portfolio
import pandas as pd

class NewTestStrategy(Strategy):
    @property
    def name(self) -> str:
        return "New Test"

    def on_bar(self, date: str, data: dict[str, pd.Series], portfolio: Portfolio) -> None:
        pass
'''

    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/api/strategies/files",
            json={"filename": filename, "content": content}
        )
        assert response.status_code == 200
        assert response.json()["filename"] == filename

    # Cleanup
    try:
        delete_strategy_file(filename)
    except FileNotFoundError:
        pass


@pytest.mark.asyncio
async def test_create_invalid_filename():
    """Test creating a file with invalid filename."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/api/strategies/files",
            json={"filename": "invalid.txt", "content": "test"}
        )
        assert response.status_code == 400


@pytest.mark.asyncio
async def test_update_strategy_file(setup_test_strategy):
    """Test updating an existing strategy file."""
    transport = ASGITransport(app=app)
    new_content = "# Updated content"

    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.put(
            f"/api/strategies/files/{setup_test_strategy}",
            json={"filename": setup_test_strategy, "content": new_content}
        )
        assert response.status_code == 200


@pytest.mark.asyncio
async def test_delete_strategy_file():
    """Test deleting a strategy file."""
    transport = ASGITransport(app=app)
    filename = "delete_test_strategy.py"
    write_strategy_file(filename, "# Test")

    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.delete(f"/api/strategies/files/{filename}")
        assert response.status_code == 200

    # Verify file is deleted
    files = list(get_strategies_dir().glob(filename))
    assert len(files) == 0


@pytest.mark.asyncio
async def test_delete_nonexistent_file():
    """Test deleting a file that doesn't exist."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.delete("/api/strategies/files/nonexistent.py")
        assert response.status_code == 404
