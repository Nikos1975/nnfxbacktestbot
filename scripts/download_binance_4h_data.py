from __future__ import annotations

import time
from pathlib import Path
from typing import Iterable

import pandas as pd
import requests


BINANCE_BASE_URL = "https://api.binance.com/api/v3/klines"

ROOT = Path(r"D:\_projects\trading")
OUT_DIR = ROOT / "data" / "nnfx_crypto" / "processed"
OUT_DIR.mkdir(parents=True, exist_ok=True)

PAIRS = {
    "BTC-USDT": "BTCUSDT",
    "ETH-USDT": "ETHUSDT",
    "SOL-USDT": "SOLUSDT",
}

INTERVAL = "4h"
START = "2018-01-01"
END = "2026-05-09"


def to_ms(value: str) -> int:
    return int(pd.Timestamp(value, tz="UTC").timestamp() * 1000)


def fetch_klines(symbol: str, interval: str, start_ms: int, end_ms: int) -> list[list]:
    rows: list[list] = []
    current = start_ms

    while current < end_ms:
        params = {
            "symbol": symbol,
            "interval": interval,
            "startTime": current,
            "endTime": end_ms,
            "limit": 1000,
        }

        response = requests.get(BINANCE_BASE_URL, params=params, timeout=30)
        response.raise_for_status()

        batch = response.json()

        if not batch:
            break

        rows.extend(batch)

        last_open_time = batch[-1][0]
        next_time = last_open_time + 1

        if next_time <= current:
            break

        current = next_time

        print(f"{symbol} {interval}: downloaded {len(rows)} rows...", flush=True)

        time.sleep(0.15)

    return rows


def klines_to_df(rows: Iterable[list]) -> pd.DataFrame:
    columns = [
        "timestamp",
        "open",
        "high",
        "low",
        "close",
        "volume",
        "close_time",
        "quote_asset_volume",
        "number_of_trades",
        "taker_buy_base_asset_volume",
        "taker_buy_quote_asset_volume",
        "ignore",
    ]

    df = pd.DataFrame(rows, columns=columns)

    df["timestamp"] = pd.to_datetime(df["timestamp"], unit="ms", utc=True)

    numeric_cols = ["open", "high", "low", "close", "volume"]
    for col in numeric_cols:
        df[col] = pd.to_numeric(df[col], errors="coerce")

    df = df[["timestamp", "open", "high", "low", "close", "volume"]]
    df = df.dropna()
    df = df.drop_duplicates(subset=["timestamp"])
    df = df.sort_values("timestamp").reset_index(drop=True)

    return df


def validate_4h(df: pd.DataFrame, pair: str) -> None:
    if df.empty:
        raise ValueError(f"{pair}: downloaded dataframe is empty")

    if df["timestamp"].duplicated().any():
        raise ValueError(f"{pair}: duplicate timestamps found")

    diffs = df["timestamp"].diff().dropna()
    expected = pd.Timedelta(hours=4)

    bad_gaps = diffs[diffs != expected]

    print()
    print(f"{pair} validation")
    print(f"Rows: {len(df)}")
    print(f"Start: {df['timestamp'].iloc[0]}")
    print(f"End:   {df['timestamp'].iloc[-1]}")
    print(f"Duplicate timestamps: {df['timestamp'].duplicated().sum()}")
    print(f"Non-4h gaps: {len(bad_gaps)}")

    if len(bad_gaps) > 0:
        print("First non-4h gaps:")
        print(bad_gaps.head(10))


def main() -> None:
    start_ms = to_ms(START)
    end_ms = to_ms(END)

    for pair, symbol in PAIRS.items():
        print()
        print("=" * 80)
        print(f"Downloading {pair} {INTERVAL}")
        print("=" * 80)

        rows = fetch_klines(symbol, INTERVAL, start_ms, end_ms)
        df = klines_to_df(rows)
        validate_4h(df, pair)

        out_path = OUT_DIR / f"{pair}_{INTERVAL}.csv"
        df.to_csv(out_path, index=False)

        print(f"Saved: {out_path}")


if __name__ == "__main__":
    main()
