"""Tests for the indicator library."""

import numpy as np
import pandas as pd
import pytest

from app.services.indicators import (
    Indicator,
    atr,
    bollinger_bands,
    compute_indicators,
    ema,
    macd,
    rsi,
    sma,
    stochastic_oscillator,
    vwap,
)


@pytest.fixture
def price_series():
    """Simple ascending price series for indicator testing."""
    return pd.Series(
        [100, 102, 101, 103, 105, 104, 106, 108, 107, 109,
         110, 112, 111, 113, 115, 114, 116, 118, 117, 119],
        dtype=float,
    )


@pytest.fixture
def ohlcv_df():
    """OHLCV DataFrame for indicators that need full data."""
    np.random.seed(42)
    n = 50
    close = 100 + np.cumsum(np.random.randn(n))
    return pd.DataFrame({
        "open": close - np.random.rand(n) * 0.5,
        "high": close + np.abs(np.random.randn(n)) * 0.5,
        "low": close - np.abs(np.random.randn(n)) * 0.5,
        "close": close,
        "volume": np.random.randint(100000, 1000000, n),
    })


class TestSMA:
    def test_sma_basic(self, price_series):
        result = sma(price_series, period=5)
        assert len(result) == len(price_series)
        # First 4 should be NaN
        assert result.iloc[:4].isna().all()
        # 5th should be average of first 5 values
        expected = np.mean([100, 102, 101, 103, 105])
        assert abs(result.iloc[4] - expected) < 0.01

    def test_sma_all_same(self):
        series = pd.Series([50.0] * 20)
        result = sma(series, period=5)
        assert all(result.dropna() == 50.0)


class TestEMA:
    def test_ema_length(self, price_series):
        result = ema(price_series, period=5)
        assert len(result) == len(price_series)
        # EMA should not have NaN values (uses adjust=False)
        assert not result.isna().any()

    def test_ema_responds_faster_than_sma(self, price_series):
        ema_result = ema(price_series, period=10)
        sma_result = sma(price_series, period=10)
        # For an uptrending series, EMA should be above SMA at the end
        assert ema_result.iloc[-1] >= sma_result.iloc[-1] - 1


class TestRSI:
    def test_rsi_range(self, price_series):
        result = rsi(price_series, period=14)
        valid = result.dropna()
        assert all(valid >= 0)
        assert all(valid <= 100)

    def test_rsi_overbought_for_rising(self):
        # Consistently rising prices should give high RSI
        rising = pd.Series([100 + i * 2.0 for i in range(30)])
        result = rsi(rising, period=14)
        assert result.iloc[-1] > 70


class TestMACD:
    def test_macd_columns(self, price_series):
        result = macd(price_series)
        assert "macd_line" in result.columns
        assert "signal_line" in result.columns
        assert "histogram" in result.columns

    def test_histogram_is_difference(self, price_series):
        result = macd(price_series)
        diff = result["macd_line"] - result["signal_line"]
        np.testing.assert_allclose(result["histogram"], diff, atol=1e-10)


class TestBollingerBands:
    def test_bb_columns(self, price_series):
        result = bollinger_bands(price_series, period=10)
        assert "bb_upper" in result.columns
        assert "bb_middle" in result.columns
        assert "bb_lower" in result.columns

    def test_upper_above_middle_above_lower(self, price_series):
        result = bollinger_bands(price_series, period=10)
        valid = result.dropna()
        assert all(valid["bb_upper"] >= valid["bb_middle"])
        assert all(valid["bb_middle"] >= valid["bb_lower"])


class TestATR:
    def test_atr_positive(self, ohlcv_df):
        result = atr(ohlcv_df, period=14)
        valid = result.dropna()
        assert all(valid > 0)

    def test_atr_length(self, ohlcv_df):
        result = atr(ohlcv_df, period=14)
        assert len(result) == len(ohlcv_df)


class TestStochasticOscillator:
    def test_stoch_columns(self, ohlcv_df):
        result = stochastic_oscillator(ohlcv_df)
        assert "stoch_k" in result.columns
        assert "stoch_d" in result.columns

    def test_stoch_range(self, ohlcv_df):
        result = stochastic_oscillator(ohlcv_df)
        valid_k = result["stoch_k"].dropna()
        assert all(valid_k >= 0)
        assert all(valid_k <= 100)


class TestVWAP:
    def test_vwap_positive(self, ohlcv_df):
        result = vwap(ohlcv_df)
        assert all(result > 0)

    def test_vwap_within_price_range(self, ohlcv_df):
        result = vwap(ohlcv_df)
        # VWAP should be between global min low and max high
        assert result.iloc[-1] >= ohlcv_df["low"].min() * 0.9
        assert result.iloc[-1] <= ohlcv_df["high"].max() * 1.1


class TestComputeIndicators:
    def test_compute_multiple_indicators(self, ohlcv_df):
        configs = [
            {"name": "sma", "params": {"period": 10}},
            {"name": "rsi", "params": {"period": 14}},
            {"name": "macd"},
        ]
        result = compute_indicators(ohlcv_df, configs)
        assert "sma_10" in result.columns
        assert "rsi_14" in result.columns
        assert "macd_line" in result.columns

    def test_unknown_indicator_raises(self, ohlcv_df):
        configs = [{"name": "unknown_indicator"}]
        with pytest.raises(ValueError, match="Unknown indicator"):
            compute_indicators(ohlcv_df, configs)

    def test_original_columns_preserved(self, ohlcv_df):
        configs = [{"name": "sma", "params": {"period": 5}}]
        result = compute_indicators(ohlcv_df, configs)
        for col in ["open", "high", "low", "close", "volume"]:
            assert col in result.columns


class TestCustomIndicator:
    def test_custom_indicator_subclass(self):
        class MidPrice(Indicator):
            @property
            def name(self):
                return "mid_price"

            def compute(self, df):
                return (df["high"] + df["low"]) / 2

        indicator = MidPrice()
        assert indicator.name == "mid_price"

        df = pd.DataFrame({
            "high": [110.0, 115.0],
            "low": [100.0, 105.0],
            "close": [105.0, 110.0],
            "open": [102.0, 108.0],
            "volume": [1000, 1000],
        })
        result = indicator.compute(df)
        assert list(result) == [105.0, 110.0]
