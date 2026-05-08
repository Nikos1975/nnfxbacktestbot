from pathlib import Path

import pandas as pd

from nnfx_crypto.backtest.event_backtester import EventBacktester
from nnfx_crypto.config.loader import load_strategy_config

from tests.test_nnfx_backtester_basic import write_config, write_ohlcv_csv


def test_backtester_applies_data_start_end_filters(tmp_path: Path):
    csv_path = tmp_path / "BTC-USDT_1h.csv"
    config_path = tmp_path / "strategy.yml"
    output_root = tmp_path / "results"
    write_ohlcv_csv(csv_path, rows=120)
    write_config(config_path, csv_path, output_root)
    text = config_path.read_text(encoding="utf-8")
    text = text.replace(
        f"path: {csv_path.as_posix()}",
        f"path: {csv_path.as_posix()}\n  start: '2024-01-02 00:00:00'\n  end: '2024-01-03 00:00:00'",
    )
    config_path.write_text(text, encoding="utf-8")
    config = load_strategy_config(config_path)
    config.backtest.warmup_bars = 0

    result = EventBacktester(config, output_root=output_root).run()
    equity = pd.read_csv(result.run_dir / "equity_curve.csv")

    assert pd.Timestamp(equity["timestamp"].min()) >= pd.Timestamp("2024-01-02 00:00:00")
    assert pd.Timestamp(equity["timestamp"].max()) <= pd.Timestamp("2024-01-03 00:00:00")


def test_backtester_applies_naive_filters_to_utc_timestamps(tmp_path: Path):
    csv_path = tmp_path / "BTC-USDT_1h.csv"
    config_path = tmp_path / "strategy.yml"
    output_root = tmp_path / "results"
    write_ohlcv_csv(csv_path, rows=120)
    df = pd.read_csv(csv_path)
    df["timestamp"] = pd.to_datetime(df["timestamp"]).dt.tz_localize("UTC")
    df.to_csv(csv_path, index=False)
    write_config(config_path, csv_path, output_root)
    text = config_path.read_text(encoding="utf-8")
    text = text.replace(
        f"path: {csv_path.as_posix()}",
        f"path: {csv_path.as_posix()}\n  start: '2024-01-02 00:00:00'\n  end: '2024-01-03 00:00:00'",
    )
    config_path.write_text(text, encoding="utf-8")
    config = load_strategy_config(config_path)
    config.backtest.warmup_bars = 0

    result = EventBacktester(config, output_root=output_root).run()
    equity = pd.read_csv(result.run_dir / "equity_curve.csv")

    assert not equity.empty
