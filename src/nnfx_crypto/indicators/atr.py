from __future__ import annotations

import pandas as pd


class ATRIndicator:
    name = "atr"

    def compute(self, df: pd.DataFrame, params: dict) -> pd.DataFrame:
        output = df.copy()
        length = int(params.get("length", 14))
        previous_close = output["close"].shift(1)
        true_range = pd.concat(
            [
                output["high"] - output["low"],
                (output["high"] - previous_close).abs(),
                (output["low"] - previous_close).abs(),
            ],
            axis=1,
        ).max(axis=1)
        output["atr"] = true_range.rolling(length, min_periods=length).mean()
        return output
