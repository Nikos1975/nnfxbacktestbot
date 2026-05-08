from __future__ import annotations

import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Literal

import pandas as pd
import typer
import requests
from rich.console import Console

app = typer.Typer()
console = Console()

Market = Literal["spot", "futures"]

BASE_URLS: dict[str, str] = {
    "spot": "https://api.binance.com/api/v3/klines",
    "futures": "https://fapi.binance.com/fapi/v1/klines",
}

INTERVAL_MS: dict[str, int] = {
    "1m": 60_000,
    "3m": 3 * 60_000,
    "5m": 5 * 60_000,
    "15m": 15 * 60_000,
    "30m": 30 * 60_000,
    "1h": 60 * 60_000,
    "2h": 2 * 60 * 60_000,
    "4h": 4 * 60 * 60_000,
    "6h": 6 * 60 * 60_000,
    "8h": 8 * 60 * 60_000,
    "12h": 12 * 60 * 60_000,
    "1d": 24 * 60 * 60_000,
}


def parse_date_to_ms(value: str) -> int:
    dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return int(dt.timestamp() * 1000)


def fetch_klines(
    market: Market,
    symbol: str,
    interval: str,
    start_ms: int,
    end_ms: int,
    limit: int = 1000,
) -> list[list]:
    url = BASE_URLS[market]
    params = {
        "symbol": symbol.upper(),
        "interval": interval,
        "startTime": start_ms,
        "endTime": end_ms,
        "limit": limit,
    }

    response = requests.get(url, params=params, timeout=30)

    if response.status_code in {418, 429}:
        retry_after = int(response.headers.get("Retry-After", "10"))
        raise RuntimeError(
            f"Binance rate limit / ban response {response.status_code}. "
            f"Retry after {retry_after} seconds."
        )

    response.raise_for_status()
    data = response.json()

    if not isinstance(data, list):
        raise RuntimeError(f"Unexpected Binance response: {data}")

    return data


@app.command()
def main(
    market: Market = typer.Option("spot", help="spot or futures"),
    symbol: str = typer.Option("BTCUSDT", help="Example: BTCUSDT"),
    interval: str = typer.Option("1h", help="Example: 1m, 5m, 15m, 1h, 4h, 1d"),
    start: str = typer.Option(..., help="UTC start date, e.g. 2024-01-01"),
    end: str = typer.Option(..., help="UTC end date, e.g. 2025-01-01"),
    out: Path = typer.Option(..., help="Output CSV path"),
    sleep_seconds: float = typer.Option(0.25, help="Pause between API calls"),
):
    if interval not in INTERVAL_MS:
        raise typer.BadParameter(f"Unsupported interval: {interval}")

    start_ms = parse_date_to_ms(start)
    end_ms = parse_date_to_ms(end)

    if end_ms <= start_ms:
        raise typer.BadParameter("end must be after start")

    rows: list[list] = []
    current_ms = start_ms

    console.print(
        f"Downloading {market} {symbol.upper()} {interval} "
        f"from {start} to {end}"
    )

    while current_ms < end_ms:
        batch = fetch_klines(
            market=market,
            symbol=symbol,
            interval=interval,
            start_ms=current_ms,
            end_ms=end_ms,
            limit=1000,
        )

        if not batch:
            break

        rows.extend(batch)

        last_open_time = int(batch[-1][0])
        next_ms = last_open_time + INTERVAL_MS[interval]

        if next_ms <= current_ms:
            raise RuntimeError("Pagination stopped advancing. Aborting.")

        current_ms = next_ms

        console.print(f"Downloaded rows: {len(rows)}", end="\r")
        time.sleep(sleep_seconds)

    if not rows:
        raise RuntimeError("No Binance candles downloaded.")

    raw = pd.DataFrame(
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

    df = pd.DataFrame(
        {
            "timestamp": pd.to_datetime(raw["open_time"], unit="ms", utc=True),
            "open": pd.to_numeric(raw["open"]),
            "high": pd.to_numeric(raw["high"]),
            "low": pd.to_numeric(raw["low"]),
            "close": pd.to_numeric(raw["close"]),
            "volume": pd.to_numeric(raw["volume"]),
        }
    )

    df = df.drop_duplicates("timestamp").sort_values("timestamp").reset_index(drop=True)

    out.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(out, index=False)

    console.print()
    console.print(f"[green]Saved:[/green] {out}")
    console.print(f"Rows: {len(df)}")
    console.print(f"Start: {df.iloc[0]['timestamp']}")
    console.print(f"End: {df.iloc[-1]['timestamp']}")


if __name__ == "__main__":
    app()