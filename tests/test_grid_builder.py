from trading_system.strategies.grid.grid_config import GridConfig
from trading_system.strategies.grid.grid_builder import build_grid_levels

def test_build_grid_levels():
    cfg = GridConfig(
        symbol="BTCUSDT",
        timeframe="1h",
        initial_cash=10000,
        lower_bound=100,
        upper_bound=200,
        grid_count=3,
        order_size_quote=10,
        fee_rate=0.001,
        slippage_rate=0.0005,
        regime={},
    )
    assert build_grid_levels(cfg) == [100.0, 150.0, 200.0]
