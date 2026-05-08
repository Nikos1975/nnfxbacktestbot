from __future__ import annotations

import numpy as np
import pandas as pd

from trading_system.indicators.atr import atr


def adx(df: pd.DataFrame, period: int = 14) -> pd.Series:
    high = pd.to_numeric(df["high"], errors="coerce")
    low = pd.to_numeric(df["low"], errors="coerce")

    up_move = high.diff()
    down_move = -low.diff()

    plus_dm = up_move.where((up_move > down_move) & (up_move > 0), 0.0)
    minus_dm = down_move.where((down_move > up_move) & (down_move > 0), 0.0)

    atr_values = atr(df, period).replace(0, np.nan).astype(float)

    plus_di = (
        100.0
        * plus_dm.rolling(period, min_periods=period).sum()
        / atr_values
    )

    minus_di = (
        100.0
        * minus_dm.rolling(period, min_periods=period).sum()
        / atr_values
    )

    denominator = (plus_di + minus_di).replace(0, np.nan).astype(float)

    dx = 100.0 * (plus_di - minus_di).abs() / denominator
    dx = pd.to_numeric(dx, errors="coerce")

    return dx.rolling(period, min_periods=period).mean()