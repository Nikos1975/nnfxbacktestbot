import json
import subprocess
import sys
from pathlib import Path

import numpy as np
import pandas as pd

from nnfx_crypto.backtest.event_backtester import EventBacktester
from nnfx_crypto.config.loader import load_strategy_config


def write_ohlcv_csv(path: Path, rows: int = 90) -> None:
    idx = np.arange(rows, dtype=float)
    close = 100 + idx * 0.15 + np.sin(idx / 3.0)
    df = pd.DataFrame(
        {
            "timestamp": pd.date_range("2024-01-01", periods=rows, freq="h"),
            "open": close - 0.05,
            "high": close + 1.0,
            "low": close - 1.0,
            "close": close,
            "volume": 1000 + idx,
        }
    )
    df.to_csv(path, index=False)


def write_config(path: Path, csv_path: Path, output_root: Path) -> None:
    path.write_text(
        f"""
strategy:
  name: algo5_fractal_rigidity
  mode: backtest
  direction_mode: both
  allow_continuation_trades: false
market:
  connector: binance_perpetual
  trading_pair: BTC-USDT
  timeframe: 1h
  quote_asset: USDT
  base_asset: BTC
data:
  source: csv
  path: {csv_path.as_posix()}
indicators:
  baseline: {{name: frama, params: {{length: 10, fc: 1, sc: 198}}}}
  c1: {{name: reflex, params: {{length: 20}}}}
  c2: {{name: stablefx, params: {{length: 14, signal_length: 5}}}}
  volume_or_volatility_filter: {{name: stiffness, params: {{length: 20, threshold: 50.0}}}}
  exit: {{name: crossroads, params: {{fast_length: 2, slow_length: 24}}}}
risk:
  account_equity: 10000
  risk_per_trade_pct: 0.005
  atr_length: 14
  stop_loss_atr_multiplier: 1.25
  tp1_atr_multiplier: 1.0
  max_open_positions_per_pair: 1
execution:
  fee_pct: 0.0006
  slippage_pct: 0.0005
  use_next_bar_open: true
backtest:
  warmup_bars: 25
  initial_capital: 10000
""",
        encoding="utf-8",
    )
    output_root.mkdir(parents=True, exist_ok=True)


def test_backtester_exports_required_files(tmp_path: Path):
    csv_path = tmp_path / "BTC-USDT_1h.csv"
    config_path = tmp_path / "strategy.yml"
    output_root = tmp_path / "results"
    write_ohlcv_csv(csv_path)
    write_config(config_path, csv_path, output_root)
    config = load_strategy_config(config_path)

    result = EventBacktester(config, output_root=output_root).run()

    for filename in [
        "resolved_config.yml",
        "trades.csv",
        "equity_curve.csv",
        "metrics.json",
        "summary.md",
    ]:
        assert (result.run_dir / filename).exists()

    metrics = json.loads((result.run_dir / "metrics.json").read_text(encoding="utf-8"))
    expected_metrics = {
        "net_pnl",
        "net_pnl_pct",
        "max_drawdown",
        "max_drawdown_pct",
        "profit_factor",
        "expectancy",
        "sharpe_ratio",
        "sortino_ratio",
        "win_rate",
        "total_trades",
        "long_trades",
        "short_trades",
        "average_win",
        "average_loss",
        "largest_win",
        "largest_loss",
        "consecutive_losses",
        "time_in_market",
        "time_underwater",
        "average_trade_duration",
        "fees_paid",
        "slippage_cost",
        "buy_and_hold_return",
        "exposure_by_pair",
        "performance_by_pair",
        "performance_by_timeframe",
        "total_volume",
        "accuracy",
        "close_types",
        "total_executors_with_positions",
        "max_open_positions_per_pair",
    }
    assert expected_metrics.issubset(metrics)

    trades = pd.read_csv(result.run_dir / "trades.csv")
    if not trades.empty:
        assert trades["pair"].eq("BTC-USDT").all()
        assert pd.to_datetime(trades["entry_time"], errors="coerce").notna().all()

    html = (result.run_dir / "report.html").read_text(encoding="utf-8")
    assert "Indicator Source Status" in html
    assert "placeholder" in html
    assert "Close Types" in html


def test_backtest_cli_prints_run_directory(tmp_path: Path):
    csv_path = tmp_path / "BTC-USDT_1h.csv"
    config_path = tmp_path / "strategy.yml"
    output_root = tmp_path / "results"
    write_ohlcv_csv(csv_path)
    write_config(config_path, csv_path, output_root)

    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "nnfx_crypto.backtest.run",
            "--config",
            str(config_path),
            "--output-root",
            str(output_root),
        ],
        cwd=Path.cwd(),
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    assert str(output_root) in result.stdout
    assert "report.html" in {path.name for path in next(output_root.iterdir()).iterdir()}


def test_backtester_records_tp1_half_close(tmp_path: Path):
    rows = []
    prices = [100, 101, 102, 103, 104, 105, 108, 109]
    for index, close in enumerate(prices):
        rows.append(
            {
                "timestamp": pd.Timestamp("2024-01-01") + pd.Timedelta(hours=index),
                "open": close,
                "high": close + 1.5,
                "low": close - 0.5,
                "close": close,
                "volume": 1000,
                "atr": 1.0,
                "baseline_signal": 1 if index >= 2 else 0,
                "c1_signal": 1 if index == 2 else 0,
                "c2_signal": 1,
                "filter_pass_long": True,
                "filter_pass_short": True,
                "exit_signal": 0,
            }
        )
    frame = pd.DataFrame(rows)
    csv_path = tmp_path / "BTC-USDT_1h.csv"
    config_path = tmp_path / "strategy.yml"
    output_root = tmp_path / "results"
    write_ohlcv_csv(csv_path)
    write_config(config_path, csv_path, output_root)
    config = load_strategy_config(config_path)
    config.backtest.warmup_bars = 0

    class StubEngine:
        def __init__(self, _config):
            pass

        def compute_indicators(self, _raw):
            return frame

        def evaluate_bar(self, data, row_index, has_open_position=False, open_position_side=None):
            if not has_open_position and row_index == 2:
                from nnfx_crypto.signals.signal_types import TradeIntent

                return TradeIntent("entry", "long", "test_entry", row_index, data.iloc[row_index]["timestamp"])
            return None

    import nnfx_crypto.backtest.event_backtester as event_backtester

    original_engine = event_backtester.NNFXSignalEngine
    event_backtester.NNFXSignalEngine = StubEngine
    try:
        result = EventBacktester(config, output_root=output_root).run()
    finally:
        event_backtester.NNFXSignalEngine = original_engine

    trades = pd.read_csv(result.run_dir / "trades.csv")
    assert "tp1" in set(trades["close_reason"])
    parsed_entry_times = pd.to_datetime(trades["entry_time"], errors="coerce")
    assert parsed_entry_times.notna().all()
    assert parsed_entry_times.dt.year.ge(2024).all()
    tp1 = trades[trades["close_reason"] == "tp1"].iloc[0]
    assert tp1["quantity"] > 0


def test_equity_curve_marks_open_positions_to_market(tmp_path: Path):
    rows = []
    prices = [100, 101, 102, 103, 110, 111, 112]
    for index, close in enumerate(prices):
        rows.append(
            {
                "timestamp": pd.Timestamp("2024-01-01") + pd.Timedelta(hours=index),
                "open": close,
                "high": close + 0.25,
                "low": close - 0.25,
                "close": close,
                "volume": 1000,
                "atr": 2.0,
                "baseline_signal": 1 if index >= 2 else 0,
                "c1_signal": 1 if index == 2 else 0,
                "c2_signal": 1,
                "filter_pass_long": True,
                "filter_pass_short": True,
                "exit_signal": 0,
            }
        )
    frame = pd.DataFrame(rows)
    csv_path = tmp_path / "BTC-USDT_1h.csv"
    config_path = tmp_path / "strategy.yml"
    output_root = tmp_path / "results"
    write_ohlcv_csv(csv_path)
    write_config(config_path, csv_path, output_root)
    config = load_strategy_config(config_path)
    config.backtest.warmup_bars = 0

    class StubEngine:
        def __init__(self, _config):
            pass

        def compute_indicators(self, _raw):
            return frame

        def evaluate_bar(self, data, row_index, has_open_position=False, open_position_side=None):
            if not has_open_position and row_index == 2:
                from nnfx_crypto.signals.signal_types import TradeIntent

                return TradeIntent("entry", "long", "test_entry", row_index, data.iloc[row_index]["timestamp"])
            return None

    import nnfx_crypto.backtest.event_backtester as event_backtester

    original_engine = event_backtester.NNFXSignalEngine
    event_backtester.NNFXSignalEngine = StubEngine
    try:
        result = EventBacktester(config, output_root=output_root).run()
    finally:
        event_backtester.NNFXSignalEngine = original_engine

    equity = pd.read_csv(result.run_dir / "equity_curve.csv")
    metrics = json.loads((result.run_dir / "metrics.json").read_text(encoding="utf-8"))
    open_rows = equity[equity["open_position"] == 1]

    assert not open_rows.empty
    assert open_rows["equity"].nunique() > 1
    assert metrics["time_in_market"] > 0


def test_backtester_stops_after_total_drawdown_breach(tmp_path: Path):
    rows = []
    prices = [100, 101, 100, 80, 79, 78, 120, 121]
    for index, close in enumerate(prices):
        rows.append(
            {
                "timestamp": pd.Timestamp("2024-01-01") + pd.Timedelta(hours=index),
                "open": close,
                "high": close + 0.1,
                "low": close - 0.1,
                "close": close,
                "volume": 1000,
                "atr": 50.0,
                "baseline_signal": 1 if index in {1, 6} else 0,
                "c1_signal": 1 if index in {1, 6} else 0,
                "c2_signal": 1,
                "filter_pass_long": True,
                "filter_pass_short": True,
                "exit_signal": 0,
            }
        )
    frame = pd.DataFrame(rows)
    csv_path = tmp_path / "BTC-USDT_1h.csv"
    config_path = tmp_path / "strategy.yml"
    output_root = tmp_path / "results"
    write_ohlcv_csv(csv_path)
    write_config(config_path, csv_path, output_root)
    config = load_strategy_config(config_path)
    config.backtest.warmup_bars = 0
    config.risk.max_total_drawdown_pct = 0.0005

    class StubEngine:
        def __init__(self, _config):
            pass

        def compute_indicators(self, _raw):
            return frame

        def evaluate_bar(self, data, row_index, has_open_position=False, open_position_side=None):
            if not has_open_position and row_index in {1, 6}:
                from nnfx_crypto.signals.signal_types import TradeIntent

                return TradeIntent("entry", "long", "test_entry", row_index, data.iloc[row_index]["timestamp"])
            return None

    import nnfx_crypto.backtest.event_backtester as event_backtester

    original_engine = event_backtester.NNFXSignalEngine
    event_backtester.NNFXSignalEngine = StubEngine
    try:
        result = EventBacktester(config, output_root=output_root).run()
    finally:
        event_backtester.NNFXSignalEngine = original_engine

    trades = pd.read_csv(result.run_dir / "trades.csv")
    assert "max_total_drawdown" in set(trades["close_reason"])
    assert len(trades) == 1


def test_max_open_positions_allows_second_entry(tmp_path: Path):
    # Two entry signals on consecutive bars; max_open_positions_per_pair=2
    rows = []
    prices = [100, 101, 102, 103, 104, 105, 106, 107, 108, 109]
    for i, close in enumerate(prices):
        rows.append({
            "timestamp": pd.Timestamp("2024-01-01") + pd.Timedelta(hours=i),
            "open": close, "high": close + 1.5, "low": close - 0.5,
            "close": close, "volume": 1000,
            "atr": 1.0,
            "baseline_signal": 1, "c1_signal": 1, "c2_signal": 1,
            "filter_pass_long": True, "filter_pass_short": True,
            "exit_signal": 0,
        })
    frame = pd.DataFrame(rows)

    csv_path = tmp_path / "BTC-USDT_1h.csv"
    config_path = tmp_path / "strategy.yml"
    output_root = tmp_path / "results"
    write_ohlcv_csv(csv_path)
    write_config(config_path, csv_path, output_root)
    config = load_strategy_config(config_path)
    config.backtest.warmup_bars = 0
    config.strategy.allow_continuation_trades = True
    config.risk.max_open_positions_per_pair = 2

    entry_calls: list[int] = []

    class StubEngine:
        def __init__(self, _config):
            pass

        def compute_indicators(self, _raw):
            return frame

        def evaluate_bar(self, data, row_index, has_open_position=False, open_position_side=None):
            from nnfx_crypto.signals.signal_types import TradeIntent
            if not has_open_position and row_index in {0, 1}:
                entry_calls.append(row_index)
                return TradeIntent("entry", "long", "test_entry", row_index, data.iloc[row_index]["timestamp"])
            return None

    import nnfx_crypto.backtest.event_backtester as event_backtester
    original = event_backtester.NNFXSignalEngine
    event_backtester.NNFXSignalEngine = StubEngine
    try:
        result = EventBacktester(config, output_root=output_root).run()
    finally:
        event_backtester.NNFXSignalEngine = original

    trades = pd.read_csv(result.run_dir / "trades.csv")
    # Both entry signals fired and both positions opened
    assert len([r for r in trades["close_reason"] if r in {"end_of_data", "stop_loss", "tp1"}]) >= 2
    assert len(trades) >= 2


def test_backtester_stops_after_daily_loss_breach(tmp_path: Path):
    # Day 1: entry at bar 1, loss triggers daily halt at bar 3
    # Day 2: daily halt resets, second entry fires and closes end-of-data
    rows = []
    prices_day1 = [100, 101, 100, 80]
    prices_day2 = [120, 121, 122, 123]
    timestamps = (
        [pd.Timestamp("2024-01-01") + pd.Timedelta(hours=i) for i in range(4)]
        + [pd.Timestamp("2024-01-02") + pd.Timedelta(hours=i) for i in range(4)]
    )
    for index, (ts, close) in enumerate(zip(timestamps, prices_day1 + prices_day2)):
        rows.append({
            "timestamp": ts,
            "open": close, "high": close + 0.1, "low": close - 0.1,
            "close": close, "volume": 1000,
            "atr": 50.0,
            "baseline_signal": 1 if index in {1, 5} else 0,
            "c1_signal": 1 if index in {1, 5} else 0,
            "c2_signal": 1,
            "filter_pass_long": True, "filter_pass_short": True,
            "exit_signal": 0,
        })
    frame = pd.DataFrame(rows)
    csv_path = tmp_path / "BTC-USDT_1h.csv"
    config_path = tmp_path / "strategy.yml"
    output_root = tmp_path / "results"
    write_ohlcv_csv(csv_path)
    write_config(config_path, csv_path, output_root)
    config = load_strategy_config(config_path)
    config.backtest.warmup_bars = 0
    config.risk.max_daily_loss_pct = 0.0005
    config.risk.max_total_drawdown_pct = 0.99

    class StubEngine:
        def __init__(self, _config):
            pass

        def compute_indicators(self, _raw):
            return frame

        def evaluate_bar(self, data, row_index, has_open_position=False, open_position_side=None):
            if not has_open_position and row_index in {1, 5}:
                from nnfx_crypto.signals.signal_types import TradeIntent
                return TradeIntent("entry", "long", "test_entry", row_index, data.iloc[row_index]["timestamp"])
            return None

    import nnfx_crypto.backtest.event_backtester as event_backtester
    original_engine = event_backtester.NNFXSignalEngine
    event_backtester.NNFXSignalEngine = StubEngine
    try:
        result = EventBacktester(config, output_root=output_root).run()
    finally:
        event_backtester.NNFXSignalEngine = original_engine

    trades = pd.read_csv(result.run_dir / "trades.csv")
    close_reasons = set(trades["close_reason"])
    assert "daily_loss_limit" in close_reasons
    # Day-2 trade closes end-of-data (daily halt reset)
    assert "end_of_data" in close_reasons
    assert len(trades) == 2
