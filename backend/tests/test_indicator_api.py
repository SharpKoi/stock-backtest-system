"""Tests for indicator API endpoints."""

import shutil

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app
from app.services.workspace import get_indicators_dir, write_indicator_file


@pytest.fixture
def clean_indicators_workspace():
    """Clean up indicator workspace before and after tests."""
    indicators_dir = get_indicators_dir()
    if indicators_dir.exists():
        shutil.rmtree(indicators_dir)
    yield
    if indicators_dir.exists():
        shutil.rmtree(indicators_dir)


@pytest.fixture
async def client():
    """Create an async HTTP client for testing."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


async def test_list_indicator_files(client: AsyncClient, clean_indicators_workspace):
    """Test listing indicator files."""
    write_indicator_file("test1.py", "# indicator 1")
    write_indicator_file("test2.py", "# indicator 2")

    response = await client.get("/api/indicators/files")
    assert response.status_code == 200

    files = response.json()
    filenames = [f["filename"] for f in files]

    assert "test1.py" in filenames
    assert "test2.py" in filenames


async def test_get_indicator_file(client: AsyncClient, clean_indicators_workspace):
    """Test getting a specific indicator file."""
    content = "from vici_trade_sdk import Indicator\n\nclass Test(Indicator):\n    pass"
    write_indicator_file("test.py", content)

    response = await client.get("/api/indicators/files/test.py")
    assert response.status_code == 200

    data = response.json()
    assert data["filename"] == "test.py"
    assert data["content"] == content


async def test_get_nonexistent_file(client: AsyncClient, clean_indicators_workspace):
    """Test getting a file that doesn't exist returns 404."""
    response = await client.get("/api/indicators/files/nonexistent.py")
    assert response.status_code == 404


async def test_create_indicator_file(client: AsyncClient, clean_indicators_workspace):
    """Test creating a new indicator file."""
    content = "from vici_trade_sdk import Indicator"
    payload = {"filename": "new.py", "content": content}

    response = await client.post("/api/indicators/files", json=payload)
    assert response.status_code == 200

    data = response.json()
    assert data["filename"] == "new.py"
    assert "saved successfully" in data["message"].lower()

    # Verify file was created
    indicators_dir = get_indicators_dir()
    assert (indicators_dir / "new.py").exists()


async def test_create_invalid_filename(client: AsyncClient, clean_indicators_workspace):
    """Test creating a file with invalid extension returns 400."""
    payload = {"filename": "invalid.txt", "content": "# content"}

    response = await client.post("/api/indicators/files", json=payload)
    assert response.status_code == 400


async def test_update_indicator_file(client: AsyncClient, clean_indicators_workspace):
    """Test updating an existing indicator file."""
    write_indicator_file("update.py", "# old content")

    new_content = "# new content"
    payload = {"filename": "update.py", "content": new_content}

    response = await client.put("/api/indicators/files/update.py", json=payload)
    assert response.status_code == 200

    # Verify file was updated
    indicators_dir = get_indicators_dir()
    assert (indicators_dir / "update.py").read_text() == new_content


async def test_delete_indicator_file(client: AsyncClient, clean_indicators_workspace):
    """Test deleting an indicator file."""
    write_indicator_file("delete.py", "# content")
    indicators_dir = get_indicators_dir()
    assert (indicators_dir / "delete.py").exists()

    response = await client.delete("/api/indicators/files/delete.py")
    assert response.status_code == 200

    # Verify file was deleted
    assert not (indicators_dir / "delete.py").exists()


async def test_delete_nonexistent_file(client: AsyncClient, clean_indicators_workspace):
    """Test deleting a non-existent file returns 404."""
    response = await client.delete("/api/indicators/files/nonexistent.py")
    assert response.status_code == 404


async def test_rename_indicator_file(client: AsyncClient, clean_indicators_workspace):
    """Test renaming an indicator file."""
    write_indicator_file("old.py", "# content")

    payload = {"new_filename": "new.py"}
    response = await client.post("/api/indicators/files/old.py/rename", json=payload)
    assert response.status_code == 200

    data = response.json()
    assert data["old_filename"] == "old.py"
    assert data["new_filename"] == "new.py"

    # Verify rename
    indicators_dir = get_indicators_dir()
    assert not (indicators_dir / "old.py").exists()
    assert (indicators_dir / "new.py").exists()


async def test_rename_nonexistent_file(client: AsyncClient, clean_indicators_workspace):
    """Test renaming a non-existent file returns 404."""
    payload = {"new_filename": "new.py"}
    response = await client.post("/api/indicators/files/nonexistent.py/rename", json=payload)
    assert response.status_code == 404


async def test_rename_to_existing_file(client: AsyncClient, clean_indicators_workspace):
    """Test renaming to an existing filename returns 409."""
    write_indicator_file("old.py", "# old")
    write_indicator_file("new.py", "# new")

    payload = {"new_filename": "new.py"}
    response = await client.post("/api/indicators/files/old.py/rename", json=payload)
    assert response.status_code == 409


async def test_rename_invalid_extension(client: AsyncClient, clean_indicators_workspace):
    """Test renaming to invalid extension returns 400."""
    write_indicator_file("test.py", "# content")

    payload = {"new_filename": "test.txt"}
    response = await client.post("/api/indicators/files/test.py/rename", json=payload)
    assert response.status_code == 400


async def test_rename_path_traversal(client: AsyncClient, clean_indicators_workspace):
    """Test that path traversal in rename is blocked."""
    write_indicator_file("test.py", "# content")

    payload = {"new_filename": "../evil.py"}
    response = await client.post("/api/indicators/files/test.py/rename", json=payload)
    assert response.status_code == 400


async def test_list_indicators_includes_builtin(client: AsyncClient):
    """Test that listing indicators includes built-in indicators."""
    response = await client.get("/api/indicators")
    assert response.status_code == 200

    indicators = response.json()
    indicator_names = [ind["name"] for ind in indicators]

    # Check for some built-in indicators
    assert "sma" in indicator_names
    assert "ema" in indicator_names
    assert "rsi" in indicator_names


async def test_list_indicators_includes_custom(client: AsyncClient, clean_indicators_workspace):
    """Test that listing indicators includes custom indicators."""
    # Create a custom indicator
    indicator_code = """from vici_trade_sdk import Indicator
import pandas as pd

class TestIndicator(Indicator):
    @property
    def name(self) -> str:
        return "test_custom"

    def compute(self, df: pd.DataFrame) -> pd.Series:
        return df["close"]
"""
    write_indicator_file("test.py", indicator_code)

    # Reload indicators
    await client.post("/api/indicators/reload")

    response = await client.get("/api/indicators")
    assert response.status_code == 200

    indicators = response.json()
    custom_indicators = [ind for ind in indicators if ind.get("type") == "custom"]

    assert len(custom_indicators) >= 1
    assert any(ind["name"] == "test_custom" for ind in custom_indicators)


async def test_reload_indicators(client: AsyncClient, clean_indicators_workspace):
    """Test reloading indicators from workspace."""
    # Create a new indicator
    indicator_code = """from vici_trade_sdk import Indicator
import pandas as pd

class NewIndicator(Indicator):
    @property
    def name(self) -> str:
        return "new_indicator"

    def compute(self, df: pd.DataFrame) -> pd.Series:
        return df["close"]
"""
    write_indicator_file("new.py", indicator_code)

    response = await client.post("/api/indicators/reload")
    assert response.status_code == 200

    data = response.json()
    assert "count" in data
    assert data["count"] >= 1
