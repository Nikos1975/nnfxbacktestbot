from __future__ import annotations

import pandas as pd


def resample_ohlcv(df: pd.DataFrame, rule: str) -> pd.DataFrame:
    indexed = df.set_index("timestamp")
    output = indexed.resample(rule).agg(
        {"open": "first", "high": "max", "low": "min", "close": "last", "volume": "sum"}
    )
    return output.dropna().reset_index()
