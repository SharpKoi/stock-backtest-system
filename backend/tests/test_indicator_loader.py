"""Tests for indicator loading from user workspace."""

from textwrap import dedent

import pytest
from vici_trade_sdk import Indicator

from app.services.indicator_loader import (
    discover_indicators,
    get_indicator_class,
    list_indicator_info,
)


@pytest.fixture
def temp_indicators_dir(tmp_path):
    """Create a temporary directory for indicator files."""
    indicators_dir = tmp_path / "indicators"
    indicators_dir.mkdir()
    return indicators_dir


def test_discover_indicators_empty_directory(temp_indicators_dir):
    """Test discovering indicators in an empty directory returns empty dict."""
    registry = discover_indicators(temp_indicators_dir)
    assert registry == {}


def test_discover_indicators_finds_valid_indicator(temp_indicators_dir):
    """Test discovering a valid indicator class."""
    indicator_code = dedent('''
        from vici_trade_sdk import Indicator
        import pandas as pd

        class WilliamsR(Indicator):
            def __init__(self, period: int = 14):
                self.period = period

            @property
            def name(self) -> str:
                return f"williams_r_{self.period}"

            def compute(self, df: pd.DataFrame) -> pd.Series:
                return pd.Series([0] * len(df), index=df.index)
    ''')

    indicator_file = temp_indicators_dir / "williams_r.py"
    indicator_file.write_text(indicator_code)

    registry = discover_indicators(temp_indicators_dir)

    assert "WilliamsR" in registry
    assert issubclass(registry["WilliamsR"], Indicator)


def test_discover_indicators_multiple_classes(temp_indicators_dir):
    """Test discovering multiple indicator classes in one file."""
    indicator_code = dedent('''
        from vici_trade_sdk import Indicator
        import pandas as pd

        class IndicatorOne(Indicator):
            @property
            def name(self) -> str:
                return "indicator_one"

            def compute(self, df: pd.DataFrame) -> pd.Series:
                return df["close"]

        class IndicatorTwo(Indicator):
            @property
            def name(self) -> str:
                return "indicator_two"

            def compute(self, df: pd.DataFrame) -> pd.Series:
                return df["close"]
    ''')

    indicator_file = temp_indicators_dir / "indicators.py"
    indicator_file.write_text(indicator_code)

    registry = discover_indicators(temp_indicators_dir)

    assert "IndicatorOne" in registry
    assert "IndicatorTwo" in registry


def test_discover_indicators_ignores_base_class(temp_indicators_dir):
    """Test that the Indicator base class itself is not included."""
    indicator_code = dedent('''
        from vici_trade_sdk import Indicator
        import pandas as pd

        class MyIndicator(Indicator):
            @property
            def name(self) -> str:
                return "my_indicator"

            def compute(self, df: pd.DataFrame) -> pd.Series:
                return df["close"]
    ''')

    indicator_file = temp_indicators_dir / "test.py"
    indicator_file.write_text(indicator_code)

    registry = discover_indicators(temp_indicators_dir)

    assert "MyIndicator" in registry
    assert "Indicator" not in registry


def test_discover_indicators_ignores_private_files(temp_indicators_dir):
    """Test that files starting with _ are ignored."""
    indicator_code = dedent('''
        from vici_trade_sdk import Indicator
        import pandas as pd

        class PrivateIndicator(Indicator):
            @property
            def name(self) -> str:
                return "private"

            def compute(self, df: pd.DataFrame) -> pd.Series:
                return df["close"]
    ''')

    private_file = temp_indicators_dir / "_private.py"
    private_file.write_text(indicator_code)

    registry = discover_indicators(temp_indicators_dir)

    assert "PrivateIndicator" not in registry


def test_discover_indicators_handles_syntax_error(temp_indicators_dir):
    """Test that files with syntax errors are skipped gracefully."""
    bad_code = "this is not valid python code {"

    bad_file = temp_indicators_dir / "bad.py"
    bad_file.write_text(bad_code)

    # Should not raise, just log error
    registry = discover_indicators(temp_indicators_dir)
    assert registry == {}


def test_discover_indicators_handles_import_error(temp_indicators_dir):
    """Test that files with import errors are skipped gracefully."""
    bad_code = "import nonexistent_module"

    bad_file = temp_indicators_dir / "bad_import.py"
    bad_file.write_text(bad_code)

    # Should not raise, just log error
    registry = discover_indicators(temp_indicators_dir)
    assert registry == {}


def test_get_indicator_class_found(temp_indicators_dir):
    """Test retrieving an indicator class by name."""
    indicator_code = dedent('''
        from vici_trade_sdk import Indicator
        import pandas as pd

        class TestIndicator(Indicator):
            @property
            def name(self) -> str:
                return "test"

            def compute(self, df: pd.DataFrame) -> pd.Series:
                return df["close"]
    ''')

    indicator_file = temp_indicators_dir / "test.py"
    indicator_file.write_text(indicator_code)

    indicator_cls = get_indicator_class("TestIndicator", temp_indicators_dir)

    assert indicator_cls is not None
    assert issubclass(indicator_cls, Indicator)


def test_get_indicator_class_not_found(temp_indicators_dir):
    """Test that retrieving a non-existent indicator returns None."""
    indicator_cls = get_indicator_class("NonExistent", temp_indicators_dir)
    assert indicator_cls is None


def test_list_indicator_info(temp_indicators_dir):
    """Test listing indicator metadata."""
    indicator_code = dedent('''
        from vici_trade_sdk import Indicator
        import pandas as pd

        class DocumentedIndicator(Indicator):
            """This is a well-documented indicator."""

            @property
            def name(self) -> str:
                return "documented"

            def compute(self, df: pd.DataFrame) -> pd.Series:
                return df["close"]
    ''')

    indicator_file = temp_indicators_dir / "documented.py"
    indicator_file.write_text(indicator_code)

    info_list = list_indicator_info(temp_indicators_dir)

    assert len(info_list) == 1
    assert info_list[0]["class_name"] == "DocumentedIndicator"
    assert info_list[0]["name"] == "documented"
    assert "well-documented" in info_list[0]["docstring"]


def test_list_indicator_info_handles_instantiation_failure(temp_indicators_dir):
    """Test listing indicators that require constructor arguments."""
    indicator_code = dedent('''
        from vici_trade_sdk import Indicator
        import pandas as pd

        class RequiresArgs(Indicator):
            """Requires constructor arguments."""

            def __init__(self, required_param: int):
                self.required_param = required_param

            @property
            def name(self) -> str:
                return f"requires_{self.required_param}"

            def compute(self, df: pd.DataFrame) -> pd.Series:
                return df["close"]
    ''')

    indicator_file = temp_indicators_dir / "requires_args.py"
    indicator_file.write_text(indicator_code)

    info_list = list_indicator_info(temp_indicators_dir)

    # Should fall back to using class name
    assert len(info_list) == 1
    assert info_list[0]["class_name"] == "RequiresArgs"
    assert info_list[0]["name"] == "RequiresArgs"  # Fallback to class name
