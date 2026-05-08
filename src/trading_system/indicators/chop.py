from __future__ import annotations

import numpy as np
import pandas as pd

from trading_system.indicators.atr import atr


def chop(df: pd.DataFrame, period: int = 14) -> pd.Series:
    atr_1 = atr(df, 1)
    atr_sum = atr_1.rolling(period, min_periods=period).sum()

    high = pd.to_numeric(df["high"], errors="coerce")
    low = pd.to_numeric(df["low"], errors="coerce")

    high_max = high.rolling(period, min_periods=period).max()
    low_min = low.rolling(period, min_periods=period).min()

    denom = (high_max - low_min).replace(0, np.nan).astype(float)

    result = 100.0 * np.log10(atr_sum / denom) / np.log10(period)
    return pd.to_numeric(result, errors="coerce")