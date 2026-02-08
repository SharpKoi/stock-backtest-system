"""Base class for custom technical indicators.

This module provides the Indicator abstract base class that users extend
to create custom technical indicators for their trading strategies.
"""

from abc import ABC, abstractmethod

import pandas as pd


class Indicator(ABC):
    """Base class for user-defined custom indicators.

    To create a custom indicator:
    1. Subclass this class
    2. Implement the `name` property to return your indicator's name
    3. Implement the `compute()` method with your calculation logic

    Example:
        class WilliamsR(Indicator):
            def __init__(self, period: int = 14):
                self.period = period

            @property
            def name(self) -> str:
                return f"williams_r_{self.period}"

            def compute(self, df: pd.DataFrame) -> pd.Series:
                highest_high = df['high'].rolling(window=self.period).max()
                lowest_low = df['low'].rolling(window=self.period).min()
                return -100 * (highest_high - df['close']) / (highest_high - lowest_low)
    """

    @property
    @abstractmethod
    def name(self) -> str:
        """Return the indicator name used as a column label.

        This name will be used as the DataFrame column name when the
        indicator is computed and added to the price data.

        Returns:
            A string identifier for this indicator (e.g., "williams_r_14")
        """

    @abstractmethod
    def compute(self, df: pd.DataFrame) -> pd.Series:
        """Compute the indicator from OHLCV data.

        Args:
            df: DataFrame with columns: open, high, low, close, volume.
                This is the full price history available at the current bar.

        Returns:
            A pandas Series with the indicator values, same index as df.
            The series should have the same length as the input DataFrame.
        """
