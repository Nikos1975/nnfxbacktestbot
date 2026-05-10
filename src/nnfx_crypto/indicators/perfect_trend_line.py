import numpy as np
import pandas as pd

class PerfectTrendLineIndicator:
    """Perfect Trend Line exit indicator approximation."""
    name = "perfect_trend_line"

    def compute(self, df: pd.DataFrame, params: dict) -> pd.DataFrame:
        output = df.copy()
        period = int(params.get("period", 10))
        atr_length = int(params.get("atr_length", 14))
        atr_multiplier = float(params.get("atr_multiplier", 2.0))
        source_col = params.get("source", "close")

        src = output[source_col].astype(float)
        highs = output["high"].astype(float)
        lows = output["low"].astype(float)

        # Compute ATR
        tr = pd.concat([
            highs - lows,
            (highs - src.shift(1)).abs(),
            (lows - src.shift(1)).abs()
        ], axis=1).max(axis=1)
        atr = tr.rolling(window=atr_length).mean()

        rolling_high = highs.rolling(window=period).max()
        rolling_low = lows.rolling(window=period).min()

        long_line = rolling_high - (atr_multiplier * atr)
        short_line = rolling_low + (atr_multiplier * atr)

        trend = np.zeros(len(output))
        current_trend = 0

        # Iterative trend logic
        for i in range(1, len(output)):
            if pd.isna(long_line.iloc[i-1]) or pd.isna(short_line.iloc[i-1]):
                continue
                
            if src.iloc[i] > short_line.iloc[i-1]:
                current_trend = 1
            elif src.iloc[i] < long_line.iloc[i-1]:
                current_trend = -1
            # else keep previous
            trend[i] = current_trend

        output["perfect_trend_line_long"] = long_line
        output["perfect_trend_line_short"] = short_line
        output["perfect_trend_line_trend"] = trend
        
        # Exit signal: 1 when trend flips bullish (exit short), -1 when trend flips bearish (exit long)
        # Wait, NNFX Signal Engine usually expects 1 for exit_long? 
        # User said: -1 when trend flips bearish, 1 when trend flips bullish.
        # This matches ExitSignal.EXIT_LONG = -1 (usually) in some systems, 
        # but let's follow the user's mapping in Signal Engine.
        
        trend_series = pd.Series(trend)
        prev_trend = trend_series.shift(1).fillna(0)
        
        exit_signals = np.zeros(len(output))
        exit_signals[(trend_series == -1) & (prev_trend != -1)] = -1 # Bearish flip
        exit_signals[(trend_series == 1) & (prev_trend != 1)] = 1   # Bullish flip
        
        output["perfect_trend_line_exit_signal"] = exit_signals
        
        return output
