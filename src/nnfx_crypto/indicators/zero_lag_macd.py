import numpy as np
import pandas as pd

class ZeroLagMACDIndicator:
    """DEMA-based Zero-Lag MACD confirmation indicator."""
    name = "zero_lag_macd"

    def _dema(self, series: pd.Series, length: int) -> pd.Series:
        ema1 = series.ewm(span=length, adjust=False).mean()
        ema2 = ema1.ewm(span=length, adjust=False).mean()
        return 2 * ema1 - ema2

    def compute(self, df: pd.DataFrame, params: dict) -> pd.DataFrame:
        output = df.copy()
        fast_length = int(params.get("fast_length", 12))
        slow_length = int(params.get("slow_length", 26))
        signal_length = int(params.get("signal_length", 9))
        source_col = params.get("source", "close")

        src = output[source_col].astype(float)

        fast_dema = self._dema(src, fast_length)
        slow_dema = self._dema(src, slow_length)

        macd_line = fast_dema - slow_dema
        macd_signal = self._dema(macd_line, signal_length)
        histogram = macd_line - macd_signal

        # Trend logic
        # Bullish: line > signal AND histogram > 0
        # Bearish: line < signal AND histogram < 0
        trend = np.zeros(len(output))
        trend[(macd_line > macd_signal) & (histogram > 0)] = 1
        trend[(macd_line < macd_signal) & (histogram < 0)] = -1

        output["zero_lag_macd_line"] = macd_line
        output["zero_lag_macd_signal"] = macd_signal
        output["zero_lag_macd_histogram"] = histogram
        output["zero_lag_macd_trend"] = trend
        
        return output
