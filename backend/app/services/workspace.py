"""User workspace directory management.

Manages per-user workspace directories at ~/.vici-backtest/users/{user_id}/
where each user stores their custom trading strategies, indicators, and reports.
"""

import logging
import shutil
from pathlib import Path

logger = logging.getLogger(__name__)


def get_workspace_root() -> Path:
    """Get the root workspace directory path.

    Returns:
        Path to ~/.vici-backtest directory.
    """
    return Path.home() / ".vici-backtest"


def get_user_workspace_dir(user_id: int) -> Path:
    """Get a specific user's workspace directory path.

    Args:
        user_id: The user's ID.

    Returns:
        Path to ~/.vici-backtest/users/{user_id} directory.
    """
    return get_workspace_root() / "users" / str(user_id)


def get_strategies_dir(user_id: int) -> Path:
    """Get the strategies directory path for a user.

    Args:
        user_id: The user's ID.

    Returns:
        Path to user's strategies directory.
    """
    return get_user_workspace_dir(user_id) / "strategies"


def get_indicators_dir(user_id: int) -> Path:
    """Get the indicators directory path for a user.

    Args:
        user_id: The user's ID.

    Returns:
        Path to user's indicators directory.
    """
    return get_user_workspace_dir(user_id) / "indicators"


def get_reports_dir(user_id: int) -> Path:
    """Get the reports directory path for a user.

    Args:
        user_id: The user's ID.

    Returns:
        Path to user's reports directory.
    """
    return get_user_workspace_dir(user_id) / "reports"


def ensure_user_workspace_exists(user_id: int) -> None:
    """Create the user's workspace directory structure if it doesn't exist.

    Args:
        user_id: The user's ID.

    Creates:
        - ~/.vici-backtest/users/{user_id}/
        - ~/.vici-backtest/users/{user_id}/strategies/
        - ~/.vici-backtest/users/{user_id}/indicators/
        - ~/.vici-backtest/users/{user_id}/reports/
    """
    workspace = get_user_workspace_dir(user_id)
    strategies = get_strategies_dir(user_id)
    indicators = get_indicators_dir(user_id)
    reports = get_reports_dir(user_id)

    workspace.mkdir(parents=True, exist_ok=True)
    strategies.mkdir(parents=True, exist_ok=True)
    indicators.mkdir(parents=True, exist_ok=True)
    reports.mkdir(parents=True, exist_ok=True)

    logger.info("User workspace directory ready: %s", workspace)


def ensure_indicators_dir_exists(user_id: int) -> None:
    """Create the user's indicators directory if it doesn't exist.

    Args:
        user_id: The user's ID.

    Creates:
        - ~/.vici-backtest/users/{user_id}/indicators/
    """
    indicators = get_indicators_dir(user_id)
    indicators.mkdir(parents=True, exist_ok=True)


def initialize_user_workspace_with_examples(user_id: int, builtin_strategies_dir: Path) -> None:
    """Copy built-in example strategies to user's workspace if empty.

    Args:
        user_id: The user's ID.
        builtin_strategies_dir: Path to backend/strategies/ directory.
    """
    ensure_user_workspace_exists(user_id)
    strategies_dir = get_strategies_dir(user_id)

    # Check if workspace already has strategies
    existing_files = list(strategies_dir.glob("*.py"))
    if existing_files:
        logger.info("User %d workspace already has strategies, skipping initialization", user_id)
        return

    # Copy example strategies from codebase to workspace
    if not builtin_strategies_dir.exists():
        logger.warning("Built-in strategies directory not found: %s", builtin_strategies_dir)
        return

    copied_count = 0
    for py_file in builtin_strategies_dir.glob("*.py"):
        if py_file.name.startswith("_"):
            continue

        dest = strategies_dir / py_file.name
        shutil.copy2(py_file, dest)
        copied_count += 1
        logger.info("Copied example strategy: %s", py_file.name)

    logger.info("Initialized user %d workspace with %d example strategies", user_id, copied_count)


def list_strategy_files(user_id: int) -> list[Path]:
    """List all Python files in the user's strategies directory.

    Args:
        user_id: The user's ID.

    Returns:
        List of Path objects for .py files in the strategies directory.
    """
    strategies_dir = get_strategies_dir(user_id)
    if not strategies_dir.exists():
        return []

    return sorted(
        path for path in strategies_dir.glob("*.py")
        if not path.name.startswith("_")
    )


def read_strategy_file(user_id: int, filename: str) -> str:
    """Read the contents of a strategy file.

    Args:
        user_id: The user's ID.
        filename: Name of the strategy file (e.g., "my_strategy.py").

    Returns:
        File contents as a string.

    Raises:
        FileNotFoundError: If the file doesn't exist.
        ValueError: If filename tries to escape the strategies directory.
    """
    if ".." in filename or "/" in filename or "\\" in filename:
        raise ValueError("Invalid filename: cannot contain path traversal")

    file_path = get_strategies_dir(user_id) / filename
    if not file_path.exists():
        raise FileNotFoundError(f"Strategy file not found: {filename}")

    return file_path.read_text(encoding="utf-8")


def write_strategy_file(user_id: int, filename: str, content: str) -> Path:
    """Write or update a strategy file.

    Args:
        user_id: The user's ID.
        filename: Name of the strategy file (e.g., "my_strategy.py").
        content: Python code content.

    Returns:
        Path to the created/updated file.

    Raises:
        ValueError: If filename is invalid or doesn't end with .py.
    """
    if not filename.endswith(".py"):
        raise ValueError("Filename must end with .py")

    if ".." in filename or "/" in filename or "\\" in filename:
        raise ValueError("Invalid filename: cannot contain path traversal")

    ensure_user_workspace_exists(user_id)
    file_path = get_strategies_dir(user_id) / filename
    file_path.write_text(content, encoding="utf-8")

    logger.info("Strategy file written for user %d: %s", user_id, file_path)
    return file_path


def delete_strategy_file(user_id: int, filename: str) -> None:
    """Delete a strategy file.

    Args:
        user_id: The user's ID.
        filename: Name of the strategy file (e.g., "my_strategy.py").

    Raises:
        FileNotFoundError: If the file doesn't exist.
        ValueError: If filename tries to escape the strategies directory.
    """
    if ".." in filename or "/" in filename or "\\" in filename:
        raise ValueError("Invalid filename: cannot contain path traversal")

    file_path = get_strategies_dir(user_id) / filename
    if not file_path.exists():
        raise FileNotFoundError(f"Strategy file not found: {filename}")

    file_path.unlink()
    logger.info("Strategy file deleted for user %d: %s", user_id, file_path)


def rename_strategy_file(user_id: int, old_filename: str, new_filename: str) -> Path:
    """Rename a strategy file.

    Args:
        user_id: The user's ID.
        old_filename: Current name of the strategy file.
        new_filename: New name for the strategy file.

    Returns:
        Path to the renamed file.

    Raises:
        FileNotFoundError: If the old file doesn't exist.
        FileExistsError: If a file with the new name already exists.
        ValueError: If either filename is invalid.
    """
    # Validate both filenames
    if ".." in old_filename or "/" in old_filename or "\\" in old_filename:
        raise ValueError("Invalid old filename: cannot contain path traversal")

    if ".." in new_filename or "/" in new_filename or "\\" in new_filename:
        raise ValueError("Invalid new filename: cannot contain path traversal")

    if not new_filename.endswith(".py"):
        raise ValueError("New filename must end with .py")

    strategies_dir = get_strategies_dir(user_id)
    old_path = strategies_dir / old_filename
    new_path = strategies_dir / new_filename

    # Check if old file exists
    if not old_path.exists():
        raise FileNotFoundError(f"Strategy file not found: {old_filename}")

    # Check if new filename already exists
    if new_path.exists():
        raise FileExistsError(f"File already exists: {new_filename}")

    # Rename the file
    old_path.rename(new_path)
    logger.info("Strategy file renamed for user %d: %s -> %s", user_id, old_filename, new_filename)

    return new_path


def get_strategy_file_path(user_id: int, filename: str) -> Path:
    """Get the full path to a strategy file.

    Args:
        user_id: The user's ID.
        filename: Name of the strategy file (e.g., "my_strategy.py").

    Returns:
        Path object for the strategy file.

    Raises:
        ValueError: If filename tries to escape the strategies directory.
    """
    if ".." in filename or "/" in filename or "\\" in filename:
        raise ValueError("Invalid filename: cannot contain path traversal")

    return get_strategies_dir(user_id) / filename


# ── Indicator File Management ──


def list_indicator_files(user_id: int) -> list[Path]:
    """List all Python files in the user's indicators directory.

    Args:
        user_id: The user's ID.

    Returns:
        List of Path objects for .py files in the indicators directory.
    """
    indicators_dir = get_indicators_dir(user_id)
    if not indicators_dir.exists():
        return []

    return sorted(
        path for path in indicators_dir.glob("*.py")
        if not path.name.startswith("_")
    )


def read_indicator_file(user_id: int, filename: str) -> str:
    """Read the contents of an indicator file.

    Args:
        user_id: The user's ID.
        filename: Name of the indicator file (e.g., "my_indicator.py").

    Returns:
        File contents as a string.

    Raises:
        FileNotFoundError: If the file doesn't exist.
        ValueError: If filename tries to escape the indicators directory.
    """
    if ".." in filename or "/" in filename or "\\" in filename:
        raise ValueError("Invalid filename: cannot contain path traversal")

    file_path = get_indicators_dir(user_id) / filename
    if not file_path.exists():
        raise FileNotFoundError(f"Indicator file not found: {filename}")

    return file_path.read_text(encoding="utf-8")


def write_indicator_file(user_id: int, filename: str, content: str) -> Path:
    """Write or update an indicator file.

    Args:
        user_id: The user's ID.
        filename: Name of the indicator file (e.g., "my_indicator.py").
        content: Python code content.

    Returns:
        Path to the created/updated file.

    Raises:
        ValueError: If filename is invalid or doesn't end with .py.
    """
    if not filename.endswith(".py"):
        raise ValueError("Filename must end with .py")

    if ".." in filename or "/" in filename or "\\" in filename:
        raise ValueError("Invalid filename: cannot contain path traversal")

    ensure_indicators_dir_exists(user_id)
    file_path = get_indicators_dir(user_id) / filename
    file_path.write_text(content, encoding="utf-8")

    logger.info("Indicator file written for user %d: %s", user_id, file_path)
    return file_path


def delete_indicator_file(user_id: int, filename: str) -> None:
    """Delete an indicator file.

    Args:
        user_id: The user's ID.
        filename: Name of the indicator file (e.g., "my_indicator.py").

    Raises:
        FileNotFoundError: If the file doesn't exist.
        ValueError: If filename tries to escape the indicators directory.
    """
    if ".." in filename or "/" in filename or "\\" in filename:
        raise ValueError("Invalid filename: cannot contain path traversal")

    file_path = get_indicators_dir(user_id) / filename
    if not file_path.exists():
        raise FileNotFoundError(f"Indicator file not found: {filename}")

    file_path.unlink()
    logger.info("Indicator file deleted for user %d: %s", user_id, file_path)


def rename_indicator_file(user_id: int, old_filename: str, new_filename: str) -> Path:
    """Rename an indicator file.

    Args:
        user_id: The user's ID.
        old_filename: Current name of the indicator file.
        new_filename: New name for the indicator file.

    Returns:
        Path to the renamed file.

    Raises:
        FileNotFoundError: If the old file doesn't exist.
        FileExistsError: If a file with the new name already exists.
        ValueError: If either filename is invalid.
    """
    # Validate both filenames
    if ".." in old_filename or "/" in old_filename or "\\" in old_filename:
        raise ValueError("Invalid old filename: cannot contain path traversal")

    if ".." in new_filename or "/" in new_filename or "\\" in new_filename:
        raise ValueError("Invalid new filename: cannot contain path traversal")

    if not new_filename.endswith(".py"):
        raise ValueError("New filename must end with .py")

    indicators_dir = get_indicators_dir(user_id)
    old_path = indicators_dir / old_filename
    new_path = indicators_dir / new_filename

    # Check if old file exists
    if not old_path.exists():
        raise FileNotFoundError(f"Indicator file not found: {old_filename}")

    # Check if new filename already exists
    if new_path.exists():
        raise FileExistsError(f"File already exists: {new_filename}")

    # Rename the file
    old_path.rename(new_path)
    logger.info("Indicator file renamed for user %d: %s -> %s", user_id, old_filename, new_filename)

    return new_path


def get_indicator_file_path(user_id: int, filename: str) -> Path:
    """Get the full path to an indicator file.

    Args:
        user_id: The user's ID.
        filename: Name of the indicator file (e.g., "my_indicator.py").

    Returns:
        Path object for the indicator file.

    Raises:
        ValueError: If filename tries to escape the indicators directory.
    """
    if ".." in filename or "/" in filename or "\\" in filename:
        raise ValueError("Invalid filename: cannot contain path traversal")

    return get_indicators_dir(user_id) / filename
