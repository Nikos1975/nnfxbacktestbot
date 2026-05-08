from __future__ import annotations

import numpy as np
import pandas as pd


class CrossRoadsIndicator:
    name = "crossroads"

    def compute(self, df: pd.DataFrame, params: dict) -> pd.DataFrame:
        output = df.copy()
        fast_length = int(params.get("fast_length", 2))
        slow_length = int(params.get("slow_length", 24))
        fast = output["close"].ewm(span=fast_length, adjust=False, min_periods=fast_length).mean()
        slow = output["close"].ewm(span=slow_length, adjust=False, min_periods=slow_length).mean()
        previous_fast = fast.shift(1)
        previous_slow = slow.shift(1)
        output["crossroads_fast"] = fast
        output["crossroads_slow"] = slow
        output["exit_signal"] = np.select(
            [
                (fast < slow) & (previous_fast >= previous_slow),
                (fast > slow) & (previous_fast <= previous_slow),
            ],
            [-1, 1],
            default=0,
        ).astype(int)
        return output
