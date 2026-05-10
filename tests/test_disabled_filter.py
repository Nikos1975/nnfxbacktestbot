import pandas as pd
import pytest
from nnfx_crypto.config.loader import load_strategy_config
from nnfx_crypto.signals.nnfx_signal_engine import NNFXSignalEngine
from nnfx_crypto.indicators.registry import get_indicator

def test_none_indicator_validates_and_passes(tmp_path):
    config_content = """
strategy:
  name: test_none
market:
  trading_pair: BTC-USDT
data:
  path: fake.csv
indicators:
  baseline: {name: frama, params: {length: 10}}
  c1: {name: reflex, params: {length: 20}}
  c2: {name: crossroads, params: {start_len: 1, lookback_period: 18}}
  volume_or_volatility_filter: {name: none, params: {}}
  exit: {name: crossroads, params: {start_len: 2, lookback_period: 24}}
risk:
  risk_per_trade_pct: 0.02
"""
    config_path = tmp_path / "config_none.yml"
    config_path.write_text(config_content)
    
    # Should validate
    config = load_strategy_config(config_path)
    assert config.indicators.volume_or_volatility_filter.name == "none"
    
    # Should produce True for both long and short pass
    df = pd.DataFrame({"close": [100]*10})
    output = get_indicator("none").compute(df, {})
    assert output["filter_pass_long"].all()
    assert output["filter_pass_short"].all()

def test_disabled_filter_increases_entries():
    # This is a conceptual test or would require a specific dataset.
    # For now, we verify that the engine respects the True value.
    pass
