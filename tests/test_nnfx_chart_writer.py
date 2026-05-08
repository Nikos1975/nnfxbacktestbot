from pathlib import Path

import pandas as pd

from nnfx_crypto.reports.chart_writer import write_price_signal_chart


def test_price_signal_chart_accepts_trade_markers(tmp_path: Path):
    frame = pd.DataFrame(
        {
            "timestamp": pd.date_range("2024-01-01", periods=5, freq="h"),
            "close": [100, 101, 102, 101, 103],
            "baseline_value": [99, 100, 101, 101, 102],
        }
    )
    trades = pd.DataFrame(
        {
            "entry_time": ["2024-01-01 01:00:00"],
            "exit_time": ["2024-01-01 03:00:00"],
            "entry_price": [101.0],
            "exit_price": [101.0],
            "side": ["long"],
            "close_reason": ["crossroads_exit_long"],
        }
    )
    output = tmp_path / "chart.png"

    write_price_signal_chart(frame, output, trades=trades)

    assert output.exists()
    assert output.stat().st_size > 0
