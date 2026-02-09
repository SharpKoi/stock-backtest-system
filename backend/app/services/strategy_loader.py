"""Strategy Loader: dynamically discover and load strategy classes.

Scans the strategies directory for Python files containing Strategy
subclasses, and provides a registry for the API to use.
"""

import importlib
import importlib.util
import inspect
import logging
from pathlib import Path

from app.services.strategy import Strategy
from app.services.workspace import get_strategies_dir

logger = logging.getLogger(__name__)


def discover_strategies(directory: Path | None = None) -> dict[str, type[Strategy]]:
    """Scan user workspace for Strategy subclasses and return a registry.

    Args:
        directory: Path to scan. Defaults to user workspace strategies directory.

    Returns:
        Dict mapping strategy class name to the class itself.
    """
    search_dir = directory or get_strategies_dir()
    registry: dict[str, type[Strategy]] = {}

    if not search_dir.exists():
        logger.warning("Strategies directory not found: %s", search_dir)
        return registry

    for py_file in search_dir.glob("*.py"):
        if py_file.name.startswith("_"):
            continue

        try:
            module = _load_module_from_file(py_file)
            for name, obj in inspect.getmembers(module, inspect.isclass):
                if issubclass(obj, Strategy) and obj is not Strategy:
                    registry[name] = obj
                    logger.info("Discovered strategy: %s from %s", name, py_file.name)
        except Exception as exc:
            logger.error("Failed to load strategy from %s: %s", py_file.name, exc)

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


def get_strategy_class(class_name: str,
                       directory: Path | None = None) -> type[Strategy] | None:
    """Look up a strategy class by name.

    Args:
        class_name: The strategy class name (e.g., "SMACrossover").
        directory: Optional directory to search.

    Returns:
        The strategy class, or None if not found.
    """
    registry = discover_strategies(directory)
    return registry.get(class_name)


def list_strategy_info(directory: Path | None = None) -> list[dict]:
    """List all available strategies with metadata.

    Args:
        directory: Optional directory to search.

    Returns:
        List of dicts with strategy information.
    """
    registry = discover_strategies(directory)
    result = []

    for class_name, cls in registry.items():
        try:
            instance = cls()
            result.append({
                "class_name": class_name,
                "name": instance.name,
                "docstring": (cls.__doc__ or "").strip(),
                "indicators": instance.indicators(),
            })
        except Exception as exc:
            logger.error("Failed to inspect strategy %s: %s", class_name, exc)
            result.append({
                "class_name": class_name,
                "name": class_name,
                "docstring": (cls.__doc__ or "").strip(),
                "indicators": [],
            })

    return result
