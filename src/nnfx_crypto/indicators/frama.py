from __future__ import annotations

import math

import numpy as np
import pandas as pd


class FRAMAIndicator:
    name = "frama"

    def compute(self, df: pd.DataFrame, params: dict) -> pd.DataFrame:
        output = df.copy()
        length = int(params.get("period_frama", params.get("length", 10)))
        price_type = int(params.get("price_type", params.get("PriceType", 0)))
        fc = float(params.get("fc", 1))
        sc = float(params.get("sc", 198))
        price = _select_price(output, price_type)
        close = output["close"].astype(float)
        high = output["high"].astype(float)
        low = output["low"].astype(float)
        frama = pd.Series(np.nan, index=output.index, dtype=float)

        fast_alpha = 2.0 / (fc + 1.0)
        slow_alpha = 2.0 / (sc + 1.0)

        for pos in range(len(output)):
            if pos < 2 * length:
                continue
            recent_start = pos - length + 1
            recent_end = pos + 1
            previous_start = pos - (2 * length) + 1
            previous_end = pos - length + 1
            full_start = previous_start
            full_end = recent_end

            n1 = (high.iloc[recent_start:recent_end].max() - low.iloc[recent_start:recent_end].min()) / length
            n2 = (
                high.iloc[previous_start:previous_end].max()
                - low.iloc[previous_start:previous_end].min()
            ) / length
            n3 = (high.iloc[full_start:full_end].max() - low.iloc[full_start:full_end].min()) / (
                2.0 * length
            )
            if n1 > 0 and n2 > 0 and n3 > 0:
                dimension = (math.log(n1 + n2) - math.log(n3)) / math.log(2)
                alpha = math.exp(-4.6 * (dimension - 1.0))
                alpha = min(fast_alpha, max(slow_alpha, alpha))
            else:
                alpha = slow_alpha

            previous = frama.iloc[pos - 1]
            if np.isnan(previous):
                previous = price.iloc[pos - 1]
            frama.iloc[pos] = alpha * price.iloc[pos] + (1.0 - alpha) * previous

        output["baseline_value"] = frama
        output["baseline_signal"] = np.select(
            [close > frama, close < frama],
            [1, -1],
            default=0,
        ).astype(int)
        output.loc[frama.isna(), "baseline_signal"] = 0
        return output


def _select_price(df: pd.DataFrame, price_type: int) -> pd.Series:
    open_ = df["open"].astype(float)
    high = df["high"].astype(float)
    low = df["low"].astype(float)
    close = df["close"].astype(float)
    if price_type == 1:
        return open_
    if price_type == 2:
        return high
    if price_type == 3:
        return low
    if price_type == 4:
        return (high + low) / 2.0
    if price_type == 5:
        return (high + low + close) / 3.0
    if price_type == 6:
        return (high + low + 2.0 * close) / 4.0
    return close
