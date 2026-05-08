from __future__ import annotations

import pandas as pd


REQUIRED_OHLCV_COLUMNS = ["timestamp", "open", "high", "low", "close", "volume"]


def validate_ohlcv(df: pd.DataFrame) -> pd.DataFrame:
    missing = [column for column in REQUIRED_OHLCV_COLUMNS if column not in df.columns]
    if missing:
        raise ValueError(f"OHLCV data missing columns: {', '.join(missing)}")

    output = df.copy()
    output["timestamp"] = pd.to_datetime(output["timestamp"], utc=False)
    output = output.sort_values("timestamp").reset_index(drop=True)
    if output["timestamp"].duplicated().any():
        raise ValueError("OHLCV data contains duplicate timestamps")
    if output[REQUIRED_OHLCV_COLUMNS].isna().any().any():
        raise ValueError("OHLCV data contains missing values")
    for column in ["open", "high", "low", "close", "volume"]:
        output[column] = pd.to_numeric(output[column], errors="raise")
    return output
