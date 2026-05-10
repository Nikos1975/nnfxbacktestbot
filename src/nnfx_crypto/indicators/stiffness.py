from __future__ import annotations

import pandas as pd


class StiffnessIndicator:
    name = "stiffness"

    def compute(self, df: pd.DataFrame, params: dict) -> pd.DataFrame:
        output = df.copy()
        ma_length = int(params.get("period1", params.get("ma_length", 100)))
        sum_length = int(params.get("period3", params.get("length", 60)))
        signal_length = int(params.get("period2", params.get("signal_length", 3)))
        threshold = float(params.get("threshold", 50.0))
        close = output["close"].astype(float)
        lower_band = close.rolling(ma_length, min_periods=ma_length).mean() - (
            0.2 * close.rolling(ma_length, min_periods=ma_length).std()
        )
        above = (close > lower_band).astype(float)
        stiffness = above.rolling(sum_length, min_periods=sum_length).sum() * float(ma_length) / sum_length
        output["stiffness_value"] = stiffness
        output["stiffness_signal"] = stiffness.rolling(
            signal_length,
            min_periods=signal_length,
        ).mean()
        passes = stiffness >= threshold
        output["filter_pass_long"] = passes.fillna(False).astype(bool)
        output["filter_pass_short"] = passes.fillna(False).astype(bool)
        return output
