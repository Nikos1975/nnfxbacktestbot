import pandas as pd
from trading_system.indicators.ma import sma

def test_sma_has_expected_warmup_nans():
    s = pd.Series([1, 2, 3, 4, 5])
    out = sma(s, 3)
    assert pd.isna(out.iloc[0])
    assert pd.isna(out.iloc[1])
    assert out.iloc[2] == 2
