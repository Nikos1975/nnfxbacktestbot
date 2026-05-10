import pandas as pd
import numpy as np
import pytest
from nnfx_crypto.indicators.rvol import RVOLIndicator
from nnfx_crypto.indicators.perfect_trend_line import PerfectTrendLineIndicator
from nnfx_crypto.indicators.zero_lag_macd import ZeroLagMACDIndicator
from nnfx_crypto.indicators.crossroads import CrossRoadsIndicator

def test_rvol_logic():
    df = pd.DataFrame({
        "volume": [10, 10, 10, 10, 50, 10], # SMA(5) at index 4 is 18. Index 4 rvol = 50/18 = 2.77
        "close": [100]*6
    })
    ind = RVOLIndicator()
    output = ind.compute(df, {"length": 5, "threshold": 2.0})
    
    assert "rvol" in output.columns
    assert "rvol_filter_signal" in output.columns
    assert output["rvol_filter_signal"].iloc[4] == 1
    assert output["rvol_filter_signal"].iloc[5] == 0
    # Isolation check
    for col in ["c1_signal", "c2_signal", "baseline_signal", "exit_signal"]:
        assert col not in output.columns

def test_perfect_trend_line_logic():
    # Simple data where price goes up then down
    df = pd.DataFrame({
        "close": [10, 11, 12, 13, 14, 15, 14, 13, 12, 11, 10],
        "high": [10.5, 11.5, 12.5, 13.5, 14.5, 15.5, 14.5, 13.5, 12.5, 11.5, 10.5],
        "low": [9.5, 10.5, 11.5, 12.5, 13.5, 14.5, 13.5, 12.5, 11.5, 10.5, 9.5]
    })
    ind = PerfectTrendLineIndicator()
    output = ind.compute(df, {"period": 3, "atr_length": 5, "atr_multiplier": 1.0})
    
    assert "perfect_trend_line_exit_signal" in output.columns
    # Isolation check
    for col in ["c1_signal", "c2_signal", "baseline_signal"]:
        assert col not in output.columns

def test_zero_lag_macd_logic():
    df = pd.DataFrame({
        "close": np.sin(np.linspace(0, 10, 100)) + 10
    })
    ind = ZeroLagMACDIndicator()
    # Test unusual params (fast > slow)
    output = ind.compute(df, {"fast_length": 26, "slow_length": 12, "signal_length": 9})
    
    assert "zero_lag_macd_trend" in output.columns
    assert not output["zero_lag_macd_trend"].isna().all()
    # Isolation check
    for col in ["c1_signal", "c2_signal", "baseline_signal", "exit_signal"]:
        assert col not in output.columns

def test_cross_roads_isolation_regression():
    df = pd.DataFrame({
        "close": [10]*20, "high": [11]*20, "low": [9]*20, "open": [10]*20
    })
    ind = CrossRoadsIndicator()
    output = ind.compute(df, {"start_len": 2, "lookback_period": 10})
    for col in ["c1_signal", "c2_signal", "exit_signal"]:
        assert col not in output.columns
