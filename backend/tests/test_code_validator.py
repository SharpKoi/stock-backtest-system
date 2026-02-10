"""Tests for code validation."""

import pytest
from pathlib import Path

from app.services.code_validator import validate_code, validate_strategy_code, validate_indicator_code


class TestCodeValidator:
    """Test suite for AST-based code validation."""

    def test_dangerous_builtin_functions(self):
        """Test that dangerous built-in functions are blocked."""
        dangerous_code = """
def exploit():
    eval("print('pwned')")
    exec("import os")
    compile("code", "<string>", "exec")
    __import__("os")
    open("/etc/passwd")
"""
        result = validate_code(dangerous_code)
        assert not result.is_valid
        assert len(result.errors) >= 5
        assert any("eval" in error for error in result.errors)
        assert any("exec" in error for error in result.errors)
        assert any("compile" in error for error in result.errors)
        assert any("__import__" in error for error in result.errors)
        assert any("open" in error for error in result.errors)

    def test_dangerous_module_imports(self):
        """Test that dangerous module imports are blocked."""
        dangerous_imports = [
            "import os",
            "import sys",
            "import subprocess",
            "import socket",
            "import pickle",
            "from os import system",
            "from subprocess import call",
        ]

        for import_stmt in dangerous_imports:
            code = f"{import_stmt}\n\nclass Test:\n    pass"
            result = validate_code(code)
            assert not result.is_valid, f"Failed to block: {import_stmt}"
            assert len(result.errors) > 0

    def test_allowed_modules(self):
        """Test that safe modules are allowed."""
        safe_code = """
import pandas as pd
import numpy as np
from datetime import datetime
from typing import List
from vici_trade_sdk import Strategy

class SafeStrategy(Strategy):
    pass
"""
        result = validate_code(safe_code)
        assert result.is_valid
        assert len(result.errors) == 0

    def test_attribute_access_restrictions(self):
        """Test that dangerous attribute access is blocked."""
        dangerous_code = """
class Exploit:
    def attack(self):
        globals_dict = self.__class__.__globals__
        builtins = self.__class__.__builtins__
        obj_dict = self.__dict__
"""
        result = validate_code(dangerous_code)
        assert not result.is_valid
        assert any("__globals__" in error for error in result.errors)
        assert any("__builtins__" in error for error in result.errors)
        assert any("__dict__" in error for error in result.errors)

    def test_syntax_error_detection(self):
        """Test that syntax errors are caught."""
        invalid_code = "def broken(\n    pass"
        result = validate_code(invalid_code)
        assert not result.is_valid
        assert len(result.errors) > 0
        assert "Syntax error" in result.errors[0]

    def test_valid_strategy_code(self):
        """Test that valid strategy code passes validation."""
        valid_strategy = """
from vici_trade_sdk import Strategy, Portfolio
import pandas as pd
import numpy as np

class MyStrategy(Strategy):
    @property
    def name(self) -> str:
        return "My Strategy"

    def indicators(self) -> list[dict]:
        return [{"name": "sma", "params": {"period": 50}}]

    def on_bar(self, date: str, data: dict, portfolio: Portfolio) -> None:
        # Safe trading logic
        for symbol in data:
            if 'sma_50' in data[symbol]:
                sma = data[symbol]['sma_50']
                if sma > 100:
                    portfolio.buy(symbol, 100)
"""
        result = validate_strategy_code(valid_strategy)
        assert result.is_valid
        assert len(result.errors) == 0

    def test_valid_indicator_code(self):
        """Test that valid indicator code passes validation."""
        valid_indicator = """
from vici_trade_sdk import Indicator
import pandas as pd
import numpy as np

class MyIndicator(Indicator):
    def __init__(self, period: int = 14):
        self.period = period

    @property
    def name(self) -> str:
        return f"my_indicator_{self.period}"

    def compute(self, df: pd.DataFrame) -> pd.Series:
        return df['close'].rolling(window=self.period).mean()
"""
        result = validate_indicator_code(valid_indicator)
        assert result.is_valid
        assert len(result.errors) == 0

    def test_warning_for_unknown_modules(self):
        """Test that unknown modules generate warnings."""
        code_with_unknown_module = """
import some_unknown_module

class Test:
    pass
"""
        result = validate_code(code_with_unknown_module)
        # Should pass validation but have warnings
        assert result.is_valid
        assert len(result.warnings) > 0
        assert "Unknown module" in result.warnings[0]

    def test_missing_class_definition(self):
        """Test warning when no class is defined."""
        code_without_class = """
import pandas as pd

def some_function():
    pass
"""
        result = validate_code(code_without_class)
        assert result.is_valid  # Not an error, just a warning
        assert len(result.warnings) > 0
        assert "No class definition" in result.warnings[0]


class TestDangerousStrategyExamples:
    """Test that all dangerous strategy examples are blocked."""

    @pytest.fixture
    def examples_dir(self):
        """Get the dangerous strategies examples directory."""
        return Path(__file__).parent.parent.parent / ".claude" / "examples" / "dangerous_strategies"

    def test_file_system_attack(self, examples_dir):
        """Test that file system attack is blocked."""
        file_path = examples_dir / "file_system_attack.py"
        if not file_path.exists():
            pytest.skip("Example file not found")

        code = file_path.read_text()
        result = validate_strategy_code(code)

        assert not result.is_valid
        # Should block: os, shutil, pathlib, open()
        assert any("os" in error for error in result.errors)
        assert any("shutil" in error for error in result.errors)
        assert any("pathlib" in error or "Path" in error for error in result.errors)
        assert any("open" in error for error in result.errors)

    def test_network_attack(self, examples_dir):
        """Test that network attack is blocked."""
        file_path = examples_dir / "network_attack.py"
        if not file_path.exists():
            pytest.skip("Example file not found")

        code = file_path.read_text()
        result = validate_strategy_code(code)

        assert not result.is_valid
        # Should block: socket, urllib, requests, http
        assert any("socket" in error for error in result.errors)
        assert any("urllib" in error for error in result.errors)
        assert any("requests" in error for error in result.errors)
        assert any("http" in error for error in result.errors)

    def test_code_injection(self, examples_dir):
        """Test that code injection is blocked."""
        file_path = examples_dir / "code_injection.py"
        if not file_path.exists():
            pytest.skip("Example file not found")

        code = file_path.read_text()
        result = validate_strategy_code(code)

        assert not result.is_valid
        # Should block: eval, exec, compile, __import__, __globals__, __builtins__
        assert any("eval" in error for error in result.errors)
        assert any("exec" in error for error in result.errors)
        assert any("compile" in error for error in result.errors)
        assert any("__import__" in error for error in result.errors)

    def test_process_execution(self, examples_dir):
        """Test that process execution is blocked."""
        file_path = examples_dir / "process_execution.py"
        if not file_path.exists():
            pytest.skip("Example file not found")

        code = file_path.read_text()
        result = validate_strategy_code(code)

        assert not result.is_valid
        # Should block: os, subprocess, multiprocessing
        assert any("os" in error for error in result.errors)
        assert any("subprocess" in error for error in result.errors)
        assert any("multiprocessing" in error for error in result.errors)

    def test_pickle_attack(self, examples_dir):
        """Test that pickle attack is blocked."""
        file_path = examples_dir / "pickle_attack.py"
        if not file_path.exists():
            pytest.skip("Example file not found")

        code = file_path.read_text()
        result = validate_strategy_code(code)

        assert not result.is_valid
        # Should block: pickle, marshal, open, exec
        assert any("pickle" in error for error in result.errors)
        assert any("marshal" in error for error in result.errors)

    def test_dynamic_import(self, examples_dir):
        """Test that dynamic import is blocked."""
        file_path = examples_dir / "dynamic_import.py"
        if not file_path.exists():
            pytest.skip("Example file not found")

        code = file_path.read_text()
        result = validate_strategy_code(code)

        assert not result.is_valid
        # Should block: importlib, sys, __import__
        assert any("importlib" in error for error in result.errors)
        assert any("sys" in error for error in result.errors)
        assert any("__import__" in error for error in result.errors)

    def test_all_dangerous_examples_blocked(self, examples_dir):
        """Ensure all dangerous strategy examples fail validation."""
        if not examples_dir.exists():
            pytest.skip("Examples directory not found")

        py_files = list(examples_dir.glob("*.py"))
        assert len(py_files) > 0, "No example files found"

        blocked_count = 0
        for file_path in py_files:
            code = file_path.read_text()
            result = validate_strategy_code(code)

            if not result.is_valid:
                blocked_count += 1
                print(f"✓ Blocked: {file_path.name} ({len(result.errors)} errors)")
            else:
                print(f"✗ FAILED TO BLOCK: {file_path.name}")

        # All dangerous examples should be blocked
        assert blocked_count == len(py_files), f"Only blocked {blocked_count}/{len(py_files)} dangerous strategies"
