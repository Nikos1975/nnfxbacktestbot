from __future__ import annotations

import numpy as np
import pandas as pd


class ReflexIndicator:
    """Deterministic Reflex placeholder.

    The exact Reflex formula is not available in this workspace. This placeholder keeps the
    stable C1 interface and emits zero-crossing signals from close minus an EMA.
    """

    name = "reflex"

    def compute(self, df: pd.DataFrame, params: dict) -> pd.DataFrame:
        output = df.copy()
        length = int(params.get("length", 50))
        ema = output["close"].ewm(span=length, adjust=False, min_periods=length).mean()
        value = output["close"] - ema
        previous = value.shift(1)
        output["reflex_value"] = value
        output["c1_signal"] = np.select(
            [(value > 0) & (previous <= 0), (value < 0) & (previous >= 0)],
            [1, -1],
            default=0,
        ).astype(int)
        return output
