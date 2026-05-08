from __future__ import annotations

from dataclasses import dataclass, asdict
from pathlib import Path

import pandas as pd
import typer
from rich.console import Console
from rich.table import Table

from trading_system.data.load_ohlcv import load_ohlcv_csv

app = typer.Typer()
console = Console()

REQUIRED_COLUMNS = ["timestamp", "open", "high", "low", "close", "volume"]

INTERVAL_TO_PANDAS_FREQ: dict[str, str] = {
    "1m": "1min",
    "3m": "3min",
    "5m": "5min",
    "15m": "15min",
    "30m": "30min",
    "1h": "1h",
    "2h": "2h",
    "4h": "4h",
    "6h": "6h",
    "8h": "8h",
    "12h": "12h",
    "1d": "1D",
}


@dataclass
class ValidationResult:
    path: str
    rows: int
    start: str
    end: str
    duplicate_timestamps: int
    missing_candles: int
    invalid_ohlc_rows: int
    non_positive_price_rows: int
    negative_volume_rows: int
    nan_rows: int
    passed: bool

    def to_dict(self) -> dict:
        return asdict(self)


def validate_ohlcv_dataframe(
    df: pd.DataFrame,
    path: Path,
    interval: str,
) -> ValidationResult:
    if interval not in INTERVAL_TO_PANDAS_FREQ:
        raise ValueError(f"Unsupported interval: {interval}")

    if df.empty:
        raise ValueError(f"OHLCV file has no rows: {path}")

    missing_columns = [col for col in REQUIRED_COLUMNS if col not in df.columns]
    if missing_columns:
        raise ValueError(f"Missing required columns: {missing_columns}")

    duplicate_timestamps = int(df["timestamp"].duplicated().sum())

    df_sorted = df.sort_values("timestamp").reset_index(drop=True)

    non_monotonic = not df_sorted["timestamp"].is_monotonic_increasing
    if non_monotonic:
        raise ValueError("Timestamps are not monotonic increasing after sorting.")

    freq = INTERVAL_TO_PANDAS_FREQ[interval]
    expected_index = pd.date_range(
        start=df_sorted["timestamp"].iloc[0],
        end=df_sorted["timestamp"].iloc[-1],
        freq=freq,
    )

    actual_index = pd.DatetimeIndex(df_sorted["timestamp"])
    missing_candles = int(len(expected_index.difference(actual_index)))

    invalid_ohlc_rows = int(
        (
            (df_sorted["high"] < df_sorted["low"])
            | (df_sorted["high"] < df_sorted["open"])
            | (df_sorted["high"] < df_sorted["close"])
            | (df_sorted["low"] > df_sorted["open"])
            | (df_sorted["low"] > df_sorted["close"])
        ).sum()
    )

    non_positive_price_rows = int(
        (
            (df_sorted["open"] <= 0)
            | (df_sorted["high"] <= 0)
            | (df_sorted["low"] <= 0)
            | (df_sorted["close"] <= 0)
        ).sum()
    )

    negative_volume_rows = int((df_sorted["volume"] < 0).sum())

    nan_rows = int(df_sorted[REQUIRED_COLUMNS].isna().any(axis=1).sum())

    passed = all(
        [
            duplicate_timestamps == 0,
            missing_candles == 0,
            invalid_ohlc_rows == 0,
            non_positive_price_rows == 0,
            negative_volume_rows == 0,
            nan_rows == 0,
        ]
    )

    return ValidationResult(
        path=str(path),
        rows=len(df_sorted),
        start=str(df_sorted["timestamp"].iloc[0]),
        end=str(df_sorted["timestamp"].iloc[-1]),
        duplicate_timestamps=duplicate_timestamps,
        missing_candles=missing_candles,
        invalid_ohlc_rows=invalid_ohlc_rows,
        non_positive_price_rows=non_positive_price_rows,
        negative_volume_rows=negative_volume_rows,
        nan_rows=nan_rows,
        passed=passed,
    )


def print_validation_result(result: ValidationResult) -> None:
    table = Table(title="OHLCV Validation")

    table.add_column("Check")
    table.add_column("Value")

    for key, value in result.to_dict().items():
        table.add_row(key, str(value))

    console.print(table)

    if result.passed:
        console.print("[green]Validation passed.[/green]")
    else:
        console.print("[red]Validation failed.[/red]")


@app.command()
def main(
    data: Path = typer.Option(..., help="CSV with timestamp,open,high,low,close,volume"),
    interval: str = typer.Option("1h", help="Expected candle interval, e.g. 1h, 4h, 1d"),
    strict: bool = typer.Option(True, help="Exit with error if validation fails"),
):
    df = load_ohlcv_csv(data)
    result = validate_ohlcv_dataframe(df=df, path=data, interval=interval)
    print_validation_result(result)

    if strict and not result.passed:
        raise typer.Exit(code=1)


if __name__ == "__main__":
    app()