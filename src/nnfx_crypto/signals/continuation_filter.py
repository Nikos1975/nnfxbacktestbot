from __future__ import annotations

import pandas as pd


def is_continuation_trade(df: pd.DataFrame, row_index: int, side: str) -> bool:
    if row_index <= 0:
        return False
    direction = 1 if side == "long" else -1
    previous = df.iloc[row_index - 1]
    return bool(
        int(previous.get("baseline_signal", 0)) == direction
        and int(previous.get("c1_signal", 0)) == direction
        and int(previous.get("c2_signal", 0)) == direction
    )
