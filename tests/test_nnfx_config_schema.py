from pathlib import Path

import pytest
from pydantic import ValidationError

from nnfx_crypto.config.loader import load_strategy_config
from nnfx_crypto.config.schema import StrategyConfig


def valid_config_dict() -> dict:
    return {
        "strategy": {
            "name": "algo5_fractal_rigidity",
            "mode": "backtest",
            "direction_mode": "both",
            "allow_continuation_trades": False,
        },
        "market": {
            "connector": "binance_perpetual",
            "trading_pair": "BTC-USDT",
            "timeframe": "1h",
            "quote_asset": "USDT",
            "base_asset": "BTC",
        },
        "data": {
            "source": "csv",
            "path": "data/nnfx_crypto/processed/BTC-USDT_1h.csv",
            "start": "2021-01-01",
            "end": "2026-01-01",
        },
        "indicators": {
            "baseline": {"name": "frama", "params": {"length": 10, "fc": 1, "sc": 198}},
            "c1": {"name": "reflex", "params": {"length": 50}},
            "c2": {"name": "stablefx", "params": {"length": 14, "signal_length": 5}},
            "volume_or_volatility_filter": {
                "name": "stiffness",
                "params": {"length": 60, "threshold": 50.0},
            },
            "exit": {"name": "crossroads", "params": {"fast_length": 2, "slow_length": 24}},
        },
        "risk": {
            "account_equity": 10000,
            "risk_per_trade_pct": 0.005,
            "atr_length": 14,
            "stop_loss_atr_multiplier": 1.25,
            "tp1_atr_multiplier": 1.0,
            "use_two_half_positions": True,
            "move_second_half_to_breakeven_after_tp1": True,
            "max_open_positions_per_pair": 1,
            "max_total_open_positions": 3,
            "max_daily_loss_pct": 0.02,
            "max_total_drawdown_pct": 0.20,
        },
        "execution": {
            "order_type": "market",
            "fee_pct": 0.0006,
            "slippage_pct": 0.0005,
            "use_next_bar_open": True,
        },
        "backtest": {
            "warmup_bars": 300,
            "initial_capital": 10000,
            "export_trades_csv": True,
            "export_equity_curve_csv": True,
            "export_metrics_json": True,
            "export_html_report": True,
            "export_chart_png": True,
        },
    }


def test_strategy_config_accepts_algo5_defaults():
    cfg = StrategyConfig.model_validate(valid_config_dict())

    assert cfg.strategy.name == "algo5_fractal_rigidity"
    assert cfg.market.trading_pair == "BTC-USDT"
    assert cfg.indicators.baseline.name == "frama"
    assert cfg.risk.stop_loss_atr_multiplier == 1.25


def test_strategy_config_rejects_unknown_timeframe():
    data = valid_config_dict()
    data["market"]["timeframe"] = "2h"

    with pytest.raises(ValidationError, match="timeframe"):
        StrategyConfig.model_validate(data)


def test_strategy_config_rejects_unknown_indicator_name():
    data = valid_config_dict()
    data["indicators"]["c1"]["name"] = "not_real"

    with pytest.raises(ValidationError, match="Unknown indicator 'not_real'"):
        StrategyConfig.model_validate(data)


def test_load_strategy_config_reads_yaml(tmp_path: Path):
    config_path = tmp_path / "strategy.yml"
    config_path.write_text(
        """
strategy:
  name: algo5_fractal_rigidity
market:
  trading_pair: BTC-USDT
data:
  path: data/nnfx_crypto/processed/BTC-USDT_1h.csv
indicators:
  baseline: {name: frama, params: {length: 10}}
  c1: {name: reflex, params: {length: 50}}
  c2: {name: stablefx, params: {length: 14}}
  volume_or_volatility_filter: {name: stiffness, params: {length: 60}}
  exit: {name: crossroads, params: {fast_length: 2, slow_length: 24}}
""",
        encoding="utf-8",
    )

    cfg = load_strategy_config(config_path)

    assert cfg.strategy.mode == "backtest"
    assert cfg.market.connector == "binance_perpetual"
    assert cfg.market.timeframe == "1h"
    assert cfg.risk.atr_length == 14
