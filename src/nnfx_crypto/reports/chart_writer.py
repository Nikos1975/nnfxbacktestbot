from __future__ import annotations

from pathlib import Path

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import pandas as pd


def write_price_signal_chart(
    frame: pd.DataFrame,
    path: str | Path,
    trades: pd.DataFrame | None = None,
) -> None:
    fig, ax = plt.subplots(figsize=(10, 4))
    ax.plot(frame["timestamp"], frame["close"], label="Close", linewidth=1)
    if "baseline_value" in frame.columns:
        ax.plot(frame["timestamp"], frame["baseline_value"], label="FRAMA", linewidth=1)
    if trades is not None and not trades.empty:
        entry_times = pd.to_datetime(trades["entry_time"], errors="coerce")
        exit_times = pd.to_datetime(trades["exit_time"], errors="coerce")
        ax.scatter(entry_times, trades["entry_price"], marker="^", label="Entry", s=40)
        ax.scatter(exit_times, trades["exit_price"], marker="v", label="Exit", s=40)
    ax.set_title("Price and Signals")
    ax.legend(loc="best")
    fig.autofmt_xdate()
    fig.tight_layout()
    fig.savefig(path)
    plt.close(fig)


def write_equity_curve_chart(equity_curve: pd.DataFrame, path: str | Path) -> None:
    fig, ax = plt.subplots(figsize=(10, 4))
    ax.plot(equity_curve["timestamp"], equity_curve["equity"], label="Equity", linewidth=1)
    ax.set_title("Equity Curve")
    ax.legend(loc="best")
    fig.autofmt_xdate()
    fig.tight_layout()
    fig.savefig(path)
    plt.close(fig)
