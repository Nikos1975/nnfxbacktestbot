from __future__ import annotations

import json
import time
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import urlopen

import pandas as pd


SYMBOL = "BTCUSDT"
PAIR = "BTC-USDT"
INTERVAL = "1d"

RAW_PATH = Path("data/raw/binance/spot/BTCUSDT/1d.csv")
PROCESSED_PATH = Path("data/nnfx_crypto/processed/BTC-USDT_1d.csv")

BASE_URL = "https://api.binance.com/api/v3/klines"


def to_ms(ts: pd.Timestamp) -> int:
    """Convert pandas timestamp to milliseconds."""
    return int(ts.timestamp() * 1000)


def fetch_klines(start_ms: int, end_ms: int | None = None) -> list[list]:
    """Fetch Binance Spot klines."""
    params = {
        "symbol": SYMBOL,
        "interval": INTERVAL,
        "startTime": start_ms,
        "limit": 1000,
    }

    if end_ms is not None:
        params["endTime"] = end_ms

    url = BASE_URL + "?" + urlencode(params)

    try:
        with urlopen(url, timeout=30) as response:
            raw_data = response.read()
    except HTTPError as exc:
        raise RuntimeError(f"HTTP error while calling Binance: {exc.code} {exc.reason}\nURL: {url}") from exc
    except URLError as exc:
        raise RuntimeError(f"Network error while calling Binance: {exc.reason}\nURL: {url}") from exc

    try:
        parsed = json.loads(raw_data.decode("utf-8"))
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"Could not parse Binance response as JSON.\nURL: {url}") from exc

    if isinstance(parsed, dict):
        raise RuntimeError(f"Binance API error: {parsed}\nURL: {url}")

    if not isinstance(parsed, list):
        raise RuntimeError(f"Unexpected Binance response type: {type(parsed)}\nURL: {url}")

    return parsed


def normalize_klines(rows: list[list]) -> pd.DataFrame:
    """Normalize Binance kline rows to the project's OHLCV format."""
    if not rows:
        return pd.DataFrame(columns=["timestamp", "open", "high", "low", "close", "volume"])

    df = pd.DataFrame(
        rows,
        columns=[
            "open_time",
            "open",
            "high",
            "low",
            "close",
            "volume",
            "close_time",
            "quote_asset_volume",
            "number_of_trades",
            "taker_buy_base_volume",
            "taker_buy_quote_volume",
            "ignore",
        ],
    )

    out = pd.DataFrame()
    out["timestamp"] = pd.to_datetime(df["open_time"], unit="ms", utc=True)
    out["open"] = df["open"].astype(float)
    out["high"] = df["high"].astype(float)
    out["low"] = df["low"].astype(float)
    out["close"] = df["close"].astype(float)
    out["volume"] = df["volume"].astype(float)

    return out


def count_missing_daily_gaps(df: pd.DataFrame) -> int:
    """Count missing daily gaps in a timestamp-sorted dataframe."""
    if df.empty or len(df) < 2:
        return 0

    timestamps = pd.to_datetime(df["timestamp"], utc=True).sort_values()
    diffs = timestamps.diff().dropna()

    return int((diffs > pd.Timedelta(days=1)).sum())


def main() -> None:
    if not PROCESSED_PATH.exists():
        raise FileNotFoundError(f"Missing processed file: {PROCESSED_PATH}")

    existing = pd.read_csv(PROCESSED_PATH)
    existing["timestamp"] = pd.to_datetime(existing["timestamp"], utc=True)

    existing = existing[["timestamp", "open", "high", "low", "close", "volume"]]
    existing = existing.sort_values("timestamp").drop_duplicates("timestamp")

    rows_before = len(existing)
    duplicates_before = int(existing["timestamp"].duplicated().sum())
    gaps_before = count_missing_daily_gaps(existing)

    last_ts = existing["timestamp"].max()
    start_ts = last_ts + pd.Timedelta(days=1)

    now_utc = pd.Timestamp.now(tz="UTC")
    today_utc_midnight = now_utc.normalize()

    print(f"Symbol:                   {SYMBOL}")
    print(f"Pair:                     {PAIR}")
    print(f"Interval:                 {INTERVAL}")
    print(f"Existing rows:            {rows_before}")
    print(f"Duplicate timestamps:     {duplicates_before}")
    print(f"Missing daily gaps:       {gaps_before}")
    print(f"Last existing timestamp:  {last_ts}")
    print(f"Download start timestamp: {start_ts}")
    print(f"Today UTC midnight:       {today_utc_midnight}")
    print("")

    if start_ts > today_utc_midnight:
        print("Already up to date.")
        return

    all_new: list[pd.DataFrame] = []
    current = start_ts

    while current <= today_utc_midnight:
        rows = fetch_klines(to_ms(current))

        if not rows:
            print("No rows returned from Binance.")
            break

        new_df = normalize_klines(rows)

        if new_df.empty:
            print("Normalized dataframe is empty.")
            break

        # Keep only rows from the required update range.
        new_df = new_df[new_df["timestamp"] >= start_ts]
        new_df = new_df[new_df["timestamp"] <= today_utc_midnight]

        if new_df.empty:
            print("No new rows inside requested date range.")
            break

        all_new.append(new_df)

        last_downloaded = new_df["timestamp"].max()
        print(f"Downloaded through:       {last_downloaded}")

        next_current = last_downloaded + pd.Timedelta(days=1)

        if next_current <= current:
            print("Stopping because download cursor did not advance.")
            break

        current = next_current
        time.sleep(0.25)

    if not all_new:
        print("No new rows downloaded.")
        return

    downloaded = pd.concat(all_new, ignore_index=True)
    downloaded["timestamp"] = pd.to_datetime(downloaded["timestamp"], utc=True)

    combined = pd.concat([existing, downloaded], ignore_index=True)
    combined["timestamp"] = pd.to_datetime(combined["timestamp"], utc=True)

    combined = combined.sort_values("timestamp").drop_duplicates("timestamp", keep="last")
    combined = combined[["timestamp", "open", "high", "low", "close", "volume"]]

    rows_after = len(combined)
    duplicates_after = int(combined["timestamp"].duplicated().sum())
    gaps_after = count_missing_daily_gaps(combined)

    RAW_PATH.parent.mkdir(parents=True, exist_ok=True)
    PROCESSED_PATH.parent.mkdir(parents=True, exist_ok=True)

    combined.to_csv(RAW_PATH, index=False)
    combined.to_csv(PROCESSED_PATH, index=False)

    print("")
    print("Update complete.")
    print(f"Rows before:              {rows_before}")
    print(f"Rows downloaded:          {len(downloaded)}")
    print(f"Rows after:               {rows_after}")
    print(f"Rows added net:           {rows_after - rows_before}")
    print(f"First row:                {combined['timestamp'].min()}")
    print(f"Last row:                 {combined['timestamp'].max()}")
    print(f"Duplicate timestamps:     {duplicates_after}")
    print(f"Missing daily gaps:       {gaps_after}")
    print(f"Columns:                  {', '.join(combined.columns)}")
    print(f"Saved raw:                {RAW_PATH}")
    print(f"Saved processed:          {PROCESSED_PATH}")


if __name__ == "__main__":
    main()