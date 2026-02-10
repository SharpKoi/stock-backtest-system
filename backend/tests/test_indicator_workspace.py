"""Tests for indicator workspace directory management."""


import pytest

from app.services.workspace import (
    delete_indicator_file,
    get_indicator_file_path,
    get_indicators_dir,
    get_user_workspace_dir,
    list_indicator_files,
    read_indicator_file,
    rename_indicator_file,
    write_indicator_file,
)

# Test user ID for isolated testing
TEST_USER_ID = 999


@pytest.fixture
def temp_workspace(monkeypatch, tmp_path):
    """Create a temporary workspace for testing."""
    monkeypatch.setenv("HOME", str(tmp_path))
    yield tmp_path / ".vici-backtest"


def test_get_workspace_dir(temp_workspace):
    """Test getting the workspace directory path."""
    workspace = get_user_workspace_dir(TEST_USER_ID)
    assert workspace == temp_workspace / "users" / str(TEST_USER_ID)


def test_get_indicators_dir(temp_workspace):
    """Test getting the indicators directory path."""
    indicators_dir = get_indicators_dir(TEST_USER_ID)
    assert indicators_dir == temp_workspace / "users" / str(TEST_USER_ID) / "indicators"


def test_write_indicator_file(temp_workspace):
    """Test writing an indicator file creates the file with correct content."""
    content = "from vici_trade_sdk import Indicator\n\nclass TestIndicator(Indicator):\n    pass"
    file_path = write_indicator_file(TEST_USER_ID, "test.py", content)

    assert file_path.exists()
    assert file_path.read_text(encoding="utf-8") == content


def test_write_indicator_file_creates_workspace(temp_workspace):
    """Test that write_indicator_file creates the workspace directory if missing."""
    indicators_dir = get_indicators_dir(TEST_USER_ID)
    assert not indicators_dir.exists()

    write_indicator_file(TEST_USER_ID, "test.py", "# content")
    assert indicators_dir.exists()


def test_write_indicator_file_invalid_extension():
    """Test writing a file without .py extension raises ValueError."""
    with pytest.raises(ValueError, match="must end with .py"):
        write_indicator_file(TEST_USER_ID, "test.txt", "content")


def test_write_indicator_file_path_traversal():
    """Test that path traversal attempts are rejected."""
    with pytest.raises(ValueError, match="path traversal"):
        write_indicator_file(TEST_USER_ID, "../test.py", "content")

    with pytest.raises(ValueError, match="path traversal"):
        write_indicator_file(TEST_USER_ID, "subdir/test.py", "content")

    with pytest.raises(ValueError, match="path traversal"):
        write_indicator_file(TEST_USER_ID, "..\\test.py", "content")


def test_read_indicator_file(temp_workspace):
    """Test reading an indicator file returns its content."""
    content = "from vici_trade_sdk import Indicator"
    write_indicator_file(TEST_USER_ID, "test.py", content)

    read_content = read_indicator_file(TEST_USER_ID, "test.py")
    assert read_content == content


def test_read_nonexistent_file():
    """Test reading a non-existent file raises FileNotFoundError."""
    with pytest.raises(FileNotFoundError):
        read_indicator_file(TEST_USER_ID, "nonexistent.py")


def test_read_indicator_file_path_traversal():
    """Test that path traversal attempts are rejected when reading."""
    with pytest.raises(ValueError, match="path traversal"):
        read_indicator_file(TEST_USER_ID, "../test.py")


def test_list_indicator_files(temp_workspace):
    """Test listing indicator files returns all .py files."""
    write_indicator_file(TEST_USER_ID, "indicator1.py", "# indicator 1")
    write_indicator_file(TEST_USER_ID, "indicator2.py", "# indicator 2")

    files = list_indicator_files(TEST_USER_ID)
    filenames = [f.name for f in files]

    assert "indicator1.py" in filenames
    assert "indicator2.py" in filenames


def test_list_indicator_files_empty(temp_workspace):
    """Test listing files in empty directory returns empty list."""
    files = list_indicator_files(TEST_USER_ID)
    assert files == []


def test_list_indicator_files_excludes_private(temp_workspace):
    """Test that files starting with _ are excluded."""
    write_indicator_file(TEST_USER_ID, "public.py", "# public")
    write_indicator_file(TEST_USER_ID, "_private.py", "# private")

    files = list_indicator_files(TEST_USER_ID)
    filenames = [f.name for f in files]

    assert "public.py" in filenames
    assert "_private.py" not in filenames


def test_delete_indicator_file(temp_workspace):
    """Test deleting an indicator file removes it from disk."""
    write_indicator_file(TEST_USER_ID, "test.py", "# content")
    indicators_dir = get_indicators_dir(TEST_USER_ID)
    file_path = indicators_dir / "test.py"

    assert file_path.exists()
    delete_indicator_file(TEST_USER_ID, "test.py")
    assert not file_path.exists()


def test_delete_nonexistent_file():
    """Test deleting a non-existent file raises FileNotFoundError."""
    with pytest.raises(FileNotFoundError):
        delete_indicator_file(TEST_USER_ID, "nonexistent.py")


def test_delete_indicator_file_path_traversal():
    """Test that path traversal attempts are rejected when deleting."""
    with pytest.raises(ValueError, match="path traversal"):
        delete_indicator_file(TEST_USER_ID, "../test.py")


def test_rename_indicator_file(temp_workspace):
    """Test renaming an indicator file."""
    write_indicator_file(TEST_USER_ID, "old.py", "# content")
    new_path = rename_indicator_file(TEST_USER_ID, "old.py", "new.py")

    indicators_dir = get_indicators_dir(TEST_USER_ID)
    assert not (indicators_dir / "old.py").exists()
    assert (indicators_dir / "new.py").exists()
    assert new_path.name == "new.py"


def test_rename_indicator_file_not_found():
    """Test renaming a non-existent file raises FileNotFoundError."""
    with pytest.raises(FileNotFoundError):
        rename_indicator_file(TEST_USER_ID, "nonexistent.py", "new.py")


def test_rename_indicator_file_already_exists(temp_workspace):
    """Test renaming to an existing filename raises FileExistsError."""
    write_indicator_file(TEST_USER_ID, "old.py", "# old")
    write_indicator_file(TEST_USER_ID, "new.py", "# new")

    with pytest.raises(FileExistsError):
        rename_indicator_file(TEST_USER_ID, "old.py", "new.py")


def test_rename_indicator_file_invalid_extension():
    """Test renaming to a file without .py extension raises ValueError."""
    write_indicator_file(TEST_USER_ID, "test.py", "# content")

    with pytest.raises(ValueError, match="must end with .py"):
        rename_indicator_file(TEST_USER_ID, "test.py", "test.txt")


def test_rename_indicator_file_path_traversal_old():
    """Test that path traversal in old filename is rejected."""
    with pytest.raises(ValueError, match="path traversal"):
        rename_indicator_file(TEST_USER_ID, "../old.py", "new.py")


def test_rename_indicator_file_path_traversal_new():
    """Test that path traversal in new filename is rejected."""
    write_indicator_file(TEST_USER_ID, "old.py", "# content")

    with pytest.raises(ValueError, match="path traversal"):
        rename_indicator_file(TEST_USER_ID, "old.py", "../new.py")


def test_get_indicator_file_path(temp_workspace):
    """Test getting the full path to an indicator file."""
    indicators_dir = get_indicators_dir(TEST_USER_ID)
    file_path = get_indicator_file_path(TEST_USER_ID, "test.py")

    assert file_path == indicators_dir / "test.py"


def test_get_indicator_file_path_rejects_traversal():
    """Test that get_indicator_file_path rejects path traversal."""
    with pytest.raises(ValueError, match="path traversal"):
        get_indicator_file_path(TEST_USER_ID, "../test.py")
