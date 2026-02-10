"""AST-based code validation for user-submitted strategies and indicators.

Validates Python code to prevent dangerous operations like:
- File system access (except workspace)
- Network access
- Subprocess execution
- Dynamic code execution (eval, exec, compile)
- Unsafe imports
"""

import ast
from dataclasses import dataclass
from typing import Any


@dataclass
class ValidationResult:
    """Result of code validation."""

    is_valid: bool
    errors: list[str]
    warnings: list[str]


# Dangerous built-in functions that should not be used
DANGEROUS_BUILTINS = {
    "eval",
    "exec",
    "compile",
    "__import__",
    "open",  # File I/O should be restricted
    "input",  # No interactive input in backtests
    "breakpoint",  # No debugging
}

# Dangerous modules that should not be imported
DANGEROUS_MODULES = {
    "os",  # System operations
    "sys",  # System-specific parameters
    "subprocess",  # Process execution
    "socket",  # Network access
    "urllib",  # Network access
    "requests",  # Network access
    "http",  # Network access
    "ftplib",  # Network access
    "smtplib",  # Network access
    "telnetlib",  # Network access
    "pickle",  # Arbitrary code execution
    "marshal",  # Arbitrary code execution
    "shelve",  # File access
    "dbm",  # File access
    "importlib",  # Dynamic imports
    "ctypes",  # Low-level system access
    "multiprocessing",  # Process creation
    "threading",  # Thread creation (can cause issues in sandboxed env)
    "asyncio",  # Async operations not supported in strategies
    "pathlib",  # File system access
    "shutil",  # File operations
    "tempfile",  # Temporary file creation
    "glob",  # File system traversal
}

# Allowed modules for trading strategies
ALLOWED_MODULES = {
    "pandas",
    "numpy",
    "math",
    "datetime",
    "typing",
    "dataclasses",
    "collections",
    "itertools",
    "functools",
    "operator",
    "decimal",
    "fractions",
    "statistics",
    "vici_trade_sdk",  # Our SDK
}


class CodeValidator(ast.NodeVisitor):
    """AST visitor that validates user code for security issues."""

    def __init__(self):
        """Initialize the validator."""
        self.errors: list[str] = []
        self.warnings: list[str] = []
        self.imports: set[str] = set()

    def visit_Import(self, node: ast.Import) -> Any:
        """Check import statements."""
        for alias in node.names:
            module_name = alias.name.split(".")[0]
            self.imports.add(module_name)

            if module_name in DANGEROUS_MODULES:
                self.errors.append(
                    f"Line {node.lineno}: Dangerous module import not allowed: {alias.name}"
                )
            elif module_name not in ALLOWED_MODULES:
                self.warnings.append(
                    f"Line {node.lineno}: Unknown module import: {alias.name}. "
                    "This may cause issues if the module is not available."
                )

        self.generic_visit(node)

    def visit_ImportFrom(self, node: ast.ImportFrom) -> Any:
        """Check from ... import statements."""
        if node.module:
            module_name = node.module.split(".")[0]
            self.imports.add(module_name)

            if module_name in DANGEROUS_MODULES:
                self.errors.append(
                    f"Line {node.lineno}: Dangerous module import not allowed: {node.module}"
                )
            elif module_name not in ALLOWED_MODULES:
                self.warnings.append(
                    f"Line {node.lineno}: Unknown module import: {node.module}. "
                    "This may cause issues if the module is not available."
                )

        self.generic_visit(node)

    def visit_Call(self, node: ast.Call) -> Any:
        """Check function calls for dangerous operations."""
        # Check for dangerous built-in functions
        if isinstance(node.func, ast.Name):
            func_name = node.func.id
            if func_name in DANGEROUS_BUILTINS:
                self.errors.append(
                    f"Line {node.lineno}: Dangerous function call not allowed: {func_name}()"
                )

        # Check for __import__ calls
        if isinstance(node.func, ast.Name) and node.func.id == "__import__":
            self.errors.append(
                f"Line {node.lineno}: Dynamic imports via __import__() are not allowed"
            )

        self.generic_visit(node)

    def visit_Attribute(self, node: ast.Attribute) -> Any:
        """Check attribute access for dangerous patterns."""
        # Check for __dict__, __class__, __globals__, etc.
        if node.attr.startswith("__") and node.attr.endswith("__"):
            if node.attr in ("__dict__", "__class__", "__globals__", "__builtins__"):
                self.errors.append(
                    f"Line {node.lineno}: Access to {node.attr} is not allowed"
                )

        self.generic_visit(node)

    def visit_Delete(self, node: ast.Delete) -> Any:
        """Warn about delete statements."""
        self.warnings.append(
            f"Line {node.lineno}: Delete statement found. "
            "Ensure you're not deleting critical objects."
        )
        self.generic_visit(node)


def validate_code(code: str) -> ValidationResult:
    """Validate Python code for security issues.

    Args:
        code: Python source code to validate.

    Returns:
        ValidationResult with validation status, errors, and warnings.
    """
    errors: list[str] = []
    warnings: list[str] = []

    # First, try to parse the code
    try:
        tree = ast.parse(code)
    except SyntaxError as e:
        return ValidationResult(
            is_valid=False,
            errors=[f"Syntax error at line {e.lineno}: {e.msg}"],
            warnings=[],
        )
    except Exception as e:
        return ValidationResult(
            is_valid=False,
            errors=[f"Failed to parse code: {str(e)}"],
            warnings=[],
        )

    # Validate the AST
    validator = CodeValidator()
    validator.visit(tree)

    errors.extend(validator.errors)
    warnings.extend(validator.warnings)

    # Additional validations
    # Check if the code defines at least one class
    has_class = any(isinstance(node, ast.ClassDef) for node in ast.walk(tree))
    if not has_class:
        warnings.append(
            "No class definition found. Strategy/Indicator should define a class."
        )

    return ValidationResult(
        is_valid=len(errors) == 0,
        errors=errors,
        warnings=warnings,
    )


def validate_strategy_code(code: str) -> ValidationResult:
    """Validate strategy code.

    Args:
        code: Strategy source code.

    Returns:
        ValidationResult with validation status.
    """
    result = validate_code(code)

    # Additional strategy-specific validations can be added here
    # For example, checking if the class inherits from Strategy

    return result


def validate_indicator_code(code: str) -> ValidationResult:
    """Validate indicator code.

    Args:
        code: Indicator source code.

    Returns:
        ValidationResult with validation status.
    """
    result = validate_code(code)

    # Additional indicator-specific validations can be added here
    # For example, checking if the class inherits from Indicator

    return result
