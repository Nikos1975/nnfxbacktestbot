import pandas as pd

from trading_system.strategies.grid.grid_backtester import run_grid_backtest
from trading_system.strategies.grid.grid_config import GridConfig


def test_grid_backtester_returns_summary_trades_and_equity():
    df = pd.DataFrame(
        {
            "timestamp": pd.date_range(
                start="2024-01-01",
                periods=200,
                freq="1h",
                tz="UTC",
            ),
            "open": [100.0] * 200,
            "high": [110.0] * 200,
            "low": [90.0] * 200,
            "close": [100.0] * 200,
            "volume": [1000.0] * 200,
        }
    )

    cfg = GridConfig(
        symbol="TESTUSDT",
        timeframe="1h",
        initial_cash=10000,
        lower_bound=90,
        upper_bound=110,
        grid_count=5,
        order_size_quote=100,
        fee_rate=0.001,
        slippage_rate=0.0005,
        regime={},
    )

    output = run_grid_backtest(df=df, cfg=cfg)

    assert output.result.rows == 200
    assert output.equity.empty is False
    assert len(output.equity) == 200
    assert "equity" in output.equity.columns
    assert "exposure_pct" in output.equity.columns
    assert "buy_and_hold_equity" in output.equity.columns
    assert "buy_and_hold_drawdown_pct" in output.equity.columns
    assert output.result.buy_and_hold_final_equity > 0
    assert output.result.buy_and_hold_max_drawdown_pct >= 0
    assert output.result.strategy_volatility_annualized_pct >= 0
    assert output.result.buy_and_hold_volatility_annualized_pct >= 0