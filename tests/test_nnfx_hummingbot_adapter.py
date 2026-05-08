from pathlib import Path

from nnfx_crypto.hummingbot.adapters.executor_action_adapter import intent_to_executor_action
from nnfx_crypto.hummingbot.adapters.hummingbot_config_adapter import (
    candles_to_dataframe,
    hummingbot_yaml_to_strategy_config,
)
from nnfx_crypto.signals.signal_types import TradeIntent


def test_hummingbot_yaml_maps_to_strategy_config(tmp_path: Path):
    config_path = tmp_path / "hb.yml"
    config_path.write_text(
        """
controller_name: nnfx_algo5_controller
controller_type: directional_trading
connector_name: binance_perpetual
trading_pair: BTC-USDT
timeframe: 1h
nnfx:
  baseline: {name: frama, params: {length: 10, fc: 1, sc: 198}}
  c1: {name: reflex, params: {length: 50}}
  c2: {name: stablefx, params: {length: 14, signal_length: 5}}
  volume_or_volatility_filter: {name: stiffness, params: {length: 60, threshold: 50.0}}
  exit: {name: crossroads, params: {fast_length: 2, slow_length: 24}}
risk:
  risk_per_trade_pct: 0.005
  atr_length: 14
  stop_loss_atr_multiplier: 1.25
  tp1_atr_multiplier: 1.0
execution:
  leverage: 1
  position_mode: ONEWAY
  order_type: MARKET
""",
        encoding="utf-8",
    )

    cfg = hummingbot_yaml_to_strategy_config(config_path)

    assert cfg.market.connector == "binance_perpetual"
    assert cfg.market.trading_pair == "BTC-USDT"
    assert cfg.indicators.baseline.name == "frama"


def test_candles_to_dataframe_normalizes_ohlcv():
    candles = [
        {"timestamp": "2024-01-01T00:00:00", "open": 1, "high": 2, "low": 0.5, "close": 1.5, "volume": 10},
        {"timestamp": "2024-01-01T01:00:00", "open": 2, "high": 3, "low": 1.5, "close": 2.5, "volume": 20},
    ]

    df = candles_to_dataframe(candles)

    assert list(df.columns) == ["timestamp", "open", "high", "low", "close", "volume"]
    assert df["close"].tolist() == [1.5, 2.5]


def test_executor_action_adapter_maps_long_entry():
    intent = TradeIntent("entry", "long", "algo5_long_entry", 5)

    action = intent_to_executor_action(
        intent=intent,
        connector_name="binance_perpetual",
        trading_pair="BTC-USDT",
        amount=0.25,
        entry_price=100.0,
        stop_price=98.0,
        tp1_price=102.0,
        existing_executor_pairs=set(),
    )

    assert action is not None
    assert action["side"] == "long"
    assert action["trading_pair"] == "BTC-USDT"
    assert action["stop_price"] == 98.0


def test_executor_action_adapter_blocks_duplicate_pair():
    intent = TradeIntent("entry", "long", "algo5_long_entry", 5)

    action = intent_to_executor_action(
        intent=intent,
        connector_name="binance_perpetual",
        trading_pair="BTC-USDT",
        amount=0.25,
        entry_price=100.0,
        stop_price=98.0,
        tp1_price=102.0,
        existing_executor_pairs={"BTC-USDT"},
    )

    assert action is None
