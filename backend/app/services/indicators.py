"""Technical indicator library.

Provides built-in indicators (SMA, EMA, RSI, MACD, Bollinger Bands, ATR,
Stochastic Oscillator, VWAP) and an extensible base class for custom indicators.

All indicator functions accept a pandas Series or DataFrame and return a
Series or DataFrame with the computed values.
"""

import inspect
from typing import Callable

import numpy as np
import pandas as pd

# Import Indicator base class from SDK for backward compatibility
from vici_trade_sdk import Indicator


# ── Built-in Indicator Functions ──

def sma(series: pd.Series, period: int) -> pd.Series:
    """Simple Moving Average.

    Args:
        series: Price series (typically close prices).
        period: Number of periods for the moving average.

    Returns:
        Series with SMA values. First (period-1) values will be NaN.
    """
    return series.rolling(window=period, min_periods=period).mean()


def ema(series: pd.Series, period: int) -> pd.Series:
    """Exponential Moving Average.

    Args:
        series: Price series.
        period: Number of periods for the EMA.

    Returns:
        Series with EMA values.
    """
    return series.ewm(span=period, adjust=False).mean()


def rsi(series: pd.Series, period: int = 14) -> pd.Series:
    """Relative Strength Index.

    Uses the standard Wilder smoothing method (exponential moving average
    of gains and losses).

    Args:
        series: Price series (typically close prices).
        period: Lookback period (default 14).

    Returns:
        Series with RSI values between 0 and 100.
    """
    delta = series.diff()
    gains = delta.where(delta > 0, 0.0)
    losses = (-delta).where(delta < 0, 0.0)

    avg_gain = gains.ewm(alpha=1.0 / period, min_periods=period, adjust=False).mean()
    avg_loss = losses.ewm(alpha=1.0 / period, min_periods=period, adjust=False).mean()

    rs = avg_gain / avg_loss
    result = 100.0 - (100.0 / (1.0 + rs))
    return result


def macd(series: pd.Series, fast_period: int = 12,
         slow_period: int = 26,
         signal_period: int = 9) -> pd.DataFrame:
    """Moving Average Convergence Divergence.

    Args:
        series: Price series.
        fast_period: Fast EMA period (default 12).
        slow_period: Slow EMA period (default 26).
        signal_period: Signal line EMA period (default 9).

    Returns:
        DataFrame with columns: macd_line, signal_line, histogram.
    """
    fast_ema = ema(series, fast_period)
    slow_ema = ema(series, slow_period)
    macd_line = fast_ema - slow_ema
    signal_line = ema(macd_line, signal_period)
    histogram = macd_line - signal_line

    return pd.DataFrame({
        "macd_line": macd_line,
        "signal_line": signal_line,
        "histogram": histogram,
    }, index=series.index)


def bollinger_bands(series: pd.Series, period: int = 20,
                    num_std: float = 2.0) -> pd.DataFrame:
    """Bollinger Bands.

    Args:
        series: Price series.
        period: Moving average period (default 20).
        num_std: Number of standard deviations for bands (default 2.0).

    Returns:
        DataFrame with columns: upper, middle, lower.
    """
    middle = sma(series, period)
    rolling_std = series.rolling(window=period, min_periods=period).std()
    upper = middle + (rolling_std * num_std)
    lower = middle - (rolling_std * num_std)

    return pd.DataFrame({
        "bb_upper": upper,
        "bb_middle": middle,
        "bb_lower": lower,
    }, index=series.index)


def atr(df: pd.DataFrame, period: int = 14) -> pd.Series:
    """Average True Range.

    Args:
        df: DataFrame with columns: high, low, close.
        period: ATR period (default 14).

    Returns:
        Series with ATR values.
    """
    high = df["high"]
    low = df["low"]
    close = df["close"]
    prev_close = close.shift(1)

    tr1 = high - low
    tr2 = (high - prev_close).abs()
    tr3 = (low - prev_close).abs()

    true_range = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
    return true_range.ewm(alpha=1.0 / period, min_periods=period, adjust=False).mean()


def stochastic_oscillator(df: pd.DataFrame, k_period: int = 14,
                          d_period: int = 3) -> pd.DataFrame:
    """Stochastic Oscillator (%K and %D).

    Args:
        df: DataFrame with columns: high, low, close.
        k_period: Lookback period for %K (default 14).
        d_period: Smoothing period for %D (default 3).

    Returns:
        DataFrame with columns: stoch_k, stoch_d.
    """
    lowest_low = df["low"].rolling(window=k_period, min_periods=k_period).min()
    highest_high = df["high"].rolling(window=k_period, min_periods=k_period).max()

    denominator = highest_high - lowest_low
    # Avoid division by zero when high == low over the window
    stoch_k = ((df["close"] - lowest_low) / denominator.replace(0, np.nan)) * 100
    stoch_d = sma(stoch_k, d_period)

    return pd.DataFrame({
        "stoch_k": stoch_k,
        "stoch_d": stoch_d,
    }, index=df.index)


def vwap(df: pd.DataFrame) -> pd.Series:
    """Volume Weighted Average Price (intraday cumulative).

    Computes the cumulative VWAP from the beginning of the dataset.
    For daily data, this gives a running average price weighted by volume.

    Args:
        df: DataFrame with columns: high, low, close, volume.

    Returns:
        Series with VWAP values.
    """
    typical_price = (df["high"] + df["low"] + df["close"]) / 3.0
    cumulative_tp_vol = (typical_price * df["volume"]).cumsum()
    cumulative_vol = df["volume"].cumsum()
    return cumulative_tp_vol / cumulative_vol


# ── Registry of Built-in Indicators ──

BUILTIN_INDICATORS = {
    "sma": sma,
    "ema": ema,
    "rsi": rsi,
    "macd": macd,
    "bollinger_bands": bollinger_bands,
    "atr": atr,
    "stochastic_oscillator": stochastic_oscillator,
    "vwap": vwap,
}


# ── Custom Indicator Registry ──

# Module-level registry for custom indicators loaded from user workspace
CUSTOM_INDICATORS: dict[str, type[Indicator]] = {}


def register_custom_indicator(name: str, indicator_cls: type[Indicator]) -> None:
    """Register a custom indicator class in the global registry.

    Args:
        name: Identifier for the indicator (typically the class name).
        indicator_cls: The Indicator subclass to register.
    """
    CUSTOM_INDICATORS[name] = indicator_cls


def get_indicator_registry() -> dict[str, type[Indicator] | Callable]:
    """Get unified registry of all available indicators.

    Returns a dictionary containing both built-in indicator functions and
    custom indicator classes. Built-in indicators take priority over custom
    indicators with the same name.

    Returns:
        Dict mapping indicator name to either a function (built-in) or class (custom).
    """
    registry = BUILTIN_INDICATORS.copy()  # Functions
    for name, cls in CUSTOM_INDICATORS.items():
        if name not in registry:
            registry[name] = cls
    return registry


def get_builtin_indicator_source(indicator_name: str) -> str | None:
    """Get source code of a built-in indicator function.

    Args:
        indicator_name: Name of the built-in indicator.

    Returns:
        Source code as string, or None if indicator not found.
    """
    if indicator_name not in BUILTIN_INDICATORS:
        return None

    func = BUILTIN_INDICATORS[indicator_name]
    try:
        return inspect.getsource(func)
    except Exception:
        return None


def compute_indicators(df: pd.DataFrame,
                       indicator_configs: list[dict]) -> pd.DataFrame:
    """Compute multiple indicators and merge them into the DataFrame.

    Supports both built-in indicators (functions) and custom indicators (classes).
    Each config dict specifies an indicator and its parameters.
    Example config: {"name": "sma", "params": {"period": 20}, "column": "close"}

    Args:
        df: OHLCV DataFrame with columns: open, high, low, close, volume.
        indicator_configs: List of indicator configuration dicts.

    Returns:
        New DataFrame with original columns plus computed indicator columns.
    """
    result = df.copy()
    registry = get_indicator_registry()  # Get unified registry

    for config in indicator_configs:
        ind_name = config["name"]
        params = config.get("params", {})

        if ind_name not in registry:
            raise ValueError(f"Unknown indicator: '{ind_name}'")

        indicator_obj = registry[ind_name]

        # Check if custom indicator class or built-in function
        if inspect.isclass(indicator_obj):
            # Custom indicator: instantiate and call compute()
            instance = indicator_obj(**params)
            output = instance.compute(result)
            col_name = instance.name
        else:
            # Built-in function: existing logic
            source_column = config.get("column", "close")
            func = indicator_obj

            # Indicators that need full OHLCV DataFrame
            if ind_name in ("atr", "stochastic_oscillator", "vwap"):
                output = func(result, **params)
            # MACD and Bollinger Bands return DataFrames
            elif ind_name in ("macd", "bollinger_bands"):
                output = func(result[source_column], **params)
            else:
                output = func(result[source_column], **params)

            # Name the column: indicator_param (e.g., sma_20)
            param_suffix = "_".join(str(v) for v in params.values())
            col_name = f"{ind_name}_{param_suffix}" if param_suffix else ind_name

        # Merge output into result
        if isinstance(output, pd.DataFrame):
            for col in output.columns:
                result[col] = output[col]
        else:
            result[col_name] = output

    return result
