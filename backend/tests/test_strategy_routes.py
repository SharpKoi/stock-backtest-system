"""Tests for strategy API routes."""

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select

from app.core.auth import hash_password
from app.core.config import settings
from app.db import get_db
from app.main import app
from app.models.models import User
from app.services.workspace import (
    delete_strategy_file,
    get_strategies_dir,
    initialize_user_workspace_with_examples,
    write_strategy_file,
)

# Test user credentials
TEST_USER_EMAIL = "test_strategy@example.com"
TEST_USER_PASSWORD = "testpassword123"
TEST_USER_ID = None  # Will be set by fixture


@pytest.fixture
async def test_user():
    """Create a test user in the database and initialize workspace."""
    global TEST_USER_ID
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

        TEST_USER_ID = user.id
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
async def setup_test_strategy(test_user):
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
    write_strategy_file(TEST_USER_ID, test_file, test_content)
    yield test_file
    try:
        delete_strategy_file(TEST_USER_ID, test_file)
    except FileNotFoundError:
        pass


@pytest.mark.asyncio
async def test_list_strategy_files(setup_test_strategy, auth_headers):
    """Test listing all strategy files."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/api/strategies/files", headers=auth_headers)
        assert response.status_code == 200
        files = response.json()
        assert isinstance(files, list)
        assert any(f["filename"] == setup_test_strategy for f in files)


@pytest.mark.asyncio
async def test_get_strategy_file(setup_test_strategy, auth_headers):
    """Test retrieving a strategy file."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get(f"/api/strategies/files/{setup_test_strategy}", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["filename"] == setup_test_strategy
        assert "TestAPIStrategy" in data["content"]


@pytest.mark.asyncio
async def test_get_nonexistent_file(auth_headers):
    """Test getting a file that doesn't exist."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/api/strategies/files/nonexistent.py", headers=auth_headers)
        assert response.status_code == 404


@pytest.mark.asyncio
async def test_create_strategy_file(test_user, auth_headers):
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
            headers=auth_headers,
            json={"filename": filename, "content": content}
        )
        assert response.status_code == 200
        assert response.json()["filename"] == filename

    # Cleanup
    try:
        delete_strategy_file(TEST_USER_ID, filename)
    except FileNotFoundError:
        pass


@pytest.mark.asyncio
async def test_create_invalid_filename(auth_headers):
    """Test creating a file with invalid filename."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/api/strategies/files",
            headers=auth_headers,
            json={"filename": "invalid.txt", "content": "test"}
        )
        assert response.status_code == 400


@pytest.mark.asyncio
async def test_update_strategy_file(setup_test_strategy, auth_headers):
    """Test updating an existing strategy file."""
    transport = ASGITransport(app=app)
    new_content = "# Updated content"

    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.put(
            f"/api/strategies/files/{setup_test_strategy}",
            headers=auth_headers,
            json={"filename": setup_test_strategy, "content": new_content}
        )
        assert response.status_code == 200


@pytest.mark.asyncio
async def test_delete_strategy_file(test_user, auth_headers):
    """Test deleting a strategy file."""
    transport = ASGITransport(app=app)
    filename = "delete_test_strategy.py"
    write_strategy_file(TEST_USER_ID, filename, "# Test")

    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.delete(f"/api/strategies/files/{filename}", headers=auth_headers)
        assert response.status_code == 200

    # Verify file is deleted
    files = list(get_strategies_dir(TEST_USER_ID).glob(filename))
    assert len(files) == 0


@pytest.mark.asyncio
async def test_delete_nonexistent_file(auth_headers):
    """Test deleting a file that doesn't exist."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.delete("/api/strategies/files/nonexistent.py", headers=auth_headers)
        assert response.status_code == 404


@pytest.mark.asyncio
async def test_rename_strategy_file(test_user, auth_headers):
    """Test renaming a strategy file."""
    transport = ASGITransport(app=app)
    old_filename = "rename_test_old.py"
    new_filename = "rename_test_new.py"
    content = "# Test content"

    # Create file
    write_strategy_file(TEST_USER_ID, old_filename, content)

    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            f"/api/strategies/files/{old_filename}/rename",
            headers=auth_headers,
            json={"new_filename": new_filename}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["old_filename"] == old_filename
        assert data["new_filename"] == new_filename

    # Verify old file is gone and new file exists
    assert not (get_strategies_dir(TEST_USER_ID) / old_filename).exists()
    assert (get_strategies_dir(TEST_USER_ID) / new_filename).exists()

    # Cleanup
    try:
        delete_strategy_file(TEST_USER_ID, new_filename)
    except FileNotFoundError:
        pass


@pytest.mark.asyncio
async def test_rename_nonexistent_file(auth_headers):
    """Test renaming a file that doesn't exist."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/api/strategies/files/nonexistent.py/rename",
            headers=auth_headers,
            json={"new_filename": "new_name.py"}
        )
        assert response.status_code == 404


@pytest.mark.asyncio
async def test_rename_to_existing_file(test_user, auth_headers):
    """Test renaming to a filename that already exists."""
    transport = ASGITransport(app=app)
    file1 = "rename_existing_1.py"
    file2 = "rename_existing_2.py"

    # Create both files
    write_strategy_file(TEST_USER_ID, file1, "# File 1")
    write_strategy_file(TEST_USER_ID, file2, "# File 2")

    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            f"/api/strategies/files/{file1}/rename",
            headers=auth_headers,
            json={"new_filename": file2}
        )
        assert response.status_code == 409  # Conflict

    # Cleanup
    try:
        delete_strategy_file(TEST_USER_ID, file1)
        delete_strategy_file(TEST_USER_ID, file2)
    except FileNotFoundError:
        pass


@pytest.mark.asyncio
async def test_rename_invalid_extension(test_user, auth_headers):
    """Test renaming to filename without .py extension."""
    transport = ASGITransport(app=app)
    filename = "rename_invalid_ext.py"
    write_strategy_file(TEST_USER_ID, filename, "# Test")

    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            f"/api/strategies/files/{filename}/rename",
            headers=auth_headers,
            json={"new_filename": "test.txt"}
        )
        assert response.status_code == 400

    # Cleanup
    try:
        delete_strategy_file(TEST_USER_ID, filename)
    except FileNotFoundError:
        pass


@pytest.mark.asyncio
async def test_rename_path_traversal(test_user, auth_headers):
    """Test that path traversal is blocked in rename."""
    transport = ASGITransport(app=app)
    filename = "rename_path_test.py"
    write_strategy_file(TEST_USER_ID, filename, "# Test")

    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            f"/api/strategies/files/{filename}/rename",
            headers=auth_headers,
            json={"new_filename": "../evil.py"}
        )
        assert response.status_code == 400

    # Cleanup
    try:
        delete_strategy_file(TEST_USER_ID, filename)
    except FileNotFoundError:
        pass
