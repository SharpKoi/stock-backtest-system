"""Tests for workspace management."""

import shutil
from pathlib import Path

import pytest

from app.services.workspace import (
    delete_strategy_file,
    ensure_workspace_exists,
    get_strategies_dir,
    get_workspace_dir,
    initialize_workspace_with_examples,
    list_strategy_files,
    read_strategy_file,
    write_strategy_file,
)


@pytest.fixture
def clean_workspace():
    """Clean up test workspace before and after tests."""
    workspace = get_workspace_dir()
    if workspace.exists():
        shutil.rmtree(workspace)
    yield
    if workspace.exists():
        shutil.rmtree(workspace)


def test_get_workspace_dir():
    """Test getting workspace directory path."""
    workspace = get_workspace_dir()
    assert workspace == Path.home() / ".vici-backtest"


def test_get_strategies_dir():
    """Test getting strategies directory path."""
    strategies = get_strategies_dir()
    assert strategies == Path.home() / ".vici-backtest" / "strategies"


def test_ensure_workspace_exists(clean_workspace):
    """Test workspace directory creation."""
    ensure_workspace_exists()

    workspace = get_workspace_dir()
    strategies = get_strategies_dir()

    assert workspace.exists()
    assert workspace.is_dir()
    assert strategies.exists()
    assert strategies.is_dir()


def test_write_strategy_file(clean_workspace):
    """Test writing a strategy file."""
    filename = "test_strategy.py"
    content = "# Test strategy"

    path = write_strategy_file(filename, content)

    assert path.exists()
    assert path.name == filename
    assert path.read_text() == content


def test_write_strategy_file_creates_workspace(clean_workspace):
    """Test that writing creates workspace if it doesn't exist."""
    assert not get_workspace_dir().exists()

    write_strategy_file("test.py", "# Test")

    assert get_workspace_dir().exists()
    assert get_strategies_dir().exists()


def test_write_strategy_file_invalid_extension(clean_workspace):
    """Test writing file without .py extension fails."""
    with pytest.raises(ValueError, match="must end with .py"):
        write_strategy_file("invalid.txt", "content")


def test_write_strategy_file_path_traversal(clean_workspace):
    """Test that path traversal is blocked."""
    with pytest.raises(ValueError, match="cannot contain path traversal"):
        write_strategy_file("../evil.py", "content")

    with pytest.raises(ValueError, match="cannot contain path traversal"):
        write_strategy_file("subdir/file.py", "content")


def test_read_strategy_file(clean_workspace):
    """Test reading a strategy file."""
    filename = "read_test.py"
    content = "# Read test content"
    write_strategy_file(filename, content)

    read_content = read_strategy_file(filename)

    assert read_content == content


def test_read_nonexistent_file(clean_workspace):
    """Test reading nonexistent file raises error."""
    with pytest.raises(FileNotFoundError, match="Strategy file not found"):
        read_strategy_file("nonexistent.py")


def test_read_strategy_file_path_traversal(clean_workspace):
    """Test that path traversal is blocked for reading."""
    with pytest.raises(ValueError, match="cannot contain path traversal"):
        read_strategy_file("../evil.py")


def test_list_strategy_files(clean_workspace):
    """Test listing strategy files."""
    write_strategy_file("strategy1.py", "# Strategy 1")
    write_strategy_file("strategy2.py", "# Strategy 2")
    write_strategy_file("_private.py", "# Should be ignored")

    files = list_strategy_files()

    assert len(files) == 2
    filenames = [f.name for f in files]
    assert "strategy1.py" in filenames
    assert "strategy2.py" in filenames
    assert "_private.py" not in filenames


def test_list_strategy_files_empty(clean_workspace):
    """Test listing files when directory doesn't exist."""
    files = list_strategy_files()
    assert files == []


def test_delete_strategy_file(clean_workspace):
    """Test deleting a strategy file."""
    filename = "delete_test.py"
    write_strategy_file(filename, "# Delete test")

    delete_strategy_file(filename)

    assert not (get_strategies_dir() / filename).exists()


def test_delete_nonexistent_file(clean_workspace):
    """Test deleting nonexistent file raises error."""
    with pytest.raises(FileNotFoundError, match="Strategy file not found"):
        delete_strategy_file("nonexistent.py")


def test_delete_strategy_file_path_traversal(clean_workspace):
    """Test that path traversal is blocked for deletion."""
    with pytest.raises(ValueError, match="cannot contain path traversal"):
        delete_strategy_file("../evil.py")


def test_initialize_workspace_with_examples(clean_workspace, tmp_path):
    """Test initializing workspace with example strategies."""
    # Create fake built-in strategies
    builtin_dir = tmp_path / "builtin_strategies"
    builtin_dir.mkdir()

    (builtin_dir / "example1.py").write_text("# Example 1")
    (builtin_dir / "example2.py").write_text("# Example 2")
    (builtin_dir / "_private.py").write_text("# Should not be copied")

    # Initialize workspace
    initialize_workspace_with_examples(builtin_dir)

    # Check files were copied
    strategies_dir = get_strategies_dir()
    assert (strategies_dir / "example1.py").exists()
    assert (strategies_dir / "example2.py").exists()
    assert not (strategies_dir / "_private.py").exists()


def test_initialize_workspace_skips_if_not_empty(clean_workspace, tmp_path):
    """Test that initialization skips if workspace already has strategies."""
    # Create a strategy in workspace
    write_strategy_file("existing.py", "# Existing")

    # Create built-in strategies
    builtin_dir = tmp_path / "builtin_strategies"
    builtin_dir.mkdir()
    (builtin_dir / "example.py").write_text("# Example")

    # Initialize should skip
    initialize_workspace_with_examples(builtin_dir)

    # Only the existing file should be there
    files = list_strategy_files()
    assert len(files) == 1
    assert files[0].name == "existing.py"


def test_initialize_workspace_handles_missing_builtin_dir(clean_workspace, tmp_path):
    """Test that initialization handles missing built-in directory gracefully."""
    nonexistent_dir = tmp_path / "nonexistent"

    # Should not raise, just log warning
    initialize_workspace_with_examples(nonexistent_dir)

    # Workspace should be created but empty
    assert get_workspace_dir().exists()
    assert len(list_strategy_files()) == 0
