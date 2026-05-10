from __future__ import annotations

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

        fast_alpha = 2.0 / (fc + 1.0)
        slow_alpha = 2.0 / (sc + 1.0)

        # Vectorised rolling windows — replaces per-bar iloc slicing
        roll_high_n = high.rolling(length).max()
        roll_low_n = low.rolling(length).min()
        roll_high_2n = high.rolling(2 * length).max()
        roll_low_2n = low.rolling(2 * length).min()

        n1 = (roll_high_n - roll_low_n) / length
        n2 = (roll_high_n.shift(length) - roll_low_n.shift(length)) / length
        n3 = (roll_high_2n - roll_low_2n) / (2 * length)

        valid = (n1 > 0) & (n2 > 0) & (n3 > 0)
        with np.errstate(divide="ignore", invalid="ignore"):
            d = np.where(valid, (np.log(n1 + n2) - np.log(n3)) / np.log(2.0), np.nan)
        alpha_arr = np.where(valid, np.exp(-4.6 * (d - 1.0)), slow_alpha)
        alpha_arr = np.clip(alpha_arr, slow_alpha, fast_alpha)

        # EMA recursion — sequential dependency, unavoidable Python loop
        price_arr = price.to_numpy(dtype=float)
        frama_arr = np.full(len(output), np.nan)
        start = 2 * length
        if start < len(output):
            frama_arr[start] = price_arr[start]
            for i in range(start + 1, len(output)):
                prev = frama_arr[i - 1]
                a = alpha_arr[i] if not np.isnan(alpha_arr[i]) else slow_alpha
                frama_arr[i] = a * price_arr[i] + (1.0 - a) * (price_arr[i - 1] if np.isnan(prev) else prev)

        frama = pd.Series(frama_arr, index=output.index)
        output["frama_value"] = frama # Compatibility
        output["baseline_value"] = frama
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
