"""Indicator Loader: dynamically discover and load indicator classes.

Scans the indicators directory for Python files containing Indicator
subclasses, and provides a registry for the API to use.
"""

import importlib
import importlib.util
import inspect
import logging
from pathlib import Path

from vici_trade_sdk import Indicator

from app.services.workspace import get_indicators_dir

logger = logging.getLogger(__name__)


def discover_indicators(user_id: int, directory: Path | None = None) -> dict[str, type[Indicator]]:
    """Scan user workspace for Indicator subclasses and return a registry.

    Args:
        user_id: The user's ID.
        directory: Path to scan. Defaults to user workspace indicators directory.

    Returns:
        Dict mapping indicator class name to the class itself.
    """
    search_dir = directory or get_indicators_dir(user_id)
    registry: dict[str, type[Indicator]] = {}

    if not search_dir.exists():
        logger.warning("Indicators directory not found: %s", search_dir)
        return registry

    for py_file in search_dir.glob("*.py"):
        if py_file.name.startswith("_"):
            continue

        try:
            module = _load_module_from_file(py_file)
            for name, obj in inspect.getmembers(module, inspect.isclass):
                if issubclass(obj, Indicator) and obj is not Indicator:
                    registry[name] = obj
                    logger.info("Discovered indicator: %s from %s", name, py_file.name)
        except Exception as exc:
            logger.error("Failed to load indicator from %s: %s", py_file.name, exc)

    return registry


def _load_module_from_file(filepath: Path):
    """Import a Python module from a file path.

    Args:
        filepath: Path to the .py file.

    Returns:
        The loaded module object.
    """
    module_name = filepath.stem
    spec = importlib.util.spec_from_file_location(module_name, filepath)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def get_indicator_class(user_id: int,
                        class_name: str,
                        directory: Path | None = None) -> type[Indicator] | None:
    """Look up an indicator class by name.

    Args:
        user_id: The user's ID.
        class_name: The indicator class name (e.g., "WilliamsR").
        directory: Optional directory to search.

    Returns:
        The indicator class, or None if not found.
    """
    registry = discover_indicators(user_id, directory)
    return registry.get(class_name)


def list_indicator_info(user_id: int, directory: Path | None = None) -> list[dict]:
    """List all available custom indicators with metadata.

    Args:
        user_id: The user's ID.
        directory: Optional directory to search.

    Returns:
        List of dicts with indicator information.
    """
    registry = discover_indicators(user_id, directory)
    result = []

    for class_name, cls in registry.items():
        try:
            # Try to instantiate with no args to get the name
            # Note: This may fail for indicators requiring constructor args
            instance = cls()
            result.append({
                "class_name": class_name,
                "name": instance.name,
                "docstring": (cls.__doc__ or "").strip(),
            })
        except Exception as exc:
            # If instantiation fails, use class name as fallback
            logger.warning("Could not instantiate indicator %s: %s", class_name, exc)
            result.append({
                "class_name": class_name,
                "name": class_name,
                "docstring": (cls.__doc__ or "").strip(),
            })

    return result
