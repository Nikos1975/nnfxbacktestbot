from pathlib import Path
import pandas as pd

REQUIRED_COLUMNS = {"timestamp", "open", "high", "low", "close", "volume"}

def load_ohlcv_csv(path: Path) -> pd.DataFrame:
    df = pd.read_csv(path)
    missing = REQUIRED_COLUMNS - set(df.columns)
    if missing:
        raise ValueError(f"Missing OHLCV columns: {sorted(missing)}")

    df = df.copy()
    df["timestamp"] = pd.to_datetime(df["timestamp"], utc=True, errors="coerce")
    if df["timestamp"].isna().any():
        raise ValueError("Invalid timestamp values found.")

    for col in ["open", "high", "low", "close", "volume"]:
        df[col] = pd.to_numeric(df[col], errors="coerce")
    if df[["open", "high", "low", "close", "volume"]].isna().any().any():
        raise ValueError("Invalid numeric OHLCV values found.")

    df = df.sort_values("timestamp").drop_duplicates("timestamp")
    return df.reset_index(drop=True)
