import pandas as pd

def sma(series: pd.Series, period: int) -> pd.Series:
    return series.rolling(period, min_periods=period).mean()

def ema(series: pd.Series, period: int) -> pd.Series:
    return series.ewm(span=period, adjust=False, min_periods=period).mean()

def slope(series: pd.Series, period: int = 5) -> pd.Series:
    return series.diff(period) / period
