from __future__ import annotations

from pathlib import Path

import pandas as pd
import typer
from rich.console import Console
from rich.table import Table

from trading_system.data.load_ohlcv import load_ohlcv_csv
from trading_system.data.validate_data import INTERVAL_TO_PANDAS_FREQ

app = typer.Typer()
console = Console()


@app.command()
def main(
    data: Path = typer.Option(..., help="CSV with timestamp,open,high,low,close,volume"),
    interval: str = typer.Option(..., help="Expected interval: 1h, 4h, 1d"),
    max_rows: int = typer.Option(100, help="Maximum missing timestamps to print"),
):
    if interval not in INTERVAL_TO_PANDAS_FREQ:
        raise typer.BadParameter(f"Unsupported interval: {interval}")

    df = load_ohlcv_csv(data)
    df = df.sort_values("timestamp").reset_index(drop=True)

    expected = pd.date_range(
        start=df["timestamp"].iloc[0],
        end=df["timestamp"].iloc[-1],
        freq=INTERVAL_TO_PANDAS_FREQ[interval],
    )

    actual = pd.DatetimeIndex(df["timestamp"])
    missing = expected.difference(actual)

    console.print(f"File: {data}")
    console.print(f"Rows: {len(df)}")
    console.print(f"Start: {df['timestamp'].iloc[0]}")
    console.print(f"End: {df['timestamp'].iloc[-1]}")
    console.print(f"Missing candles: {len(missing)}")

    if len(missing) == 0:
        console.print("[green]No missing candles.[/green]")
        return

    table = Table(title="Missing Candle Timestamps")
    table.add_column("#", justify="right")
    table.add_column("timestamp")

    for i, ts in enumerate(missing[:max_rows], start=1):
        table.add_row(str(i), str(ts))

    console.print(table)

    if len(missing) > max_rows:
        console.print(f"[yellow]Only showing first {max_rows} of {len(missing)} missing candles.[/yellow]")


if __name__ == "__main__":
    app()